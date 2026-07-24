import json

import pytest

from models.character import new_character
from rules.feature_configurations import update_feature_configuration
from rules.level_up import (
    commit_level_up_draft,
    create_level_up_draft,
    refresh_level_up_draft_choices,
    resolve_pending_choice,
)
from services.character_engine import recalculate_character
from services.character_sheet import build_character_sheet
from services.save_load import migrate_character
from tests.test_level_one_builds import app_data


@pytest.fixture
def enable_level_17_20_for_test(monkeypatch):
    levels = list(range(1, 21))
    import rules.character_validation as character_validation
    import rules.leveling as leveling

    monkeypatch.setattr(leveling, "SUPPORTED_LEVELS", levels)
    monkeypatch.setattr(character_validation, "SUPPORTED_LEVELS", levels)


def wizard_spell_names(data, levels, count, casting_time=None, exclude=None):
    excluded = set(exclude or [])
    level_set = set(levels)
    names = [
        spell["name"]
        for spell in data["spells"]
        if "Wizard" in spell.get("classes", [])
        and spell.get("level") in level_set
        and (casting_time is None or spell.get("casting_time") == casting_time)
        and spell["name"] not in excluded
    ]
    assert len(names) >= count
    return names[:count]


def level_seventeen_wizard(data):
    spellbook = [
        "Magic Missile",
        "Shield",
        "Blur",
        "Misty Step",
        *wizard_spell_names(data, range(1, 10), 34, exclude={"Magic Missile", "Shield", "Blur", "Misty Step"}),
    ]
    character = new_character()
    character.update({
        "name": "Master Wizard",
        "species": "Human",
        "background": "Sage",
        "class": "Wizard",
        "subclass": "Evoker",
        "level": 17,
    })
    character["background_options"] = {
        "primary_ability": "Intelligence",
        "secondary_ability": "Constitution",
    }
    character["species_options"] = {
        "skill_proficiencies": ["Perception"],
        "origin_feats": ["Tough"],
    }
    character["class_options"] = {
        "class_skills": ["Arcana", "Investigation"],
        "wizard_scholar_skill": "Arcana",
    }
    character["base_ability_scores"]["Intelligence"] = 18
    character["spells"] = {
        "cantrips": wizard_spell_names(data, {0}, 5),
        "spellbook": spellbook,
        "known": [],
        "prepared": spellbook[:22],
    }
    return character


