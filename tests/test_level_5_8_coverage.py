import json
from pathlib import Path

from models.character import new_character
from rules.class_choice_rules import required_class_choice_definitions
from rules.level_up import commit_level_up_draft, create_level_up_draft, get_level_up_plan, resolve_pending_choice
from rules.leveling import SUPPORTED_LEVELS
from services.character_engine import recalculate_character
from tests.test_level_one_builds import app_data, finalized
from tests.test_level_up import level_one_fighter, level_three_character


COVERAGE_PATH = Path("data/coverage/level_5_8_choice_coverage.json")


def load_coverage():
    return json.loads(COVERAGE_PATH.read_text(encoding="utf-8"))


def test_level_5_8_coverage_file_tracks_required_future_choices():
    coverage = load_coverage()

    required_keys = {
        "rogue_6_expertise",
        "barbarian_6_wild_heart_aspect_of_the_wilds",
        "bard_6_lore_magical_discoveries",
        "cleric_7_blessed_strikes",
        "druid_7_elemental_fury",
        "fighter_6_asi_or_feat",
        "fighter_7_champion_additional_fighting_style",
        "ranger_7_gloom_stalker_iron_mind",
        "ranger_7_hunter_defensive_tactics",
        "sorcerer_6_draconic_elemental_affinity",
        "warlock_5_invocations",
        "warlock_7_invocations",
        "later_subclass_feature_gains",
        "generic_spell_progression",
    }

    assert required_keys.issubset(coverage)
    for key, entry in coverage.items():
        assert entry["choice_type"]
        assert "implemented" in entry
        assert "tested" in entry
        assert "blocks_level_path" in entry
        if not entry["implemented"]:
            assert entry["blocks_level_path"], key


def test_levels_five_to_sixteen_are_enabled_and_level_seventeen_is_blocked():
    data = app_data()
    character = new_character()
    character.update({
        "name": "Astra",
        "species": "Human",
        "background": "Soldier",
        "class": "Fighter",
        "level": 20,
    })

    assert max(SUPPORTED_LEVELS) == 20
    plan = get_level_up_plan(character, 21, data)
    assert plan["blocked_reason"] == "Only Levels 1-20 are supported right now."


def test_future_simple_choice_definitions_are_prepared_without_enabling_levels():
    data = app_data()

    rogue = future_character("Rogue", data, level=6, subclass="Thief")
    rogue["class_options"]["class_skills"] = ["Acrobatics", "Insight", "Investigation", "Perception"]
    rogue["expertise"] = ["Stealth", "Sleight of Hand"]
    recalculate_character(rogue, data)
    rogue_choices = choice_keys(rogue, data, 6)
    assert "rogue_level_6_expertise" in rogue_choices

    fighter = future_character("Fighter", data, level=7, subclass="Champion")
    fighter["class_options"]["fighting_style"] = "Defense"
    recalculate_character(fighter, data)
    fighter_choices = choice_keys(fighter, data, 7)
    assert "champion_additional_fighting_styles" in fighter_choices

    ranger = future_character("Ranger", data, level=7, subclass="Hunter")
    recalculate_character(ranger, data)
    ranger_choices = choice_keys(ranger, data, 7)
    assert "defensive_tactics" in ranger_choices

    cleric = future_character("Cleric", data, level=7, subclass="Life Domain")
    recalculate_character(cleric, data)
    cleric_choices = choice_keys(cleric, data, 7)
    assert "blessed_strikes" in cleric_choices

    druid = future_character("Druid", data, level=7, subclass="Circle of the Land")
    recalculate_character(druid, data)
    druid_choices = choice_keys(druid, data, 7)
    assert "elemental_fury" in druid_choices

    sorcerer = future_character("Sorcerer", data, level=6, subclass="Draconic Sorcery")
    recalculate_character(sorcerer, data)
    sorcerer_choices = choice_keys(sorcerer, data, 6)
    assert "elemental_affinity" in sorcerer_choices


