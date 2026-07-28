from copy import deepcopy
from uuid import uuid4


ABILITIES = ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]


DEFAULT_CHARACTER = {
    "schema_version": 5,
    "character_id": "",
    "name": "",
    "level": 1,
    "class_levels": {},
    "notes": "",
    "species": "",
    "species_traits": [],
    "size": "",
    "background": "",
    "background_feature": "",
    "class": "",
    "subclass": "",
    "ability_scores": {
        "Strength": 10,
        "Dexterity": 10,
        "Constitution": 10,
        "Intelligence": 10,
        "Wisdom": 10,
        "Charisma": 10
    },
    "base_ability_scores": {
        "Strength": 10,
        "Dexterity": 10,
        "Constitution": 10,
        "Intelligence": 10,
        "Wisdom": 10,
        "Charisma": 10
    },
    "ability_score_bonuses": {
        "Strength": 0,
        "Dexterity": 0,
        "Constitution": 0,
        "Intelligence": 0,
        "Wisdom": 0,
        "Charisma": 0
    },
    "ability_modifiers": {},
    "ability_score_method": "Manual entry",
    "ability_score_assignments": {},
    "rolled_ability_scores": [],
    "proficiency_bonus": 2,
    "saving_throw_proficiencies": [],
    "skill_proficiencies": [],
    "expertise": [],
    "saving_throw_bonuses": {},
    "skill_bonuses": {},
    "armor_proficiencies": [],
    "weapon_proficiencies": [],
    "tool_proficiencies": [],
    "languages": [],
    "features": [],
    "pending_choices": [],
    "feature_configurations": [],
    "level_history": [],
    "completed_level_up_transactions": [],
    "hit_dice": {},
    "hp_rolls": [],
    "hp_history": [],
    "class_options": {},
    "species_options": {},
    "background_options": {},
    "origin_feats": [],
    "general_feats": [],
    "ability_score_adjustments": [],
    "derived_resources": {},
    "weapon_masteries": [],
    "origin_feat_choices": {
        "skills": [],
        "tools": [],
        "cantrips": [],
        "spell": "",
        "spellcasting_ability": ""
    },
    "spells": {
        "cantrips": [],
        "prepared": [],
        "known": [],
        "spellbook": []
    },
    "include_default_equipment": True,
    "custom_equipment": [],
    "equipment": [],
    "equipment_migration_pending": False,
    "presentation_preferences": {
        "primary_weapon": "",
        "featured_cantrip": "",
        "weapon_wielding_modes": {}
    },
    "import_provenance": {},
    "import_overrides": {
        "maximum_hp_adjustment": 0
    },
    "pdf_passthrough_fields": {},
    "hit_points": {
        "max": 0,
        "maximum": 0,
        "current": 0,
        "temporary": 0,
        "hit_die": ""
    },
    "armor_class": 10,
    "initiative": 0,
    "speed": 30
}


def new_character():
    character = deepcopy(DEFAULT_CHARACTER)
    character["character_id"] = uuid4().hex
    return character


def merge_unique(*lists):
    merged = []
    for items in lists:
        for item in items or []:
            if item and item not in merged:
                merged.append(item)
    return merged
