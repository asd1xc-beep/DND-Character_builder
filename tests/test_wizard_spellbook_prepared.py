from models.character import new_character
from rules.character_validation import build_validation_report, invalid_spell_choice_messages
import pytest

from rules.level_up import (
    commit_level_up_draft,
    create_level_up_draft,
    refresh_level_up_draft_choices,
    resolve_pending_choice,
)
from rules.leveling import effective_spellcasting
from services.character_engine import recalculate_character
from services.character_sheet import build_character_sheet
from services.save_load import CURRENT_SCHEMA_VERSION, migrate_character
from tests.test_level_one_builds import app_data


def wizard_spell_names(data, levels, count):
    level_set = set(levels)
    names = [
        spell["name"]
        for spell in data["spells"]
        if "Wizard" in spell.get("classes", [])
        and spell.get("level") in level_set
    ]
    assert len(names) >= count
    return names[:count]


def wizard_school_spell_names(data, school_code, levels, count, exclude=None):
    level_set = set(levels)
    excluded = set(exclude or [])
    names = [
        spell["name"]
        for spell in data["spells"]
        if "Wizard" in spell.get("classes", [])
        and spell.get("school_code") == school_code
        and spell.get("level") in level_set
        and spell["name"] not in excluded
    ]
    assert len(names) >= count
    return names[:count]


def diviner_savant_choices(data, spellbook, max_level=8):
    choices = wizard_school_spell_names(data, "D", {1, 2}, 2, spellbook)
    excluded = set(spellbook) | set(choices)
    for level, maximum_spell_level in ((5, 3), (7, 4), (9, 5), (11, 6), (13, 7), (15, 8)):
        if maximum_spell_level > max_level:
            continue
        choice = wizard_school_spell_names(data, "D", range(1, maximum_spell_level + 1), 1, excluded)[0]
        choices.append(choice)
        excluded.add(choice)
    return {
        "savant_spells": choices[:2],
        "savant_spells_level_5": choices[2:3],
        "savant_spells_level_7": choices[3:4],
        "savant_spells_level_9": choices[4:5],
        "savant_spells_level_11": choices[5:6],
        "savant_spells_level_13": choices[6:7],
        "savant_spells_level_15": choices[7:8],
    }


def level_sixteen_wizard(data):
    spellbook = wizard_spell_names(data, range(1, 9), 36)
    character = new_character()
    character.update({
        "name": "Vey",
        "species": "Human",
        "background": "Sage",
        "class": "Wizard",
        "subclass": "Diviner",
        "level": 16,
    })
    character["species_options"] = {"skill_proficiencies": ["Perception"], "origin_feats": ["Tough"]}
    character["background_options"] = {"primary_ability": "Intelligence", "secondary_ability": "Constitution"}
    character["class_options"] = {
        "class_skills": ["Arcana", "Investigation"],
        "wizard_scholar_skill": "Arcana",
    }
    character["class_options"].update(diviner_savant_choices(data, spellbook))
    character["spells"] = {
        "cantrips": wizard_spell_names(data, {0}, 5),
        "spellbook": spellbook,
        "prepared": spellbook[:21],
        "known": [],
    }
    return character


def test_wizard_spellcasting_tracks_spellbook_and_prepared_limits_independently():
    data = app_data()
    spellcasting = effective_spellcasting(data["classes_by_name"]["Wizard"], level=16)

    assert spellcasting["spellbook_spells"] == 36
    assert spellcasting["prepared_spells"] == 21
    assert "known_spells" not in spellcasting


def test_wizard_prepared_spells_must_be_noncantrips_from_spellbook_and_within_limit():
    data = app_data()
    character = level_sixteen_wizard(data)
    wizard = data["classes_by_name"]["Wizard"]
    spellcasting = effective_spellcasting(wizard, character["subclass"], 16)

    messages = invalid_spell_choice_messages(character, wizard, spellcasting, 16, data["spells"])
    assert messages == []

    outside_spellbook = next(
        spell
        for spell in wizard_spell_names(data, range(1, 9), 45)
        if spell not in character["spells"]["spellbook"]
    )
    character["spells"]["prepared"][-1] = outside_spellbook
    messages = invalid_spell_choice_messages(character, wizard, spellcasting, 16, data["spells"])
    assert f"{outside_spellbook} must be in your Wizard spellbook before it can be prepared" in messages

    character = level_sixteen_wizard(data)
    character["spells"]["prepared"].append(character["spells"]["spellbook"][21])
    report = build_validation_report(character, wizard, spells=data["spells"])
    assert "Choose no more than 21 prepared spells" in report["missing"]

    character = level_sixteen_wizard(data)
    character["spells"]["prepared"][0] = character["spells"]["cantrips"][0]
    messages = invalid_spell_choice_messages(character, wizard, spellcasting, 16, data["spells"])
    assert f"{character['spells']['cantrips'][0]} cannot be a prepared Wizard cantrip" in messages

    character = level_sixteen_wizard(data)
    character["spells"]["spellbook"].append(character["spells"]["spellbook"][0])
    messages = invalid_spell_choice_messages(character, wizard, spellcasting, 16, data["spells"])
    assert "Choose each Wizard spellbook spell only once" in messages