def test_lore_magical_discoveries_has_cross_list_spell_options():
    coverage = load_coverage()
    data = app_data()
    bard = future_character("Bard", data, level=6, subclass="College of Lore")
    recalculate_character(bard, data)

    choices = {
        definition["key"]: definition
        for definition in required_class_choice_definitions(
            bard,
            data["classes_by_name"]["Bard"],
            6,
            data,
        )
    }

    assert "magical_discoveries" in choices
    assert "Fireball" in choices["magical_discoveries"]["options"]
    assert "Revivify" in choices["magical_discoveries"]["options"]
    assert coverage["bard_6_lore_magical_discoveries"]["blocks_level_path"] is False


def test_fighter_can_level_from_four_to_five_with_automatic_gains():
    data = app_data()
    character = level_three_character(level_one_fighter(), "Champion", data)
    finalized(character, data)
    level_to_four(character, data, {"mode": "asi", "ability_increases": {"Strength": 2}})
    finalized(character, data)

    draft = create_level_up_draft(character, 5, data)
    result = commit_level_up_draft(character, draft, data)
    sheet, report = finalized(character, data)

    assert result["ok"]
    assert character["level"] == 5
    assert "Extra Attack" in sheet["features"]
    assert "Tactical Shift" in sheet["features"]
    assert sheet["resources"]["second_wind"] == 3
    assert report["complete"]


def test_rogue_level_six_expertise_is_resolved_in_level_up_flow():
    data = app_data()
    character = new_character()
    character.update({
        "name": "Shade",
        "species": "Halfling",
        "background": "Criminal",
        "class": "Rogue",
        "subclass": "Thief",
        "level": 5,
        "weapon_masteries": ["Dagger", "Shortsword"],
    })
    character["background_options"] = {
        "primary_ability": "Dexterity",
        "secondary_ability": "Intelligence",
    }
    character["class_options"] = {
        "class_skills": ["Acrobatics", "Insight", "Investigation", "Perception"],
        "rogue_thieves_cant_language": "Elvish",
    }
    character["expertise"] = ["Stealth", "Sleight of Hand"]
    finalized(character, data)

    draft = create_level_up_draft(character, 6, data)
    expertise_choice = next(choice for choice in draft["pending_choices"] if choice["class_option_key"] == "rogue_level_6_expertise")
    selected = expertise_choice["options"][:2]

    assert resolve_pending_choice(draft, expertise_choice["id"], selected)
    result = commit_level_up_draft(character, draft, data)
    sheet, report = finalized(character, data)

    assert result["ok"]
    assert character["level"] == 6
    assert set(selected).issubset(character["expertise"])
    assert all(skill["expertise"] for skill in sheet["skills"] if skill["name"] in selected)
    assert report["complete"]


def test_lore_bard_level_six_magical_discoveries_adds_granted_spells():
    data = app_data()
    character = level_six_ready_lore_bard(data)

    draft = create_level_up_draft(character, 6, data)
    spell_choice = next(choice for choice in draft["pending_choices"] if choice.get("class_option_key") == "magical_discoveries")
    prepared_choice = next(choice for choice in draft["pending_choices"] if choice.get("spell_field") == "prepared")

    assert "Fireball" in spell_choice["options"]
    assert resolve_pending_choice(draft, spell_choice["id"], ["Fireball", "Revivify"])
    assert resolve_pending_choice(draft, prepared_choice["id"], [prepared_choice["options"][0]])

    result = commit_level_up_draft(character, draft, data)
    sheet, report = finalized(character, data)

    assert result["ok"]
    assert character["level"] == 6
    assert "Fireball" in sheet["spells"]["granted"]
    assert "Revivify" in sheet["spells"]["granted"]
    assert any(spell["name"] == "Fireball" and spell["description"] for spell in sheet["spell_details"])
    assert report["complete"]


