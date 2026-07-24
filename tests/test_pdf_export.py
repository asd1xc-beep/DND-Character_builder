from pypdf import PdfReader

from models.character import new_character
from services.pdf_export import build_wotc_field_values, export_character_pdf, spells_grouped_by_level
from tests.test_level_one_builds import app_data, finalized


def test_wotc_pdf_export_fills_core_fields():
    data = app_data()
    character = new_character()
    character.update({
        "name": "PDF Test",
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

    path = export_character_pdf(sheet)
    fields = PdfReader(str(path)).get_fields()

    assert fields["CharacterName"].get("/V") == "PDF Test"
    assert fields["ClassLevel"].get("/V") == "Fighter 1"
    assert fields["Race "].get("/V") == "Human"
    assert fields["Background"].get("/V") == "Soldier"
    assert fields["HPMax"].get("/V") == "14"
    assert fields["CON"].get("/V") == "15"
    features = fields["Features and Traits"].get("/V")
    assert "Tough:" in features
    assert "Weapon mastery:" in features
    assert "Longsword" in features
    assert "Longbow" in features
    assert "Dagger" in features


def test_wotc_pdf_attack_rows_use_structured_profiles_and_blank_large_field():
    sheet = {
        "identity": {
            "name": "Attack Rows",
            "class": "Wizard",
            "level": 1,
            "background": "Sage",
            "species": "Human",
            "speed": 30,
        },
        "core_stats": {
            "proficiency_bonus_display": "+2",
            "armor_class": 12,
            "initiative_display": "+2",
            "hit_points": {"max": 8, "current": 8},
            "hit_die": "d6",
        },
        "abilities": [
            {"name": "Strength", "score": 16, "modifier_display": "+3"},
            {"name": "Dexterity", "score": 14, "modifier_display": "+2"},
            {"name": "Constitution", "score": 10, "modifier_display": "+0"},
            {"name": "Intelligence", "score": 16, "modifier_display": "+3"},
            {"name": "Wisdom", "score": 10, "modifier_display": "+0"},
            {"name": "Charisma", "score": 10, "modifier_display": "+0"},
        ],
        "saving_throws": [
            {"name": "Strength", "bonus_display": "+3"},
            {"name": "Dexterity", "bonus_display": "+2"},
            {"name": "Constitution", "bonus_display": "+0"},
            {"name": "Intelligence", "bonus_display": "+5"},
            {"name": "Wisdom", "bonus_display": "+0"},
            {"name": "Charisma", "bonus_display": "+0"},
        ],
        "skills": [
            {"name": "Acrobatics", "bonus": 2, "bonus_display": "+2"},
            {"name": "Animal Handling", "bonus": 0, "bonus_display": "+0"},
            {"name": "Arcana", "bonus": 5, "bonus_display": "+5"},
            {"name": "Athletics", "bonus": 3, "bonus_display": "+3"},
            {"name": "Deception", "bonus": 0, "bonus_display": "+0"},
            {"name": "History", "bonus": 3, "bonus_display": "+3"},
            {"name": "Insight", "bonus": 0, "bonus_display": "+0"},
            {"name": "Intimidation", "bonus": 0, "bonus_display": "+0"},
            {"name": "Investigation", "bonus": 3, "bonus_display": "+3"},
            {"name": "Medicine", "bonus": 0, "bonus_display": "+0"},
            {"name": "Nature", "bonus": 3, "bonus_display": "+3"},
            {"name": "Perception", "bonus": 0, "bonus_display": "+0"},
            {"name": "Performance", "bonus": 0, "bonus_display": "+0"},
            {"name": "Persuasion", "bonus": 0, "bonus_display": "+0"},
            {"name": "Religion", "bonus": 3, "bonus_display": "+3"},
            {"name": "Sleight of Hand", "bonus": 2, "bonus_display": "+2"},
            {"name": "Stealth", "bonus": 2, "bonus_display": "+2"},
            {"name": "Survival", "bonus": 0, "bonus_display": "+0"},
        ],
        "proficiencies": {"armor": [], "weapons": [], "tools": [], "languages": []},
        "equipment": ["Longsword"],
        "features": [],
        "feature_details": [],
        "origin_feats": [],
        "general_feats": [],
        "weapon_masteries": [],
        "spells": {
            "cantrips": ["Minor Illusion"],
            "known": [],
            "prepared": [],
            "spellbook": [],
            "granted": [],
            "spellcasting_ability": "Intelligence",
        },
        "spell_details": [
            {
                "name": "Minor Illusion",
                "description": "You create a sound or an image of an object within range.",
            }
        ],
        "resources": {},
        "attack_profiles": [
            {"name": "Longsword", "attack_display": "+5", "damage_display": "1d8+3 Slashing", "kind": "weapon"},
            {"name": "Fire Bolt", "attack_display": "+5", "damage_display": "1d10 Fire", "kind": "cantrip"},
        ],
    }

    values = build_wotc_field_values(sheet)

    assert values["AttacksSpellcasting"] == ""
    assert "Minor Illusion" not in values["AttacksSpellcasting"]
    assert "You create a sound" not in values["AttacksSpellcasting"]
    assert values["Wpn Name"] == "Longsword"
    assert values["Wpn1 AtkBonus"] == "+5"
    assert values["Wpn1 Damage"] == "1d8+3 Slashing"
    assert values["Wpn Name 2"] == "Fire Bolt"
    assert values["Wpn2 AtkBonus "] == "+5"
    assert values["Wpn2 Damage "] == "1d10 Fire"
    assert values["Wpn Name 3"] == ""
    assert values["Wpn3 AtkBonus  "] == ""
    assert values["Wpn3 Damage "] == ""


def test_wotc_pdf_spell_fields_use_spell_levels():
    sheet = {
        "identity": {
            "name": "Bard Test",
            "class": "Bard",
            "level": 8,
            "background": "Entertainer",
            "species": "Human",
            "speed": 30,
        },
        "core_stats": {
            "proficiency_bonus_display": "+3",
            "armor_class": 14,
            "initiative_display": "+2",
            "hit_points": {"max": 51, "current": 51},
            "hit_die": "d8",
        },
        "abilities": [
            {"name": "Strength", "score": 10, "modifier_display": "+0"},
            {"name": "Dexterity", "score": 14, "modifier_display": "+2"},
            {"name": "Constitution", "score": 14, "modifier_display": "+2"},
            {"name": "Intelligence", "score": 10, "modifier_display": "+0"},
            {"name": "Wisdom", "score": 12, "modifier_display": "+1"},
            {"name": "Charisma", "score": 18, "modifier_display": "+4"},
        ],
        "saving_throws": [
            {"name": "Strength", "bonus_display": "+0"},
            {"name": "Dexterity", "bonus_display": "+5"},
            {"name": "Constitution", "bonus_display": "+2"},
            {"name": "Intelligence", "bonus_display": "+0"},
            {"name": "Wisdom", "bonus_display": "+1"},
            {"name": "Charisma", "bonus_display": "+7"},
        ],
        "skills": [
            {"name": "Acrobatics", "bonus": 2, "bonus_display": "+2"},
            {"name": "Animal Handling", "bonus": 1, "bonus_display": "+1"},
            {"name": "Arcana", "bonus": 0, "bonus_display": "+0"},
            {"name": "Athletics", "bonus": 0, "bonus_display": "+0"},
            {"name": "Deception", "bonus": 7, "bonus_display": "+7"},
            {"name": "History", "bonus": 0, "bonus_display": "+0"},
            {"name": "Insight", "bonus": 1, "bonus_display": "+1"},
            {"name": "Intimidation", "bonus": 4, "bonus_display": "+4"},
            {"name": "Investigation", "bonus": 0, "bonus_display": "+0"},
            {"name": "Medicine", "bonus": 1, "bonus_display": "+1"},
            {"name": "Nature", "bonus": 0, "bonus_display": "+0"},
            {"name": "Perception", "bonus": 1, "bonus_display": "+1"},
            {"name": "Performance", "bonus": 7, "bonus_display": "+7"},
            {"name": "Persuasion", "bonus": 7, "bonus_display": "+7"},
            {"name": "Religion", "bonus": 0, "bonus_display": "+0"},
            {"name": "Sleight of Hand", "bonus": 2, "bonus_display": "+2"},
            {"name": "Stealth", "bonus": 2, "bonus_display": "+2"},
            {"name": "Survival", "bonus": 1, "bonus_display": "+1"},
        ],
        "proficiencies": {"armor": [], "weapons": [], "tools": [], "languages": []},
        "equipment": [],
        "features": [],
        "feature_details": [],
        "origin_feats": [],
        "general_feats": [],
        "weapon_masteries": [],
        "resources": {"spell_slots": {"1": 4, "2": 3, "3": 3, "4": 2}},
        "spells": {
            "cantrips": ["Vicious Mockery"],
            "known": [],
            "prepared": ["Bane", "Invisibility", "Hypnotic Pattern", "Hallucinatory Terrain"],
            "granted": [],
            "spellcasting_ability": "Charisma",
        },
        "spell_details": [
            {"name": "Vicious Mockery", "level": 0, "description": ""},
            {"name": "Bane", "level": 1, "description": ""},
            {"name": "Invisibility", "level": 2, "description": ""},
            {"name": "Hypnotic Pattern", "level": 3, "description": ""},
            {"name": "Hallucinatory Terrain", "level": 4, "description": ""},
        ],
    }

    grouped = spells_grouped_by_level(sheet)
    values = build_wotc_field_values(sheet)

    assert grouped[4] == ["Hallucinatory Terrain"]
    assert values["Spells 1023"] == "Bane"
    assert values["Spells 1034"] == "Invisibility"
    assert values["Spells 1047"] == "Hypnotic Pattern"
    assert values["Spells 1060"] == "Hallucinatory Terrain"
    assert values["SlotsTotal 22"] == "2"
