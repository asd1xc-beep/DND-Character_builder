from models.character import new_character
from rules.feature_configurations import update_feature_configuration
from services.character_engine import recalculate_character
from services.character_sheet import build_character_sheet
from tests.test_level_one_builds import app_data, finalized
from tests.test_subclass_structured_choices import level_three_ranger


def test_hunter_feature_configuration_can_change_without_rewriting_history():
    data = app_data()
    character = level_three_ranger("Hunter")
    character["class_options"]["hunters_prey"] = "Colossus Slayer"
    character["level_history"] = [{
        "class": "Ranger",
        "from_level": 2,
        "to_level": 3,
        "resolved_choices": [{"name": "Hunter's Prey", "value": "Colossus Slayer"}],
    }]

    sheet, report = finalized(character, data)
    history_before = list(character["level_history"])
    config = next(config for config in character["feature_configurations"] if config["feature_id"] == "hunters_prey")
    replacement = next(option for option in config["eligible_options"] if option != "Colossus Slayer")

    assert report["complete"]
    assert "Colossus Slayer" in sheet["features"]
    assert update_feature_configuration(character, "hunters_prey", replacement)
    recalculate_character(character, data)
    sheet = build_character_sheet(character)

    assert character["class_options"]["hunters_prey"] == "Colossus Slayer"
    assert character["level_history"] == history_before
    assert replacement in sheet["features"]
    assert "Colossus Slayer" not in sheet["features"]


def test_invalid_feature_configuration_value_is_rejected():
    data = app_data()
    character = level_three_ranger("Hunter")
    character["class_options"]["hunters_prey"] = "Colossus Slayer"
    finalized(character, data)

    assert not update_feature_configuration(character, "hunters_prey", "Not A Real Option")
    assert character["feature_configurations"][0]["current_value"] == "Colossus Slayer"


def test_wild_heart_aspect_configuration_is_created_and_cleared_by_subclass_change():
    data = app_data()
    character = new_character()
    character.update({
        "name": "Tal",
        "species": "Dwarf",
        "background": "Soldier",
        "class": "Barbarian",
        "subclass": "Path of the Wild Heart",
        "level": 6,
    })
    character["background_options"] = {
        "primary_ability": "Strength",
        "secondary_ability": "Constitution",
    }
    character["class_options"] = {
        "class_skills": ["Athletics", "Survival"],
        "primal_knowledge_skill": ["Nature"],
        "aspect_of_the_wilds": "Owl",
    }
    character["weapon_masteries"] = ["Greataxe", "Handaxe"]

    recalculate_character(character, data)

    assert character["feature_configurations"][0]["feature_id"] == "aspect_of_the_wilds"
    assert character["feature_configurations"][0]["current_value"] == "Owl"

    character["subclass"] = "Path of the Berserker"
    recalculate_character(character, data)

    assert character["feature_configurations"] == []


def test_fiendish_resilience_and_third_eye_configurations_are_editable():
    data = app_data()
    warlock = new_character()
    warlock.update({
        "name": "Morrow",
        "species": "Dwarf",
        "background": "Sage",
        "class": "Warlock",
        "subclass": "Fiend Patron",
        "level": 10,
    })
    warlock["background_options"] = {"primary_ability": "Charisma", "secondary_ability": "Dexterity"}
    warlock["class_options"] = {
        "class_skills": ["Arcana", "Investigation"],
        "eldritch_invocations": [
            "Agonizing Blast",
            "Armor of Shadows",
            "Devil's Sight",
            "Eldritch Mind",
            "Fiendish Vigor",
            "Mask of Many Faces",
            "One with Shadows",
        ],
    }
    warlock["spells"] = {
        "cantrips": ["Blade Ward", "Chill Touch", "Eldritch Blast", "Mage Hand"],
        "prepared": [
            "Armor of Agathys",
            "Arms of Hadar",
            "Bane",
            "Charm Person",
            "Comprehend Languages",
            "Detect Magic",
            "Expeditious Retreat",
            "Hellish Rebuke",
            "Hex",
            "Illusory Script",
        ],
        "known": [],
    }

    recalculate_character(warlock, data)
    config = next(config for config in warlock["feature_configurations"] if config["feature_id"] == "fiendish_resilience_damage_type")

    assert config["current_value"] == "Fire"
    assert config["change_timing"] == "short_or_long_rest"
    assert update_feature_configuration(warlock, "fiendish_resilience_damage_type", "Cold")

    wizard = new_character()
    wizard.update({
        "name": "Vey",
        "species": "Human",
        "background": "Sage",
        "class": "Wizard",
        "subclass": "Diviner",
        "level": 10,
    })
    wizard["background_options"] = {"primary_ability": "Intelligence", "secondary_ability": "Constitution"}
    wizard["class_options"] = {"class_skills": ["Arcana", "Investigation"], "wizard_scholar_skill": "Arcana"}
    wizard["spells"] = {
        "cantrips": ["Fire Bolt", "Light", "Mage Hand", "Minor Illusion", "Prestidigitation"],
        "spellbook": [
            "Burning Hands",
            "Charm Person",
            "Detect Magic",
            "Feather Fall",
            "Mage Armor",
            "Magic Missile",
        ],
        "known": [],
        "prepared": [],
    }

    recalculate_character(wizard, data)
    config = next(config for config in wizard["feature_configurations"] if config["feature_id"] == "third_eye_mode")

    assert config["eligible_options"] == ["Darkvision", "Greater Comprehension", "See Invisibility"]
    assert update_feature_configuration(wizard, "third_eye_mode", "See Invisibility")
