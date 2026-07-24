"""Generate a broad rules coverage audit from normalized 5e.tools data."""

from __future__ import annotations

import json
import importlib
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

IMPORTED_DIR = ROOT_DIR / "data" / "imported" / "5etools"
COVERAGE_DIR = ROOT_DIR / "data" / "coverage"
AUDIT_PATH = COVERAGE_DIR / "imported_feature_audit.json"

CLASS_CHOICE_HANDLERS = {
    "Ability Score Improvement": "rules.level_up.apply_asi_or_feat_choice",
    "Additional Fighting Style": "rules.class_choice_rules.required_class_choice_definitions",
    "Aspect of the Wilds": "rules.feature_configurations.refresh_feature_configurations",
    "Blessed Strikes": "rules.class_choice_rules.required_class_choice_definitions",
    "Deft Explorer": "rules.class_choice_rules.required_class_choice_definitions",
    "Defensive Tactics": "rules.feature_configurations.refresh_feature_configurations",
    "Divine Order": "rules.class_choice_rules.required_class_choice_definitions",
    "Elemental Affinity": "rules.class_choice_rules.required_class_choice_definitions",
    "Elemental Fury": "rules.class_choice_rules.required_class_choice_definitions",
    "Eldritch Invocation Options": "rules.invocations.eligible_invocation_names",
    "Eldritch Invocations": "rules.invocations.eligible_invocation_names",
    "Expertise": "rules.class_choice_rules.expertise_options",
    "Fighting Style": "rules.class_choice_rules.fighting_style_options",
    "Hunter's Prey": "rules.feature_configurations.refresh_feature_configurations",
    "Magical Discoveries": "rules.class_choice_rules.magical_discoveries_options",
    "Magical Secrets": "rules.class_choice_rules.bard_eligible_spell_lists",
    "Maneuver Options": "rules.level_up.subclass_level_up_choices",
    "Metamagic": "rules.class_choice_rules.metamagic_total_for_level",
    "Metamagic Options": "rules.class_choice_rules.metamagic_total_for_level",
    "Mystic Arcanum": "rules.mystic_arcanum.mystic_arcanum_options",
    "Otherworldly Glamour": "rules.class_choice_rules.required_class_choice_definitions",
    "Primal Knowledge": "rules.class_choice_rules.barbarian_primal_knowledge_options",
    "Primal Order": "rules.class_choice_rules.required_class_choice_definitions",
    "Rage of the Wilds": "rules.level_up.subclass_level_up_choices",
    "Scholar": "rules.class_choice_rules.scholar_options",
    "Student of War": "rules.level_up.subclass_level_up_choices",
    "Thieves' Cant": "rules.class_choice_rules.language_options",
    "Weapon Mastery": "rules.weapon_mastery.eligible_weapon_mastery_names",
    "Wild Shape": "rules.class_choice_rules.wild_shape_form_options",
}

REST_CHANGEABLE_FEATURES = {
    "Aspect of the Wilds",
    "Defensive Tactics",
    "Fiendish Resilience",
    "Hunter's Prey",
    "The Third Eye",
}

