from models.character import new_character
from rules.class_choice_rules import wild_shape_form_options
from services.character_engine import recalculate_character
from services.character_sheet import build_character_sheet
from tests.test_level_one_builds import app_data, finalized


def base_character(class_name, level):
    character = new_character()
    character.update({
        "name": "Phase Four",
        "species": "Human",
        "background": "Soldier",
        "class": class_name,
        "level": level,
    })
    character["species_options"] = {
        "skill_proficiencies": ["Perception"],
        "origin_feats": ["Tough"],
    }
    character["background_options"] = {
        "primary_ability": "Dexterity",
        "secondary_ability": "Constitution",
    }
    character["class_options"] = {"class_skills": ["Athletics", "Survival"]}
    return character


def test_barbarian_fast_movement_applies_unless_heavy_armor_is_worn():
    data = app_data()
    character = base_character("Barbarian", 5)
    character["weapon_masteries"] = ["Greataxe", "Handaxe", "Longsword"]
    character["class_options"]["primal_knowledge_skill"] = ["Nature"]

    recalculate_character(character, data)

    assert character["speed"] == 40
    fast_movement = next(modifier for modifier in character["speed_modifiers"] if modifier["id"] == "barbarian_fast_movement")
    assert fast_movement["applies"] is True

    character["equipment"] = ["Chain Mail"]
    recalculate_character(character, data)
    fast_movement = next(modifier for modifier in character["speed_modifiers"] if modifier["id"] == "barbarian_fast_movement")

    assert character["speed"] == 30
    assert fast_movement["applies"] is False


def test_monk_unarmored_movement_scales_and_respects_armor_and_shield():
    data = app_data()
    monk = base_character("Monk", 10)
    monk["class_options"] = {"class_skills": ["Acrobatics", "Stealth"]}

    recalculate_character(monk, data)

    assert monk["speed"] == 50
    modifier = next(modifier for modifier in monk["speed_modifiers"] if modifier["id"] == "monk_unarmored_movement")
    assert modifier["amount"] == 20
    assert modifier["applies"] is True

    monk["equipment"] = ["Shield"]
    recalculate_character(monk, data)
    modifier = next(modifier for modifier in monk["speed_modifiers"] if modifier["id"] == "monk_unarmored_movement")

    assert monk["speed"] == 30
    assert modifier["applies"] is False


def test_moon_druid_wild_shape_catalog_includes_higher_cr_beasts():
    data = app_data()
    character = base_character("Druid", 9)
    character["subclass"] = "Circle of the Moon"
    character["class_options"] = {
        "class_skills": ["Medicine", "Survival"],
        "primal_order": "Warden",
        "wild_shape_forms": [],
    }

    moon_forms = wild_shape_form_options(character, 9, data["beasts"])
    land_forms = wild_shape_form_options({**character, "subclass": "Circle of the Land"}, 9, data["beasts"])

    assert "Giant Scorpion" in moon_forms
    assert "Ankylosaurus" in moon_forms
    assert "Elephant" not in moon_forms
    assert "Giant Scorpion" not in land_forms
    assert all(beast["creature_type"] == "Beast" for beast in data["beasts"])


def test_spellcasting_source_labels_keep_class_and_subclass_sources_distinct():
    data = app_data()
    bard = base_character("Bard", 10)
    bard["subclass"] = "College of Lore"
    bard["class_options"] = {
        "class_skills": ["Performance", "Persuasion", "Stealth"],
        "bard_expertise": ["Performance", "Persuasion"],
        "bard_level_9_expertise": ["Stealth", "Athletics"],
        "lore_skills": ["Arcana", "History", "Insight"],
        "magical_discoveries": ["Fireball", "Revivify"],
    }
    bard["spells"] = {
        "cantrips": ["Blade Ward", "Dancing Lights", "Mage Hand", "Vicious Mockery"],
        "prepared": [
            "Animal Friendship",
            "Bane",
            "Charm Person",
            "Color Spray",
            "Command",
            "Comprehend Languages",
            "Cure Wounds",
            "Detect Magic",
            "Disguise Self",
            "Dissonant Whispers",
            "Faerie Fire",
            "Feather Fall",
            "Heroism",
            "Invisibility",
            "Cone of Cold",
        ],
        "known": [],
    }

    sheet, _ = finalized(bard, data)

    assert any(source["source_name"] == "Bard Spellcasting" for source in sheet["spells"]["spellcasting_sources"])
    assert not any(source["source_name"] == "College of Lore" and source["source_type"] == "class" for source in sheet["spells"]["spellcasting_sources"])
    assert any(detail["name"] == "Fireball" and "Magical Discoveries" in detail["sources"] for detail in sheet["spell_details"])