def test_wizard_level_up_adds_spellbook_spells_without_auto_preparing_them():
    data = app_data()
    character = level_sixteen_wizard(data)
    character["level"] = 12
    character["spells"]["cantrips"] = wizard_spell_names(data, {0}, 5)
    character["spells"]["spellbook"] = wizard_spell_names(data, range(1, 7), 28)
    character["spells"]["prepared"] = character["spells"]["spellbook"][:16]
    character["class_options"].update(diviner_savant_choices(data, character["spells"]["spellbook"], max_level=6))
    recalculate_character(character, data)

    draft = create_level_up_draft(character, 13, data)
    spellbook_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "spellbook_spells")
    savant_choice = next(choice for choice in draft["pending_choices"] if choice.get("class_option_key") == "savant_spells_level_13")
    selected = spellbook_choice["options"][:2]
    selected_savant = savant_choice["options"][:1]

    assert resolve_pending_choice(draft, spellbook_choice["id"], selected)
    assert resolve_pending_choice(draft, savant_choice["id"], selected_savant)
    result = commit_level_up_draft(character, draft, data)

    assert result["ok"]
    assert set(selected).issubset(character["spells"]["spellbook"])
    assert set(selected_savant).issubset(character["spells"]["spellbook"])
    assert not set(selected).intersection(character["spells"]["prepared"])
    assert not set(selected_savant).intersection(character["spells"]["prepared"])


@pytest.mark.parametrize(
    ("current_level", "target_level", "existing_spell_levels", "existing_count", "savant_max_level"),
    [
        (12, 13, range(1, 7), 28, 6),
        (14, 15, range(1, 8), 32, 7),
    ],
)
def test_later_wizard_savant_choices_cannot_duplicate_same_level_spellbook_additions(
    current_level,
    target_level,
    existing_spell_levels,
    existing_count,
    savant_max_level,
):
    data = app_data()
    character = level_sixteen_wizard(data)
    character["level"] = current_level
    character["spells"]["spellbook"] = wizard_spell_names(data, existing_spell_levels, existing_count)
    character["spells"]["prepared"] = character["spells"]["spellbook"][:16]
    character["class_options"].update(diviner_savant_choices(data, character["spells"]["spellbook"], max_level=savant_max_level))
    recalculate_character(character, data)

    draft = create_level_up_draft(character, target_level, data)
    spellbook_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "spellbook_spells")
    savant_choice = next(
        choice
        for choice in draft["pending_choices"]
        if choice.get("class_option_key") == f"savant_spells_level_{target_level}"
    )
    duplicate_spell = next(spell for spell in savant_choice["options"] if spell in spellbook_choice["options"])
    other_spell = next(spell for spell in spellbook_choice["options"] if spell != duplicate_spell)

    assert resolve_pending_choice(draft, spellbook_choice["id"], [duplicate_spell, other_spell], spellbook_choice)
    assert resolve_pending_choice(draft, savant_choice["id"], [duplicate_spell], savant_choice)

    refresh_level_up_draft_choices(character, draft, data)
    refreshed_savant = next(
        choice
        for choice in draft["pending_choices"]
        if choice.get("class_option_key") == f"savant_spells_level_{target_level}"
    )

    assert refreshed_savant["status"] == "unresolved"
    assert duplicate_spell not in refreshed_savant["options"]
    assert not draft["can_finalize"]


def test_wizard_later_savant_and_arcane_recovery_progression_are_sheet_values():
    data = app_data()
    character = level_sixteen_wizard(data)
    recalculate_character(character, data)
    sheet = build_character_sheet(character)

    assert character["derived_resources"]["arcane_recovery_levels"] == 8
    assert character["derived_resources"]["arcane_recovery_max_slot_level"] == 5
    assert len(character["class_options"]["savant_spells_level_13"]) == 1
    assert len(character["class_options"]["savant_spells_level_15"]) == 1
    assert set(character["class_options"]["savant_spells_level_13"]).issubset(sheet["spells"]["spellbook"])
    assert set(character["class_options"]["savant_spells_level_15"]).issubset(sheet["spells"]["spellbook"])


def test_wizard_save_migration_moves_legacy_known_spells_into_spellbook():
    saved = {
        "schema_version": 2,
        "name": "Legacy Wizard",
        "class": "Wizard",
        "spells": {
            "cantrips": ["Fire Bolt"],
            "known": ["Burning Hands", "Shield"],
            "prepared": [],
        },
    }

    migrated = migrate_character(saved)

    assert migrated["schema_version"] == CURRENT_SCHEMA_VERSION
    assert migrated["spells"]["spellbook"] == ["Burning Hands", "Shield"]
    assert migrated["spells"]["known"] == []
    assert "Review prepared spells before play." in migrated["migration_warnings"][0]