CLASS_FEATURE_CLASSIFICATIONS = {
    "Abjure Foes": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Acrobatic Movement": ("movement_modifier", "services.character_engine.calculate_speed_details"),
    "Arcane Charge": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Arcane Apotheosis": ("resource_progression", "services.character_engine.calculate_class_resources"),
    "Archdruid": ("resource_progression", "services.character_engine.calculate_class_resources"),
    "Avatar of Battle": ("automatic_sheet_value", "services.character_engine.calculate_damage_resistances"),
    "Aura of Courage": ("resource_progression", "services.character_engine.calculate_class_resources"),
    "Aura Expansion": ("resource_progression", "services.character_engine.calculate_class_resources"),
    "Aura of Protection": ("resource_progression", "services.character_engine.calculate_class_resources"),
    "Avenging Angel": ("resource_progression", "services.character_engine.subclass_resources"),
    "Battering Roots": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Beguiling Defenses": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Bewitching Magic": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Bestial Fury": ("feature_upgrade", "services.character_engine.feature_descriptions_for_character"),
    "Body and Mind": ("automatic_sheet_value", "services.character_engine.class_feature_ability_adjustments"),
    "Brutal Strike": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Bulwark of Force": ("resource_progression", "services.character_engine.subclass_resources"),
    "Battle Magic": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Celestial Resilience": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Combat Superiority": ("resource_progression", "services.character_engine.battle_master_resources"),
    "Corona of Light": ("resource_progression", "services.character_engine.subclass_resources"),
    "Contact Patron": ("spell_grant", "rules.feature_spell_grants.feature_spell_grant_records"),
    "Controlled Chaos": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Create Thrall": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Cunning Strike": ("feature_reference", "services.character_engine.related_features_for_character"),
    "Devious Strikes": ("feature_reference", "services.character_engine.related_features_for_character"),
    "Deflect Energy": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Disciplined Survivor": ("proficiency_grant", "services.character_engine.class_feature_saving_throw_proficiencies"),
    "Divine Intervention": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Dragon Companion": ("spell_grant", "rules.feature_spell_grants.feature_spell_grant_records"),
    "Dragon Wings": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Elder Champion": ("resource_progression", "services.character_engine.subclass_resources"),
    "Eldritch Hex": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Eldritch Master": ("resource_progression", "services.character_engine.calculate_class_resources"),
    "Eldritch Strike": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Empowered Evocation": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Envenom Weapons": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Epic Boon": ("required_permanent_choice", "rules.level_up.epic_boon_choice"),
    "Feral Senses": ("automatic_sheet_value", "services.character_engine.calculate_senses"),
    "Fey Reinforcements": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Fiendish Resilience": ("rest_changeable_configuration", "rules.feature_configurations.refresh_feature_configurations"),
    "Fleet Step": ("movement_modifier", "services.character_engine.calculate_speed_details"),
    "Foe Slayer": ("resource_progression", "services.character_engine.calculate_class_resources"),
    "Flurry of Healing and Harm": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Full of Stars": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Guarded Mind": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Greater Portent": ("resource_progression", "services.character_engine.subclass_resources"),
    "Glorious Defense": ("resource_progression", "services.character_engine.subclass_resources"),
    "Greater Divine Intervention": ("resource_progression", "services.character_engine.calculate_class_resources"),
    "Hurl Through Hell": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Heightened Focus": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Heroic Warrior": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Homing Strikes": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Holy Nimbus": ("resource_progression", "services.character_engine.subclass_resources"),
    "Illusory Self": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Illusory Reality": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Improved Blessed Strikes": ("feature_upgrade", "services.character_engine.feature_descriptions_for_character"),
    "Improved Combat Superiority": ("resource_progression", "services.character_engine.battle_master_resources"),
    "Improved Brutal Strike": ("feature_upgrade", "services.character_engine.feature_descriptions_for_character"),
    "Improved Cunning Strike": ("feature_upgrade", "services.character_engine.feature_descriptions_for_character"),
    "Improved Elemental Fury": ("feature_upgrade", "services.character_engine.feature_descriptions_for_character"),
    "Improved Shadow Step": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Indomitable": ("resource_progression", "services.character_engine.calculate_class_resources"),
    "Infiltration Expertise": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Intimidating Presence": ("resource_progression", "services.character_engine.subclass_resources"),
    "Leading Evasion": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Living Legend": ("resource_progression", "services.character_engine.subclass_resources"),
    "Lunar Form": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Magical Secrets": ("feature_upgrade", "rules.class_choice_rules.bard_eligible_spell_lists"),
    "Magical Ambush": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Misty Wanderer": ("spell_grant", "rules.feature_spell_grants.feature_spell_grant_records"),
    "Moonlight Step": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Nature Speaker": ("spell_grant", "rules.feature_spell_grants.feature_spell_grant_records"),
    "Nature's Sanctuary": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Nature's Veil": ("resource_progression", "services.character_engine.calculate_class_resources"),
    "Nature's Ward": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Oceanic Gift": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Overchannel": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Peerless Skill": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Perfect Focus": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Persistent Rage": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Power of the Wilds": ("feature_upgrade", "services.character_engine.feature_descriptions_for_character"),
    "Primal Champion": ("automatic_sheet_value", "services.character_engine.class_feature_ability_adjustments"),
    "Psychic Teleportation": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Psychic Veil": ("resource_progression", "services.character_engine.subclass_resources"),
    "Radiant Strikes": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Rage of the Gods": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Relentless Rage": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Relentless": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Relentless Hunter": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Restoring Touch": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Revelation in Flesh": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Retaliation": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Searing Vengeance": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Self-Restoration": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Shadowy Dodge": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Share Spells": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Signature Spells": ("required_permanent_choice", "rules.level_up.signature_spells_choice"),
    "Slippery Mind": ("proficiency_grant", "services.character_engine.class_feature_saving_throw_proficiencies"),
    "Smite of Protection": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Soul Blades": ("feature_upgrade", "services.character_engine.feature_descriptions_for_character"),
    "Soul of Vengeance": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Spell Breaker": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Spell Mastery": ("required_permanent_choice", "rules.level_up.spell_mastery_choice"),
    "Spell Resistance": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Stalker's Flurry": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Stroke of Luck": ("resource_progression", "services.character_engine.calculate_class_resources"),
    "Studied Attacks": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Stormborn": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Stride of the Elements": ("movement_modifier", "services.character_engine.calculate_speed_details"),
    "Superior Critical": ("feature_upgrade", "services.character_engine.feature_descriptions_for_character"),
    "Superior Hunter's Defense": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Superior Hunter's Prey": ("feature_upgrade", "services.character_engine.feature_descriptions_for_character"),
    "Supreme Sneak": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Tactical Master": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Telekinetic Master": ("spell_grant", "rules.feature_spell_grants.feature_spell_grant_records"),
    "The Third Eye": ("rest_changeable_configuration", "rules.feature_configurations.refresh_feature_configurations"),
    "Thought Shield": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Tireless": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Trance of Order": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Travel Along the Tree": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Three Extra Attacks": ("resource_progression", "services.character_engine.calculate_class_resources"),
    "Twinkling Constellations": ("feature_upgrade", "services.character_engine.feature_descriptions_for_character"),
    "Two Extra Attacks": ("feature_upgrade", "services.character_engine.feature_descriptions_for_character"),
    "Unbreakable Majesty": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Undying Sentinel": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Ultimate Combat Superiority": ("resource_progression", "services.character_engine.battle_master_resources"),
    "Use Magic Device": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Versatile Trickster": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
    "Words of Creation": ("spell_grant", "rules.feature_spell_grants.feature_spell_grant_records"),
    "Zealous Presence": ("active_play_description_only", "services.character_engine.feature_descriptions_for_character"),
}

