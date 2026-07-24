from models.character import new_character
from rules.character_validation import build_validation_report
from services.character_engine import recalculate_character
from services.character_sheet import build_character_sheet
from services.data_loader import (
    FIVETOOLS_SOURCE,
    by_name,
    load_backgrounds,
    load_beasts,
    load_classes,
    load_equipment,
    load_feats,
    load_rules,
    load_species,
    load_spells,
    load_weapon_masteries,
    load_weapons,
)


def app_data():
    classes = load_classes(FIVETOOLS_SOURCE)
    species = load_species(FIVETOOLS_SOURCE)
    backgrounds = load_backgrounds(FIVETOOLS_SOURCE)
    return {
        "classes": classes,
        "classes_by_name": by_name(classes),
        "species": species,
        "species_by_name": by_name(species),
        "backgrounds": backgrounds,
        "backgrounds_by_name": by_name(backgrounds),
        "feats": load_feats(FIVETOOLS_SOURCE),
        "spells": load_spells(FIVETOOLS_SOURCE),
        "equipment": load_equipment(FIVETOOLS_SOURCE),
        "weapons": load_weapons(FIVETOOLS_SOURCE),
        "weapon_masteries": load_weapon_masteries(FIVETOOLS_SOURCE),
        "beasts": load_beasts(FIVETOOLS_SOURCE),
        "rules": load_rules(FIVETOOLS_SOURCE),
    }


def validate(character, data):
    return build_validation_report(
        character,
        data["classes_by_name"].get(character.get("class"), {}),
        data["species_by_name"].get(character.get("species"), {}),
        data["backgrounds_by_name"].get(character.get("background"), {}),
        data["spells"],
        data["weapons"],
    )


def finalized(character, data):
    recalculate_character(character, data)
    return build_character_sheet(character), validate(character, data)


def feature_details_by_name(sheet):
    return {feature["name"]: feature for feature in sheet.get("feature_details", [])}


def test_human_fighter_level_one_sheet_is_complete():
    data = app_data()
    character = new_character()
    character.update({
        "name": "Astra",
        "species": "Human",
        "background": "Soldier",
        "class": "Fighter",
        "weapon_masteries": ["Longsword", "Longbow", "Dagger"],
    })
    character["species_options"] = {
        "skill_proficiencies": ["Perception"],
        "origin_feats": ["Tough"],
    }
    character["background_options"] = {
        "primary_ability": "Strength",
        "secondary_ability": "Constitution",
        "tool_proficiencies": ["Any gaming set"],
    }
    character["class_options"] = {
        "class_skills": ["Acrobatics", "Survival"],
        "fighting_style": "Defense",
    }
    character["base_ability_scores"]["Constitution"] = 14

    sheet, report = finalized(character, data)

    assert report["complete"]
    assert sheet["core_stats"]["hit_points"]["max"] == 14
    assert "Tough" in sheet["origin_feats"]
    assert sheet["weapon_masteries"] == ["Longsword", "Longbow", "Dagger"]
    details = feature_details_by_name(sheet)
    assert details["Tough"]["description"]
    assert "{@" not in details["Tough"]["description"]
    assert details["Second Wind"]["description"]


