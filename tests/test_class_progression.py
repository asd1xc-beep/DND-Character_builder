from models.character import new_character
from rules.character_validation import invalid_spell_choice_messages
from rules.leveling import (
    effective_spellcasting,
    get_available_spell_levels,
    get_cantrip_limit,
    get_class_progression,
    get_class_resources,
    get_known_spell_limit,
    get_prepared_spell_limit,
    get_spell_slots,
)
from tests.test_level_one_builds import app_data, finalized


def test_level_three_spell_progression_comes_from_imported_class_data():
    data = app_data()
    wizard = data["classes_by_name"]["Wizard"]
    cleric = data["classes_by_name"]["Cleric"]
    warlock = data["classes_by_name"]["Warlock"]

    assert get_spell_slots(wizard, 3) == {"1": 4, "2": 2}
    assert get_available_spell_levels(wizard, 3) == [1, 2]
    assert get_cantrip_limit(wizard, 3) == 3
    assert get_prepared_spell_limit(wizard, 3) == 6
    assert get_known_spell_limit(wizard, 3) == 10
    assert get_class_progression(wizard, 3)["spellbook_spells_added"] == 2

    assert effective_spellcasting(wizard, level=3)["spellbook_spells"] == 10
    assert effective_spellcasting(wizard, level=3)["prepared_spells"] == 6
    assert effective_spellcasting(cleric, level=3)["prepared_spells"] == 6
    assert effective_spellcasting(cleric, level=3)["spell_slots"] == {"1": 4, "2": 2}
    assert effective_spellcasting(warlock, level=3)["prepared_spells"] == 4
    assert effective_spellcasting(warlock, level=3)["spell_slots"] == {"2": 2}


def test_subclass_spellcasting_progression_is_level_aware():
    data = app_data()
    fighter = data["classes_by_name"]["Fighter"]
    rogue = data["classes_by_name"]["Rogue"]

    eldritch_knight_level_three = effective_spellcasting(fighter, "Eldritch Knight", 3)
    eldritch_knight_level_eight = effective_spellcasting(fighter, "Eldritch Knight", 8)
    arcane_trickster_level_eight = effective_spellcasting(rogue, "Arcane Trickster", 8)

    assert eldritch_knight_level_three["cantrips_known"] == 2
    assert eldritch_knight_level_three["prepared_spells"] == 3
    assert eldritch_knight_level_three["spell_slots"] == {"1": 2}

    assert eldritch_knight_level_eight["prepared_spells"] == 6
    assert eldritch_knight_level_eight["spell_slots"] == {"1": 4, "2": 2}
    assert eldritch_knight_level_eight["maximum_spell_level"] == 2

    assert arcane_trickster_level_eight["prepared_spells"] == 6
    assert arcane_trickster_level_eight["spell_slots"] == {"1": 4, "2": 2}
    assert arcane_trickster_level_eight["granted_cantrips"] == ["Mage Hand"]


def test_pact_magic_available_spell_levels_include_lower_levels():
    data = app_data()
    warlock = data["classes_by_name"]["Warlock"]

    assert get_available_spell_levels(warlock, 1) == [1]
    assert get_available_spell_levels(warlock, 3) == [1, 2]
    assert get_available_spell_levels(warlock, 5) == [1, 2, 3]
    assert get_available_spell_levels(warlock, 7) == [1, 2, 3, 4]
    assert get_available_spell_levels(warlock, 9) == [1, 2, 3, 4, 5]


def test_pact_magic_validation_allows_lower_level_spells_and_rejects_above_slot_level():
    data = app_data()
    warlock = data["classes_by_name"]["Warlock"]
    spellcasting = effective_spellcasting(warlock, level=3)
    character = new_character()
    character.update({
        "class": "Warlock",
        "level": 3,
        "spells": {
            "cantrips": ["Eldritch Blast", "Mage Hand"],
            "prepared": ["Armor of Agathys", "Hex", "Invisibility", "Misty Step"],
            "known": [],
        },
    })

    messages = invalid_spell_choice_messages(character, warlock, spellcasting, 3, data["spells"])

    assert "Armor of Agathys is not an eligible Level 1 prepared spell" not in messages
    assert "Hex is not an eligible Level 1 prepared spell" not in messages

    character["spells"]["prepared"][-1] = "Counterspell"
    messages = invalid_spell_choice_messages(character, warlock, spellcasting, 3, data["spells"])

    assert "Counterspell is not an eligible Level 3 prepared spell" in messages


def test_level_three_class_resources_use_progression_values():
    data = app_data()

    assert get_class_resources(data["classes_by_name"]["Rogue"], 3)["sneak_attack"] == "2d6"
    assert get_class_resources(data["classes_by_name"]["Warlock"], 3)["eldritch_invocations"] == 3
    assert get_class_resources(data["classes_by_name"]["Warlock"], 3)["pact_slot_level"] == 2
    assert get_class_resources(data["classes_by_name"]["Monk"], 3)["focus_points"] == 3
    assert get_class_resources(data["classes_by_name"]["Sorcerer"], 3)["sorcery_points"] == 3
    assert get_class_resources(data["classes_by_name"]["Bard"], 3)["bardic_die"] == "1d6"
    assert get_class_resources(data["classes_by_name"]["Cleric"], 3)["channel_divinity"] == 2
    assert get_class_resources(data["classes_by_name"]["Druid"], 3)["wild_shape"] == 2
    assert get_class_resources(data["classes_by_name"]["Paladin"], 3)["lay_on_hands_pool"] == 15
    assert get_class_resources(data["classes_by_name"]["Fighter"], 3)["weapon_mastery_count"] == 3


def test_recalculated_level_three_character_receives_progression_resources():
    data = app_data()
    character = new_character()
    character.update({
        "name": "Shade",
        "species": "Halfling",
        "background": "Criminal",
        "class": "Rogue",
        "subclass": "Assassin",
        "level": 3,
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

    sheet, report = finalized(character, data)

    assert report["complete"]
    assert sheet["resources"]["sneak_attack"] == "2d6"
    assert sheet["resources"]["weapon_mastery_count"] == 2


def level_three_wizard_for_spell_validation():
    character = new_character()
    character.update({
        "name": "Ilyra",
        "species": "Dwarf",
        "background": "Farmer",
        "class": "Wizard",
        "level": 3,
    })
    character["background_options"] = {
        "primary_ability": "Intelligence",
        "secondary_ability": "Constitution",
    }
    character["class_options"] = {"class_skills": ["Arcana", "Investigation"]}
    character["spells"] = {
        "cantrips": ["Fire Bolt", "Mage Hand", "Ray of Frost"],
        "spellbook": [
            "Burning Hands",
            "Detect Magic",
            "Feather Fall",
            "Find Familiar",
            "Mage Armor",
            "Magic Missile",
            "Misty Step",
            "Scorching Ray",
            "Shield",
            "Web",
        ],
        "known": [],
        "prepared": [],
    }
    return character


def test_spell_validation_rejects_spells_above_available_level():
    data = app_data()
    character = level_three_wizard_for_spell_validation()
    character["spells"]["spellbook"][-1] = "Fireball"

    _sheet, report = finalized(character, data)

    assert not report["complete"]
    assert "Fireball is not an eligible Level 3 spellbook spell" in report["missing"]


def test_spell_validation_rejects_wrong_class_spell_list():
    data = app_data()
    character = level_three_wizard_for_spell_validation()
    character["spells"]["spellbook"][-1] = "Cure Wounds"

    _sheet, report = finalized(character, data)

    assert not report["complete"]
    assert "Cure Wounds is not on the Wizard spell list" in report["missing"]