FEATURE_OUTPUT_FIELDS = {
    "Arcane Recovery": ["arcane_recovery_levels", "arcane_recovery_max_slot_level"],
    "Arcane Apotheosis": ["arcane_apotheosis_free_metamagic_per_turn"],
    "Archdruid": [
        "archdruid_wild_shape_slot_conversion",
        "archdruid_initiative_wild_shape_recovery",
    ],
    "Action Surge": ["action_surge_uses", "action_surge_recharge"],
    "Aura Expansion": ["aura_of_protection_range"],
    "Aura of Courage": ["aura_of_courage_range"],
    "Aura of Protection": ["aura_of_protection_range"],
    "Avenging Angel": ["avenging_angel_free_uses", "avenging_angel_alternate_recovery_resource"],
    "Avatar of Battle": ["damage_resistances"],
    "Body and Mind": ["ability_scores.Dexterity", "ability_scores.Wisdom"],
    "Bulwark of Force": [
        "bulwark_of_force_free_uses",
        "bulwark_of_force_targets",
        "bulwark_of_force_alternate_recovery_resource",
    ],
    "Elder Champion": ["elder_champion_free_uses", "elder_champion_alternate_recovery_resource"],
    "Eldritch Master": ["eldritch_master_pact_slot_recovery", "eldritch_master_recovery_trigger"],
    "Corona of Light": ["corona_of_light_uses", "corona_of_light_recharge"],
    "Combat Superiority": ["maneuvers_known", "superiority_dice", "superiority_die"],
    "Dragon Companion": ["Summon Dragon"],
    "Feral Senses": ["blindsight_range"],
    "Glorious Defense": ["glorious_defense_uses", "glorious_defense_recharge"],
    "Greater Divine Intervention": ["greater_divine_intervention_wish_recharge"],
    "Greater Portent": ["portent_dice"],
    "Foe Slayer": ["hunters_mark_damage_die"],
    "Holy Nimbus": ["holy_nimbus_free_uses", "holy_nimbus_alternate_recovery_resource"],
    "Indomitable": ["indomitable_uses", "indomitable_recharge"],
    "Intimidating Presence": [
        "intimidating_presence_free_uses",
        "intimidating_presence_alternate_recovery_resource",
    ],
    "Living Legend": ["living_legend_free_uses", "living_legend_alternate_recovery_resource"],
    "Nature's Veil": ["natures_veil_uses", "natures_veil_recharge"],
    "Primal Champion": ["ability_scores.Strength", "ability_scores.Constitution"],
    "Psychic Veil": ["psychic_veil_free_uses", "psychic_veil_alternate_recovery_resource"],
    "Signature Spells": ["signature_spells"],
    "Spellcasting": ["spellbook_spells", "prepared_spells"],
    "Stroke of Luck": ["stroke_of_luck_uses", "stroke_of_luck_recharge"],
    "Three Extra Attacks": ["attacks_per_attack_action"],
    "Telekinetic Master": ["Telekinesis"],
    "Ultimate Combat Superiority": ["maneuvers_known", "superiority_dice", "superiority_die"],
    "Words of Creation": ["Power Word Heal", "Power Word Kill"],
}