def test_wizard_level_eighteen_spell_mastery_choice_is_required_and_sheet_ready(enable_level_17_20_for_test):
    data = app_data()
    character = level_seventeen_wizard(data)
    recalculate_character(character, data)

    draft = create_level_up_draft(character, 18, data)
    spellbook_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "spellbook_spells")
    mastery_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "spell_mastery_selection")
    savant_choice = next(
        choice
        for choice in draft["pending_choices"]
        if choice.get("class_option_key", "").endswith("savant_spells")
    )

    assert "Magic Missile" in mastery_choice["level_1_options"]
    assert "Blur" in mastery_choice["level_2_options"]
    assert "Shield" not in mastery_choice["level_1_options"]
    assert "Misty Step" not in mastery_choice["level_2_options"]

    assert not resolve_pending_choice(
        draft,
        mastery_choice["id"],
        {"level_1": "Shield", "level_2": "Misty Step"},
        mastery_choice,
    )
    assert resolve_pending_choice(draft, spellbook_choice["id"], spellbook_choice["options"][:2], spellbook_choice)
    refresh_level_up_draft_choices(character, draft, data)
    savant_choice = next(
        choice
        for choice in draft["pending_choices"]
        if choice.get("class_option_key", "").endswith("savant_spells")
    )
    assert not set(savant_choice["options"][:2]).intersection(spellbook_choice["options"][:2])
    assert resolve_pending_choice(draft, savant_choice["id"], savant_choice["options"][:2], savant_choice)
    assert resolve_pending_choice(
        draft,
        mastery_choice["id"],
        {"level_1": "Magic Missile", "level_2": "Blur"},
        mastery_choice,
    )

    result = commit_level_up_draft(character, draft, data)
    assert result["ok"], result

    recalculate_character(character, data)
    history_before = json.loads(json.dumps(character["level_history"]))
    level_1_config = next(config for config in character["feature_configurations"] if config["feature_id"] == "spell_mastery_level_1")
    level_2_config = next(config for config in character["feature_configurations"] if config["feature_id"] == "spell_mastery_level_2")
    sheet = build_character_sheet(character)
    grants = {
        grant["name"]: grant
        for grant in sheet["spells"]["grant_details"]
        if grant["source"].get("source_name") == "Spell Mastery"
    }
    spell_sources = {detail["name"]: detail["sources"] for detail in sheet["spell_details"]}

    assert character["class_options"]["spell_mastery_level_1"] == "Magic Missile"
    assert character["class_options"]["spell_mastery_level_2"] == "Blur"
    assert level_1_config["current_value"] == "Magic Missile"
    assert level_1_config["change_timing"] == "long_rest"
    assert "Magic Missile" in level_1_config["eligible_options"]
    assert "Shield" not in level_1_config["eligible_options"]
    assert level_2_config["current_value"] == "Blur"
    assert level_2_config["change_timing"] == "long_rest"
    assert "Blur" in level_2_config["eligible_options"]
    assert "Misty Step" not in level_2_config["eligible_options"]
    assert set(grants) == {"Magic Missile", "Blur"}
    assert grants["Magic Missile"]["always_prepared"] is True
    assert grants["Magic Missile"]["casting_rules"]["at_will_lowest_level"] is True
    assert "Spell Mastery" in spell_sources["Magic Missile"]
    assert "Spell Mastery" in spell_sources["Blur"]

    replacement = next(option for option in level_1_config["eligible_options"] if option != "Magic Missile")
    assert not update_feature_configuration(character, "spell_mastery_level_1", "Shield")
    assert update_feature_configuration(character, "spell_mastery_level_1", replacement)
    recalculate_character(character, data)
    sheet = build_character_sheet(character)
    grants = {
        grant["name"]: grant
        for grant in sheet["spells"]["grant_details"]
        if grant["source"].get("source_name") == "Spell Mastery"
    }

    assert character["class_options"]["spell_mastery_level_1"] == "Magic Missile"
    assert character["level_history"] == history_before
    assert set(grants) == {replacement, "Blur"}
    assert grants[replacement]["casting_rules"]["at_will_lowest_level"] is True

    loaded = migrate_character(json.loads(json.dumps(character)))
    recalculate_character(loaded, data)
    loaded_config = next(config for config in loaded["feature_configurations"] if config["feature_id"] == "spell_mastery_level_1")

    assert loaded_config["current_value"] == replacement


def test_wizard_spell_mastery_can_use_spellbook_spells_added_in_same_draft(enable_level_17_20_for_test):
    data = app_data()
    character = level_seventeen_wizard(data)
    new_mastery_spell = "Magic Missile"
    character["spells"]["spellbook"] = [
        spell for spell in character["spells"]["spellbook"] if spell != new_mastery_spell
    ]
    character["spells"]["prepared"] = [
        spell for spell in character["spells"]["prepared"] if spell != new_mastery_spell
    ]
    recalculate_character(character, data)

    draft = create_level_up_draft(character, 18, data)
    spellbook_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "spellbook_spells")
    mastery_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "spell_mastery_selection")
    other_spell = next(spell for spell in spellbook_choice["options"] if spell != new_mastery_spell)

    assert new_mastery_spell not in mastery_choice["level_1_options"]
    assert resolve_pending_choice(draft, spellbook_choice["id"], [new_mastery_spell, other_spell], spellbook_choice)

    refresh_level_up_draft_choices(character, draft, data)
    refreshed_mastery = next(choice for choice in draft["pending_choices"] if choice["type"] == "spell_mastery_selection")

    assert new_mastery_spell in refreshed_mastery["level_1_options"]
    assert resolve_pending_choice(
        draft,
        refreshed_mastery["id"],
        {"level_1": new_mastery_spell, "level_2": "Blur"},
        refreshed_mastery,
    )