def test_elf_wizard_magic_initiate_sheet_is_complete():
    data = app_data()
    character = new_character()
    character.update({
        "name": "Ilyra",
        "species": "Elf",
        "background": "Sage",
        "class": "Wizard",
    })
    character["species_options"] = {
        "skill_proficiencies": ["Perception"],
        "lineage": "High Elf",
        "lineage_spells": ["Choose a cantrip"],
        "lineage_spellcasting_ability": "Intelligence",
    }
    character["background_options"] = {
        "primary_ability": "Intelligence",
        "secondary_ability": "Wisdom",
    }
    character["origin_feat_choices"] = {
        "skills": [],
        "tools": [],
        "cantrips": ["Mage Hand", "Light"],
        "spell": "Shield",
        "spellcasting_ability": "Intelligence",
    }
    character["class_options"] = {"class_skills": ["Investigation", "Religion"]}
    character["spells"] = {
        "cantrips": ["Fire Bolt", "Minor Illusion", "Prestidigitation"],
        "spellbook": ["Burning Hands", "Detect Magic", "Identify", "Mage Armor", "Magic Missile", "Sleep"],
        "known": [],
        "prepared": [],
    }

    sheet, report = finalized(character, data)

    assert report["complete"]
    assert sheet["abilities"][3]["score"] == 12
    assert "Shield" in sheet["spells"]["granted"]
    assert len(sheet["spells"]["spellbook"]) == 6
    spell_details = {spell["name"]: spell for spell in sheet["spell_details"]}
    assert "Shield" in spell_details
    assert "+5 bonus to AC" in spell_details["Shield"]["description"]
    assert "Burning Hands" in spell_details
    assert "{@" not in spell_details["Burning Hands"]["description"]


def test_dwarf_cleric_protector_applies_heavy_armor_and_hp():
    data = app_data()
    character = new_character()
    character.update({
        "name": "Borin",
        "species": "Dwarf",
        "background": "Acolyte",
        "class": "Cleric",
    })
    character["background_options"] = {
        "primary_ability": "Wisdom",
        "secondary_ability": "Charisma",
    }
    character["origin_feat_choices"] = {
        "skills": [],
        "tools": [],
        "cantrips": ["Guidance", "Thaumaturgy"],
        "spell": "Bless",
        "spellcasting_ability": "Wisdom",
    }
    character["class_options"] = {
        "class_skills": ["Medicine", "Persuasion"],
        "divine_order": "Protector",
    }
    character["spells"] = {
        "cantrips": ["Guidance", "Light", "Sacred Flame"],
        "prepared": ["Bless", "Cure Wounds", "Guiding Bolt", "Shield of Faith"],
        "known": [],
    }
    character["base_ability_scores"]["Constitution"] = 14

    sheet, report = finalized(character, data)

    assert report["complete"]
    assert sheet["core_stats"]["hit_points"]["max"] == 11
    assert "Heavy Armor" in sheet["proficiencies"]["armor"]
    assert "Martial Weapons" in sheet["proficiencies"]["weapons"]


def test_rogue_expertise_and_weapon_mastery_are_sheet_ready():
    data = app_data()
    character = new_character()
    character.update({
        "name": "Shade",
        "species": "Halfling",
        "background": "Criminal",
        "class": "Rogue",
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
    stealth = next(skill for skill in sheet["skills"] if skill["name"] == "Stealth")
    assert stealth["expertise"]
    assert sheet["resources"]["sneak_attack"] == "1d6"
    assert "Elvish" in sheet["proficiencies"]["languages"]


def test_warlock_invocation_and_pact_slots_are_sheet_ready():
    data = app_data()
    character = new_character()
    character.update({
        "name": "Vex",
        "species": "Tiefling",
        "background": "Charlatan",
        "class": "Warlock",
    })
    character["species_options"] = {
        "lineage": "Infernal",
        "lineage_spells": ["Fire Bolt"],
        "lineage_spellcasting_ability": "Charisma",
    }
    character["background_options"] = {
        "primary_ability": "Charisma",
        "secondary_ability": "Dexterity",
    }
    character["class_options"] = {
        "class_skills": ["Arcana", "Investigation"],
        "eldritch_invocations": ["Eldritch Mind"],
    }
    character["origin_feat_choices"] = {
        "skills": ["Deception", "Performance", "Persuasion"],
        "tools": [],
        "cantrips": [],
        "spell": "",
        "spellcasting_ability": "",
    }
    character["spells"] = {
        "cantrips": ["Eldritch Blast", "Mage Hand"],
        "prepared": ["Armor of Agathys", "Hex"],
        "known": [],
    }

    sheet, report = finalized(character, data)

    assert report["complete"]
    assert sheet["resources"]["eldritch_invocations"] == 1
    assert sheet["resources"]["spell_slots"] == {"1": 1}
    assert "Eldritch Mind" in sheet["features"]