EXPECTED_VALUE_CHECKPOINTS = [
    {
        "id": "sorcerer_metamagic_level_2",
        "feature_id": "sorcerer_metamagic",
        "owner": "Sorcerer",
        "level": 2,
        "handler": "rules.class_choice_rules.metamagic_total_for_level",
        "expected_values": {"metamagic_options_known": 2},
    },
    {
        "id": "sorcerer_metamagic_level_10",
        "feature_id": "sorcerer_metamagic",
        "owner": "Sorcerer",
        "level": 10,
        "handler": "rules.class_choice_rules.metamagic_total_for_level",
        "expected_values": {"metamagic_options_known": 4},
    },
    {
        "id": "sorcerer_metamagic_level_17",
        "feature_id": "sorcerer_metamagic",
        "owner": "Sorcerer",
        "level": 17,
        "handler": "rules.class_choice_rules.metamagic_total_for_level",
        "expected_values": {"metamagic_options_known": 6},
    },
    {
        "id": "battle_master_level_15",
        "feature_id": "battle_master_combat_superiority",
        "owner": "Fighter: Battle Master",
        "level": 15,
        "handler": "services.character_engine.battle_master_resources",
        "expected_values": {
            "maneuvers_known": 9,
            "superiority_dice": 6,
            "superiority_die": "d10",
        },
    },
    {
        "id": "battle_master_level_18",
        "feature_id": "battle_master_combat_superiority",
        "owner": "Fighter: Battle Master",
        "level": 18,
        "handler": "services.character_engine.battle_master_resources",
        "expected_values": {
            "maneuvers_known": 9,
            "superiority_dice": 6,
            "superiority_die": "d12",
        },
    },
    {
        "id": "fighter_action_surge_level_2",
        "feature_id": "fighter_action_surge",
        "owner": "Fighter",
        "level": 2,
        "handler": "services.character_engine.calculate_class_resources",
        "expected_values": {"action_surge_uses": 1},
    },
    {
        "id": "fighter_action_surge_level_17",
        "feature_id": "fighter_action_surge",
        "owner": "Fighter",
        "level": 17,
        "handler": "services.character_engine.calculate_class_resources",
        "expected_values": {"action_surge_uses": 2},
    },
    {
        "id": "ranger_feral_senses_level_18",
        "feature_id": "ranger_feral_senses",
        "owner": "Ranger",
        "level": 18,
        "handler": "services.character_engine.calculate_senses",
        "expected_values": {"blindsight_range": 30},
    },
    {
        "id": "paladin_aura_of_protection_level_6",
        "feature_id": "paladin_aura_of_protection",
        "owner": "Paladin",
        "level": 6,
        "handler": "services.character_engine.calculate_class_resources",
        "expected_values": {"aura_of_protection_range": 10},
    },
    {
        "id": "paladin_aura_of_protection_level_18",
        "feature_id": "paladin_aura_of_protection",
        "owner": "Paladin",
        "level": 18,
        "handler": "services.character_engine.calculate_class_resources",
        "expected_values": {"aura_of_protection_range": 30},
    },
]

