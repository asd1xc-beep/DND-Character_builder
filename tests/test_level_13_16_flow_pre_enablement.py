import pytest

from models.character import new_character
from rules.level_up import commit_level_up_draft, create_level_up_draft
from services.character_engine import recalculate_character
from services.character_sheet import build_character_sheet
from tests.test_level_9_12_enablement import human_options, resolve_basic_level_up_choices
from tests.test_level_one_builds import app_data


@pytest.fixture
def enable_level_13_16_for_test(monkeypatch):
    # Keep older test helpers compatible with the enabled production range.
    levels = list(range(1, 17))
    import rules.character_validation as character_validation
    import rules.leveling as leveling

    monkeypatch.setattr(leveling, "SUPPORTED_LEVELS", levels)
    monkeypatch.setattr(character_validation, "SUPPORTED_LEVELS", levels)


def spell_names(data, class_name, levels, count):
    level_set = set(levels)
    names = [
        spell["name"]
        for spell in data["spells"]
        if class_name in spell.get("classes", [])
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


def diviner_savant_options(data, spellbook, through_level):
    options = {}
    excluded = set(spellbook)
    initial = wizard_school_spell_names(data, "D", {1, 2}, 2, excluded)
    options["savant_spells"] = initial
    excluded.update(initial)
    for level, maximum_spell_level in ((5, 3), (7, 4), (9, 5), (11, 6), (13, 7), (15, 8)):
        if level > through_level:
            continue
        spell = wizard_school_spell_names(data, "D", range(1, maximum_spell_level + 1), 1, excluded)[0]
        options[f"savant_spells_level_{level}"] = [spell]
        excluded.add(spell)
    return options


def apply_level(character, target_level, data, asi_ability="Constitution", preferred_spells=None):
    recalculate_character(character, data)
    draft = create_level_up_draft(character, target_level, data)

    assert draft["status"] == "draft", draft
    assert not draft.get("blocked_reason"), draft
    resolve_basic_level_up_choices(draft, asi_ability=asi_ability, preferred_spells=preferred_spells)
    result = commit_level_up_draft(character, draft, data)
    assert result["ok"], result
    recalculate_character(character, data)
    return draft


def level_twelve_champion_fighter():
    character = new_character()
    character.update({
        "name": "Astra",
        "species": "Human",
        "background": "Soldier",
        "class": "Fighter",
        "subclass": "Champion",
        "level": 12,
        "weapon_masteries": ["Longsword", "Longbow", "Dagger", "Shortsword", "Greatsword"],
    })
    character.update(human_options("Strength", "Constitution"))
    character["class_options"] = {
        "class_skills": ["Acrobatics", "Survival"],
        "fighting_style": "Defense",
        "champion_additional_fighting_styles": ["Dueling"],
    }
    character["base_ability_scores"]["Strength"] = 14
    character["base_ability_scores"]["Constitution"] = 14
    return character


def level_twelve_diviner_wizard(data):
    character = new_character()
    character.update({
        "name": "Vey",
        "species": "Human",
        "background": "Sage",
        "class": "Wizard",
        "subclass": "Diviner",
        "level": 12,
    })
    character.update(human_options("Intelligence", "Constitution"))
    spellbook = spell_names(data, "Wizard", {1, 2, 3, 4, 5, 6}, 28)
    character["class_options"] = {
        "class_skills": ["Arcana", "Investigation"],
        "wizard_scholar_skill": "Arcana",
    }
    character["class_options"].update(diviner_savant_options(data, spellbook, 11))
    character["base_ability_scores"]["Intelligence"] = 18
    character["spells"] = {
        "cantrips": spell_names(data, "Wizard", {0}, 5),
        "spellbook": spellbook,
        "known": [],
        "prepared": spell_names(data, "Wizard", {1, 2, 3, 4, 5, 6}, 16),
    }
    return character


def level_twelve_fiend_warlock(data):
    character = new_character()
    character.update({
        "name": "Morrow",
        "species": "Human",
        "background": "Soldier",
        "class": "Warlock",
        "subclass": "Fiend Patron",
        "level": 12,
    })
    character.update(human_options("Charisma", "Dexterity"))
    character["base_ability_scores"]["Charisma"] = 18
    character["class_options"] = {
        "class_skills": ["Arcana", "Investigation"],
        "eldritch_invocations": [
            "Agonizing Blast",
            "Armor of Shadows",
            "Devil's Sight",
            "Eldritch Mind",
            "Fiendish Vigor",
            "Lessons of the First Ones",
            "Mask of Many Faces",
            "One with Shadows",
        ],
        "mystic_arcanum_6": ["Arcane Gate"],
    }
    character["spells"] = {
        "cantrips": spell_names(data, "Warlock", {0}, 4),
        "prepared": spell_names(data, "Warlock", {1, 2, 3, 4, 5}, 11),
        "known": [],
    }
    return character


def level_fourteen_fey_wanderer(data):
    character = new_character()
    character.update({
        "name": "Lio",
        "species": "Human",
        "background": "Guide",
        "class": "Ranger",
        "subclass": "Fey Wanderer",
        "level": 14,
    })
    character.update(human_options("Wisdom", "Dexterity"))
    character["base_ability_scores"]["Wisdom"] = 18
    character["class_options"] = {
        "class_skills": ["Animal Handling", "Nature", "Survival"],
        "fighting_style": "Archery",
        "ranger_deft_explorer_expertise": ["Survival"],
        "ranger_level_9_expertise": ["Animal Handling", "Nature"],
        "ranger_languages": ["Elvish", "Sylvan"],
        "fey_wanderer_skill": "Persuasion",
    }
    character["expertise"] = ["Survival", "Animal Handling", "Nature"]
    character["spells"] = {
        "cantrips": [],
        "prepared": spell_names(data, "Ranger", {1, 2, 3, 4}, 11),
        "known": [],
    }
    return character


def test_fighter_level_thirteen_to_sixteen_flow_is_enabled(enable_level_13_16_for_test):
    data = app_data()
    character = level_twelve_champion_fighter()

    for target_level in range(13, 17):
        draft = apply_level(character, target_level, data, asi_ability="Strength")
        if target_level in {14, 16}:
            assert any(choice["type"] == "asi_or_feat" for choice in draft["pending_choices"])
        if target_level == 16:
            assert any(choice["type"] == "weapon_mastery_selection" for choice in draft["pending_choices"])

    sheet = build_character_sheet(character)

    assert character["level"] == 16
    assert "Superior Critical" in sheet["features"]
    assert len(sheet["weapon_masteries"]) == 6
    assert character["ability_scores"]["Strength"] == 20


def test_diviner_level_thirteen_and_fourteen_flow_adds_spells_and_greater_portent(enable_level_13_16_for_test):
    data = app_data()
    character = level_twelve_diviner_wizard(data)

    level_thirteen = apply_level(character, 13, data)
    level_fourteen = apply_level(character, 14, data)
    sheet = build_character_sheet(character)

    assert any(choice["type"] == "spellbook_spells" for choice in level_thirteen["pending_choices"])
    assert any(choice["type"] == "spellbook_spells" for choice in level_fourteen["pending_choices"])
    assert character["level"] == 14
    assert len(character["spells"]["spellbook"]) == 33
    assert character["class_options"]["savant_spells_level_13"]
    assert sheet["resources"]["portent_dice"] == 3
    assert "Greater Portent" in sheet["features"]


def test_warlock_mystic_arcanum_and_invocation_flow_is_enabled(enable_level_13_16_for_test):
    data = app_data()
    character = level_twelve_fiend_warlock(data)

    level_thirteen = apply_level(character, 13, data)
    apply_level(character, 14, data)
    level_fifteen = apply_level(character, 15, data)
    sheet = build_character_sheet(character)

    assert any(choice.get("class_option_key") == "mystic_arcanum_7" for choice in level_thirteen["pending_choices"])
    assert any(choice.get("class_option_key") == "mystic_arcanum_8" for choice in level_fifteen["pending_choices"])
    assert any(choice.get("class_option_key") == "eldritch_invocations" for choice in level_fifteen["pending_choices"])
    assert {record["spell_level"] for record in character["mystic_arcanum"]} == {6, 7, 8}
    assert len(character["class_options"]["eldritch_invocations"]) == 9
    assert len([
        detail
        for detail in sheet["spell_details"]
        if "Mystic Arcanum" in detail["sources"]
    ]) == 3


def test_fey_wanderer_level_fifteen_flow_adds_misty_wanderer_metadata(enable_level_13_16_for_test):
    data = app_data()
    character = level_fourteen_fey_wanderer(data)

    draft = apply_level(character, 15, data)
    sheet = build_character_sheet(character)
    grant = next(
        grant
        for grant in sheet["spells"]["grant_details"]
        if grant["name"] == "Misty Step"
        and grant["source"].get("source_name") == "Misty Wanderer"
    )

    assert any(feature["name"] == "Misty Wanderer" for feature in draft["automatic_features"])
    assert character["level"] == 15
    assert grant["casting_rules"]["free_casts"] == character["ability_modifiers"]["Wisdom"]
    assert grant["casting_rules"]["can_bring_willing_creature"] is True