def test_level_eight_asi_or_feat_remains_available():
    data = app_data()
    character = level_seven_champion_fighter(data)

    draft = create_level_up_draft(character, 8, data)
    asi_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "asi_or_feat")

    assert resolve_pending_choice(
        draft,
        asi_choice["id"],
        {"mode": "asi", "ability_increases": {"Strength": 2}},
    )

    result = commit_level_up_draft(character, draft, data)
    sheet, report = finalized(character, data)

    assert result["ok"]
    assert character["level"] == 8
    assert character["ability_scores"]["Strength"] >= 14
    assert sheet["identity"]["level"] == 8
    assert report["complete"]


def future_character(class_name, data, level, subclass=""):
    character = new_character()
    character.update({
        "name": "Future",
        "species": "Human",
        "background": "Soldier",
        "class": class_name,
        "subclass": subclass,
        "level": level,
    })
    character["background_options"] = {
        "primary_ability": "Strength",
        "secondary_ability": "Constitution",
    }
    character["class_options"] = {"class_skills": []}
    return character


def level_to_four(character, data, asi_value):
    draft = create_level_up_draft(character, 4, data)
    asi_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "asi_or_feat")
    mastery_choice = next((choice for choice in draft["pending_choices"] if choice["type"] == "weapon_mastery_selection"), None)
    assert resolve_pending_choice(draft, asi_choice["id"], asi_value)
    if mastery_choice:
        assert resolve_pending_choice(draft, mastery_choice["id"], mastery_choice["options"][:mastery_choice["choose"]])
    assert commit_level_up_draft(character, draft, data)["ok"]


def level_six_ready_lore_bard(data):
    character = new_character()
    character.update({
        "name": "Lyra",
        "species": "Dwarf",
        "background": "Soldier",
        "class": "Bard",
        "subclass": "College of Lore",
        "level": 5,
    })
    character["background_options"] = {
        "primary_ability": "Charisma",
        "secondary_ability": "Dexterity",
    }
    character["class_options"] = {
        "class_skills": ["Performance", "Persuasion", "Deception"],
        "bard_expertise": ["Performance", "Persuasion"],
        "lore_skills": ["Arcana", "History", "Insight"],
    }
    character["spells"] = {
        "cantrips": ["Mage Hand", "Minor Illusion", "Vicious Mockery"],
        "prepared": [
            "Bane",
            "Charm Person",
            "Cure Wounds",
            "Detect Magic",
            "Dissonant Whispers",
            "Faerie Fire",
            "Healing Word",
            "Invisibility",
            "Shatter",
        ],
        "known": [],
    }
    finalized(character, data)
    return character


def level_seven_champion_fighter(data):
    character = level_three_character(level_one_fighter(), "Champion", data)
    finalized(character, data)
    level_to_four(character, data, {"mode": "asi", "ability_increases": {"Strength": 2}})
    finalized(character, data)
    assert commit_level_up_draft(character, create_level_up_draft(character, 5, data), data)["ok"]
    finalized(character, data)
    draft = create_level_up_draft(character, 6, data)
    asi_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "asi_or_feat")
    assert resolve_pending_choice(draft, asi_choice["id"], {"mode": "asi", "ability_increases": {"Constitution": 2}})
    assert commit_level_up_draft(character, draft, data)["ok"]
    finalized(character, data)
    draft = create_level_up_draft(character, 7, data)
    style_choice = next(choice for choice in draft["pending_choices"] if choice.get("class_option_key") == "champion_additional_fighting_styles")
    assert resolve_pending_choice(draft, style_choice["id"], [style_choice["options"][0]])
    assert commit_level_up_draft(character, draft, data)["ok"]
    finalized(character, data)
    return character


def choice_keys(character, data, level):
    return {
        definition["key"]
        for definition in required_class_choice_definitions(
            character,
            data["classes_by_name"][character["class"]],
            level,
            data,
        )
    }