FEATURE_EFFECTS = {
    "Bulwark of Force": ["free_use_counter", "target_count", "alternate_recovery_resource"],
    "Body and Mind": ["ability_score_increase", "ability_score_maximum"],
    "Cunning Strike": ["referenced_options"],
    "Devious Strikes": ["referenced_options"],
    "Glorious Defense": ["ability_modifier_uses"],
    "Corona of Light": ["ability_modifier_uses"],
    "Greater Portent": ["resource_maximum"],
    "Indomitable": ["resource_maximum"],
    "Intimidating Presence": ["free_use_counter", "alternate_recovery_resource"],
    "Nature's Veil": ["ability_modifier_uses"],
    "Primal Champion": ["ability_score_increase", "ability_score_maximum"],
    "Psychic Veil": ["free_use_counter", "alternate_recovery_resource"],
}

SPELL_FEATURE_NAMES = {
    "Arcane Trickster Spellcasting",
    "Archfey Spells",
    "Celestial Spells",
    "Circle of the Land Spells",
    "Circle of the Moon Spells",
    "Clockwork Spells",
    "Fey Wanderer Spells",
    "Life Domain Spells",
    "Light Domain Spells",
    "Oath of Devotion Spells",
    "Oath of Glory Spells",
    "Pact Magic",
    "Psionic Spells",
    "Spellcasting",
}

RESOURCE_FEATURE_NAMES = {
    "Action Surge",
    "Arcane Recovery",
    "Bardic Inspiration",
    "Channel Divinity",
    "Font of Magic",
    "Lay on Hands",
    "Rage",
    "Second Wind",
    "Sorcery Incarnate",
    "Wild Companion",
}

SHEET_VALUE_TRAITS = {
    "Adrenaline Rush",
    "Brave",
    "Celestial Resistance",
    "Darkvision",
    "Dwarven Resilience",
    "Dwarven Toughness",
    "Fey Ancestry",
    "Fiendish Legacy",
    "Giant Ancestry",
    "Gnomish Lineage",
    "Halfling Nimbleness",
    "Light Bearer",
    "Little Giant",
    "Resourceful",
    "Skillful",
}

DESCRIPTION_ONLY_HANDLER = "services.character_engine.feature_descriptions_for_character"
FEAT_OUTPUT_FIELDS = {
    "Boon of Energy Resistance": ["damage_resistances"],
    "Boon of Fortitude": ["hit_points.max"],
    "Boon of Skill": ["skill_proficiencies", "expertise"],
    "Boon of Speed": ["speed"],
    "Boon of Truesight": ["truesight_range"],
    "Great Weapon Master": ["great_weapon_master_damage_bonus"],
    "Shield Master": ["shield_master_bash_dc", "shield_master_bash_ability"],
    "Skulker": ["blindsight_range", "blindsight_source"],
}

FEAT_OUTPUT_HANDLERS = {
    "Boon of Energy Resistance": "services.character_engine.calculate_damage_resistances",
    "Boon of Fortitude": "services.character_engine.recalculate_hit_points",
    "Boon of Skill": "rules.feat_grants.feat_grants_for_character",
    "Boon of Speed": "services.character_engine.calculate_speed_details",
    "Boon of Truesight": "services.character_engine.calculate_senses",
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def slug(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "_" for char in str(value)).strip("_")


def base_record(source_type, source_id, owner, name, level="", description_available=False):
    return {
        "source_type": source_type,
        "source_id": source_id,
        "owner": owner,
        "name": name,
        "level": level,
        "classification": "",
        "handler": "",
        "handler_verified": False,
        "support_status": "unsupported",
        "reviewed": False,
        "description_available": bool(description_available),
        "effects": [],
        "expected_output_fields": [],
        "output_verified": False,
        "related_feature_names": [],
        "raw_rule_indicators": [],
        "notes": [],
    }


def handler_verified(handler):
    if not handler:
        return False
    module_name, _, attribute = handler.rpartition(".")
    if not module_name or not attribute:
        return False
    try:
        module = importlib.import_module(module_name)
    except Exception:
        return False
    return hasattr(module, attribute)


def support_status_for(classification):
    if classification == "unsupported":
        return "unsupported"
    if classification == "active_play_description_only":
        return "description_only"
    return "supported"


def mark_record(
    record,
    classification,
    handler="",
    reviewed=True,
    notes=None,
    effects=None,
    expected_output_fields=None,
):
    verified = handler_verified(handler)
    expected_fields = list(expected_output_fields if expected_output_fields is not None else record.get("expected_output_fields", []))
    effect_names = list(effects if effects is not None else record.get("effects", []))
    record.update({
        "classification": classification,
        "handler": handler,
        "handler_verified": verified,
        "support_status": support_status_for(classification),
        "reviewed": reviewed,
        "effects": effect_names,
        "expected_output_fields": expected_fields,
        "output_verified": verified and bool(expected_fields or record.get("related_feature_names")),
    })
    if notes is not None:
        record["notes"] = list(notes)
    return record


def classify_feature(record):
    name = record["name"]
    if name in CLASS_FEATURE_CLASSIFICATIONS:
        classification, handler = CLASS_FEATURE_CLASSIFICATIONS[name]
        notes = []
        if classification == "unsupported":
            notes = ["Feature has a standing sheet effect that is not automated yet."]
        mark_record(
            record,
            classification,
            handler,
            reviewed=True,
            notes=notes,
            effects=FEATURE_EFFECTS.get(name, []),
            expected_output_fields=FEATURE_OUTPUT_FIELDS.get(name, []),
        )
    elif name in CLASS_CHOICE_HANDLERS:
        classification = "rest_changeable_configuration" if name in REST_CHANGEABLE_FEATURES else "required_permanent_choice"
        mark_record(record, classification, CLASS_CHOICE_HANDLERS[name])
    elif name.endswith(" Subclass"):
        mark_record(record, "required_permanent_choice", "rules.level_up.resolve_pending_choice")
    elif name == "Subclass Feature":
        mark_record(record, "feature_upgrade", "rules.level_up.classify_level_features")
    elif name in SPELL_FEATURE_NAMES or name.endswith(" Spells") or name in {"Pact Magic"}:
        mark_record(
            record,
            "resource_progression",
            "rules.leveling.effective_spellcasting",
            expected_output_fields=FEATURE_OUTPUT_FIELDS.get(name, []),
        )
    elif name in RESOURCE_FEATURE_NAMES:
        mark_record(
            record,
            "resource_progression",
            "rules.leveling.get_class_resources",
            expected_output_fields=FEATURE_OUTPUT_FIELDS.get(name, []),
        )
    elif record["description_available"]:
        mark_record(
            record,
            "active_play_description_only",
            DESCRIPTION_ONLY_HANDLER,
            notes=["Feature text is retained on the final sheet; no durable build-time sheet value is modeled for this feature."],
        )
    else:
        mark_record(
            record,
            "unsupported",
            "",
            reviewed=False,
            notes=["No explicit sheet-value, choice, or description-only classification recorded yet."],
        )
    return record


def classify_species_trait(record):
    name = record["name"]
    if name in SHEET_VALUE_TRAITS:
        mark_record(record, "automatic_sheet_value", "services.character_engine.recalculate_character")
    elif record["description_available"]:
        mark_record(record, "active_play_description_only", "services.character_engine.feature_descriptions_for_character")
    else:
        mark_record(record, "unsupported", "", reviewed=False, notes=["Species trait lacks a recorded handler and description."])
    return record


def classify_background(record):
    mark_record(record, "automatic_sheet_value", "services.character_engine.calculate_background_ability_bonuses")
    return record


def classify_feat(record, feat):
    from rules.feat_rules import ACTIVE_PLAY_FEATS, PERMANENT_GRANT_FEATS, SHEET_VALUE_FEATS, feat_support_status

    name = feat.get("name", "")
    status = feat_support_status(feat)
    record["support"] = status
    if name == "Ability Score Improvement":
        mark_record(record, "required_permanent_choice", "rules.level_up.apply_asi_or_feat_choice")
    elif name in FEAT_OUTPUT_FIELDS:
        mark_record(
            record,
            "automatic_sheet_value",
            FEAT_OUTPUT_HANDLERS.get(name, "rules.feat_grants.feat_sheet_resources"),
            expected_output_fields=FEAT_OUTPUT_FIELDS[name],
        )
    elif name in SHEET_VALUE_FEATS or name in PERMANENT_GRANT_FEATS:
        classification = "active_play_description_only" if status.get("sheet_calculation") == "description_only" else "automatic_sheet_value"
        mark_record(
            record,
            classification,
            "rules.feat_rules.feat_choice_schema",
            notes=status.get("notes", []),
        )
    elif name in ACTIVE_PLAY_FEATS:
        mark_record(record, "active_play_description_only", "rules.feat_rules.ACTIVE_PLAY_FEATS")
    else:
        mark_record(record, "unsupported", "", reviewed=False, notes=status.get("notes", ["Feat has not been audited yet."]))
    return record


def class_feature_records(classes):
    records = []
    for class_data in classes:
        descriptions = class_data.get("feature_descriptions", {})
        related_features = class_data.get("feature_related_features", {})
        for level, names in class_data.get("level_features", {}).items():
            for name in names:
                record = base_record(
                    "class_feature",
                    f"{slug(class_data['name'])}_{level}_{slug(name)}",
                    class_data["name"],
                    name,
                    int(level),
                    name in descriptions,
                )
                record["related_feature_names"] = [
                    related.get("name", "")
                    for related in related_features.get(name, [])
                    if related.get("name")
                ]
                if record["related_feature_names"]:
                    record["raw_rule_indicators"].append("refClassFeature")
                records.append(classify_feature(record))
        if class_data.get("spellcasting"):
            records.append({
                **base_record(
                    "class_spellcasting",
                    f"{slug(class_data['name'])}_spellcasting",
                    class_data["name"],
                    "Spellcasting",
                    "",
                    True,
                ),
                "classification": "spell_progression",
                "handler": "rules.leveling.effective_spellcasting",
                "handler_verified": handler_verified("rules.leveling.effective_spellcasting"),
                "support_status": "supported",
                "reviewed": True,
                "expected_output_fields": FEATURE_OUTPUT_FIELDS["Spellcasting"],
                "output_verified": handler_verified("rules.leveling.effective_spellcasting"),
            })
        for subclass in class_data.get("subclasses", []):
            records.extend(subclass_feature_records(class_data, subclass))
    return records


def subclass_feature_records(class_data, subclass):
    records = []
    descriptions = subclass.get("feature_descriptions", {})
    related_features = subclass.get("feature_related_features", {})
    owner = f"{class_data['name']}: {subclass['name']}"
    for level, names in subclass.get("level_features", {}).items():
        for name in names:
            record = base_record(
                "subclass_feature",
                f"{slug(class_data['name'])}_{slug(subclass['short_name'])}_{level}_{slug(name)}",
                owner,
                name,
                int(level),
                name in descriptions,
            )
            record["related_feature_names"] = [
                related.get("name", "")
                for related in related_features.get(name, [])
                if related.get("name")
            ]
            if record["related_feature_names"]:
                record["raw_rule_indicators"].append("refSubclassFeature")
            records.append(classify_feature(record))
    for level, grants in subclass.get("grants_by_level", {}).items():
        if not grants:
            continue
        records.append({
            **base_record(
                "subclass_spell_grant",
                f"{slug(class_data['name'])}_{slug(subclass['short_name'])}_{level}_spell_grants",
                owner,
                "Subclass spell grants",
                int(level),
                True,
            ),
            "classification": "spell_grant",
            "handler": "rules.leveling.get_active_subclass_grants",
            "handler_verified": handler_verified("rules.leveling.get_active_subclass_grants"),
            "support_status": "supported",
            "reviewed": True,
            "grant_count": len(grants),
        })
    if subclass.get("spellcasting_progression") or subclass.get("spellcasting"):
        records.append({
            **base_record(
                "subclass_spellcasting",
                f"{slug(class_data['name'])}_{slug(subclass['short_name'])}_spellcasting",
                owner,
                "Subclass spellcasting",
                "",
                True,
            ),
            "classification": "spell_progression",
            "handler": "rules.leveling.effective_spellcasting",
            "handler_verified": handler_verified("rules.leveling.effective_spellcasting"),
            "support_status": "supported",
            "reviewed": True,
        })
    return records


def species_records(species):
    records = []
    for species_data in species:
        descriptions = species_data.get("trait_descriptions", {})
        for trait in species_data.get("traits", []):
            record = base_record(
                "species_trait",
                f"{slug(species_data['name'])}_{slug(trait)}",
                species_data["name"],
                trait,
                "",
                trait in descriptions,
            )
            records.append(classify_species_trait(record))
    return records


def background_records(backgrounds):
    records = []
    for background in backgrounds:
        feature = background.get("feature")
        if not feature:
            continue
        record = base_record(
            "background_feature",
            f"{slug(background['name'])}_{slug(feature)}",
            background["name"],
            feature,
            "",
            bool(background.get("feature_descriptions")),
        )
        records.append(classify_background(record))
    return records


def feat_records(feats):
    records = []
    for feat in feats:
        record = base_record(
            "feat",
            feat.get("id") or slug(feat.get("name", "feat")),
            feat.get("source", ""),
            feat.get("name", ""),
            "",
            bool(feat.get("description")),
        )
        records.append(classify_feat(record, feat))
    return records


def generate_coverage_audit():
    classes = read_json(IMPORTED_DIR / "classes.json")
    species = read_json(IMPORTED_DIR / "species.json")
    backgrounds = read_json(IMPORTED_DIR / "backgrounds.json")
    feats = read_json(IMPORTED_DIR / "feats.json")

    records = [
        *class_feature_records(classes),
        *species_records(species),
        *background_records(backgrounds),
        *feat_records(feats),
    ]
    records.sort(key=lambda item: (
        item["source_type"],
        str(item["owner"]),
        int(item["level"] or 0),
        item["name"],
    ))

    summary = {}
    for record in records:
        summary[record["classification"]] = summary.get(record["classification"], 0) + 1

    import_warnings = []
    for class_data in classes:
        import_warnings.extend(class_data.get("import_warnings", []))
        for subclass in class_data.get("subclasses", []):
            import_warnings.extend(subclass.get("import_warnings", []))

    audit = {
        "generated_from": "data/imported/5etools",
        "record_count": len(records),
        "summary": dict(sorted(summary.items())),
        "import_warnings": sorted(set(import_warnings)),
        "expected_value_checkpoints": [
            {
                **checkpoint,
                "handler_verified": handler_verified(checkpoint["handler"]),
            }
            for checkpoint in EXPECTED_VALUE_CHECKPOINTS
        ],
        "records": records,
    }
    COVERAGE_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    return audit


def main():
    audit = generate_coverage_audit()
    print(f"Wrote {AUDIT_PATH.relative_to(ROOT_DIR)} with {audit['record_count']} records.")


if __name__ == "__main__":
    main()
