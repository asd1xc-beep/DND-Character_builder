from math import ceil

from models.character import ABILITIES, merge_unique
from rules.class_choice_rules import (
    battle_master_progression,
    class_choice_expertise,
    class_choice_languages,
    class_choice_saving_throw_proficiencies,
    class_choice_skill_proficiencies,
)
from rules.feat_grants import (
    feat_grants_for_character,
    feat_sheet_resources,
    feat_speed_bonus,
    feat_spell_grant_records,
    has_general_feat,
    medium_armor_dexterity_cap,
)
from rules.feature_spell_grants import feature_spell_grant_records
from rules.feature_configurations import configured_feature_values, refresh_feature_configurations
from rules.feat_rules import general_feat_names
from rules.ability_scores import (
    ability_score_maximums_for_class,
    calculate_ability_modifiers,
    DEFAULT_ABILITY_SCORE_MAXIMUM,
)
from rules.hit_points import (
    calculate_max_hit_points,
    ensure_hp_history,
    hit_die_label,
)
from rules.level_up import ensure_level_tracking
from rules.leveling import (
    class_features_up_to_level,
    effective_spellcasting,
    get_active_subclass_grants,
    get_class_resources,
    normalize_level,
    selected_subclass_data,
    subclass_features_up_to_level,
)
from rules.wizard_spellbook import wizard_spellbook_spells
from rules.wizard_savant import savant_spell_source_records, selected_savant_spells
from rules.mystic_arcanum import mystic_arcanum_grant_records, sync_mystic_arcanum_class_options
from rules.proficiencies import (
    calculate_saving_throw_bonuses,
    calculate_skill_bonuses,
    proficiency_bonus_for_level,
)
from services.character_sheet import spell_grants


def calculate_armor_class(character):
    details = calculate_armor_class_details(character)
    character["armor_class_details"] = details
    return details["value"]


def calculate_armor_class_details(character):
    dexterity = character["ability_modifiers"].get("Dexterity", 0)
    constitution = character["ability_modifiers"].get("Constitution", 0)
    wisdom = character["ability_modifiers"].get("Wisdom", 0)
    charisma = character["ability_modifiers"].get("Charisma", 0)
    dexterity_score = character.get("ability_scores", {}).get("Dexterity", 10)
    equipment = set(character.get("equipment", []))
    class_name = character.get("class", "")
    subclass_name = character.get("subclass", "")
    has_shield = "Shield" in equipment
    has_armor = any(armor in equipment for armor in ARMOR_FORMULAS)
    medium_cap = medium_armor_dexterity_cap(character, dexterity_score)

    formulas = [
        armor_formula("unarmored", "Unarmored", 10 + dexterity, "base", allows_shield=True),
    ]
    for armor_name, formula in ARMOR_FORMULAS.items():
        if armor_name not in equipment:
            continue
        dexterity_bonus = dexterity
        if formula["category"] == "medium":
            dexterity_bonus = min(dexterity, medium_cap)
        if formula["category"] == "heavy":
            dexterity_bonus = 0
        formulas.append(armor_formula(
            slug(armor_name),
            armor_name,
            formula["base"] + dexterity_bonus,
            "armor",
            allows_shield=True,
        ))

    if class_name == "Barbarian" and not has_armor:
        formulas.append(armor_formula(
            "barbarian_unarmored_defense",
            "Barbarian Unarmored Defense",
            10 + dexterity + constitution,
            "class_feature",
            allows_shield=True,
        ))
    if class_name == "Monk" and not has_armor:
        formulas.append(armor_formula(
            "monk_unarmored_defense",
            "Monk Unarmored Defense",
            10 + dexterity + wisdom,
            "class_feature",
            allows_shield=False,
        ))
    if class_name == "Bard" and subclass_name == "College of Dance" and not has_armor:
        formulas.append(armor_formula(
            "dance_bard_unarmored_defense",
            "College of Dance Unarmored Defense",
            10 + dexterity + charisma,
            "subclass_feature",
            allows_shield=False,
        ))
    if class_name == "Sorcerer" and subclass_name == "Draconic Sorcery" and not has_armor:
        formulas.append(armor_formula(
            "draconic_resilience",
            "Draconic Resilience",
            10 + dexterity + charisma,
            "subclass_feature",
            allows_shield=False,
        ))

    candidates = []
    for formula in formulas:
        value = formula["base_value"]
        shield_applied = False
        if has_shield and formula["allows_shield"]:
            value += 2
            shield_applied = True
        candidates.append({**formula, "value": value, "shield_applied": shield_applied})

    best = max(candidates, key=lambda item: item["value"])
    return {
        "value": best["value"],
        "formula_id": best["id"],
        "source": best["source"],
        "source_name": best["name"],
        "shield_applied": best["shield_applied"],
        "medium_armor_dexterity_cap": medium_cap,
        "candidates": candidates,
    }


ARMOR_FORMULAS = {
    "Leather Armor": {"base": 11, "category": "light"},
    "Studded Leather Armor": {"base": 12, "category": "light"},
    "Chain Shirt": {"base": 13, "category": "medium"},
    "Scale Mail": {"base": 14, "category": "medium"},
    "Chain Mail": {"base": 16, "category": "heavy"},
}


def armor_formula(formula_id, name, base_value, source, allows_shield):
    return {
        "id": formula_id,
        "name": name,
        "base_value": base_value,
        "source": source,
        "allows_shield": allows_shield,
    }


def calculate_background_ability_bonuses(character, background_data):
    bonuses = {ability: 0 for ability in ABILITIES}
    options = background_data.get("ability_options", {})
    if options.get("mode") != "choose_weighted":
        return bonuses

    primary = character.get("background_options", {}).get("primary_ability")
    secondary = character.get("background_options", {}).get("secondary_ability")
    if primary in bonuses:
        bonuses[primary] += int(options.get("primary_bonus", 2))
    if secondary in bonuses and secondary != primary:
        bonuses[secondary] += int(options.get("secondary_bonus", 1))
    return bonuses


def apply_source_ability_adjustments(base_scores, background_bonuses, adjustments):
    scores = {
        ability: int(base_scores.get(ability, 10)) + int(background_bonuses.get(ability, 0))
        for ability in ABILITIES
    }
    source_bonuses = {ability: 0 for ability in ABILITIES}
    for adjustment in adjustments or []:
        maximum = int(adjustment.get("maximum", 20) or 20)
        for ability, amount in adjustment.get("adjustments", {}).items():
            if ability not in scores:
                continue
            before = scores[ability]
            scores[ability] = min(maximum, before + int(amount or 0))
            source_bonuses[ability] += scores[ability] - before
    return scores, source_bonuses


def ability_score_maximums(character, class_data):
    class_name = class_data.get("name", character.get("class", ""))
    level = character.get("level", 1)
    maximums = {ability: DEFAULT_ABILITY_SCORE_MAXIMUM for ability in ABILITIES}
    maximums.update(ability_score_maximums_for_class(class_name, level))
    return maximums


def class_feature_ability_adjustments(character, class_data):
    class_name = class_data.get("name", character.get("class", ""))
    level = int(character.get("level", 1) or 1)
    if class_name == "Barbarian" and level >= 20:
        return [{
            "source_type": "class_feature",
            "source_name": "Primal Champion",
            "adjustments": {"Strength": 4, "Constitution": 4},
            "maximum": 25,
        }]
    if class_name == "Monk" and level >= 20:
        return [{
            "source_type": "class_feature",
            "source_name": "Body and Mind",
            "adjustments": {"Dexterity": 4, "Wisdom": 4},
            "maximum": 25,
        }]
    return []


def selected_class_option_features(class_options, feature_configurations=None):
    feature_names = []
    configured_keys = {
        config.get("feature_id")
        for config in feature_configurations or []
        if config.get("current_value")
    }
    for key, value in class_options.items():
        if key in configured_keys:
            continue
        if key == "savant_spells" or key.startswith("savant_spells_level_"):
            continue
        if key in {
            "battle_master_save_ability",
            "class_skills",
            "equipment_package",
            "extra_cantrips",
            "signature_spells",
            "bard_expertise",
            "blessed_warrior_cantrips",
            "druidic_warrior_cantrips",
            "fey_wanderer_skill",
            "metamagic",
            "primal_knowledge_skill",
            "ranger_deft_explorer_expertise",
            "ranger_languages",
            "rogue_thieves_cant_language",
            "lore_skills",
            "maneuvers",
            "magical_discoveries",
            "magical_secrets",
            "student_of_war_skill",
            "student_of_war_tool",
            "wild_shape_forms",
            "wizard_scholar_skill",
        }:
            continue
        if isinstance(value, str):
            feature_names.append(value)
        elif isinstance(value, list):
            feature_names.extend(item for item in value if isinstance(item, str))
    return feature_names


def active_origin_feats(character):
    return merge_unique(
        character.get("origin_feats", []),
        character.get("background_options", {}).get("origin_feats", []),
        character.get("species_options", {}).get("origin_feats", []),
    )


def calculate_class_resources(character, class_data):
    resources = get_class_resources(class_data, character.get("level", 1))
    resources["proficiency_bonus"] = character.get("proficiency_bonus", 2)
    class_name = class_data.get("name", character.get("class", ""))
    level = int(character.get("level", 1) or 1)
    if class_data.get("name") == "Wizard":
        resources["arcane_recovery_levels"] = ceil(int(character.get("level", 1) or 1) / 2)
        resources["arcane_recovery_max_slot_level"] = 5
    if class_name == "Fighter" and level >= 9:
        resources["indomitable_uses"] = 3 if level >= 17 else 2 if level >= 13 else 1
        resources["indomitable_recharge"] = "long_rest"
    if class_name == "Fighter" and action_surge_uses(level):
        resources["action_surge_uses"] = action_surge_uses(level)
        resources["action_surge_recharge"] = "short_or_long_rest"
    if class_name == "Fighter" and level >= 20:
        resources["attacks_per_attack_action"] = 4
    elif class_name == "Fighter" and level >= 11:
        resources["attacks_per_attack_action"] = 3
    elif class_name == "Fighter" and level >= 5:
        resources["attacks_per_attack_action"] = 2
    if class_name == "Paladin" and aura_of_protection_range(level):
        aura_range = aura_of_protection_range(level)
        resources["aura_of_protection_range"] = aura_range
        resources["paladin_aura_range"] = aura_range
        if level >= 10:
            resources["aura_of_courage_range"] = aura_range
        for aura_name in paladin_subclass_aura_names(character, class_data, level):
            resources[f"{slug(aura_name)}_range"] = aura_range
    if class_name == "Cleric" and level >= 20:
        resources["greater_divine_intervention_wish_available"] = True
        resources["greater_divine_intervention_wish_recharge"] = "2d4 long rests"
    if class_name == "Druid" and level >= 20:
        resources["archdruid_wild_shape_slot_conversion"] = True
        resources["archdruid_wild_shape_slot_conversion_recharge"] = "long_rest"
        resources["archdruid_initiative_wild_shape_recovery"] = 1
    if class_name == "Ranger" and level >= 14:
        resources["natures_veil_uses"] = max(1, character["ability_modifiers"].get("Wisdom", 0))
        resources["natures_veil_recharge"] = "long_rest"
    if class_name == "Ranger" and level >= 20:
        resources["hunters_mark_damage_die"] = "1d10"
    if class_name == "Rogue" and level >= 20:
        resources["stroke_of_luck_uses"] = 1
        resources["stroke_of_luck_recharge"] = "short_or_long_rest"
    if class_name == "Sorcerer" and level >= 20:
        resources["arcane_apotheosis_free_metamagic_per_turn"] = 1
        resources["arcane_apotheosis_requires_innate_sorcery"] = True
    if class_name == "Warlock" and level >= 20:
        resources["eldritch_master_pact_slot_recovery"] = "all"
        resources["eldritch_master_recovery_trigger"] = "magical_cunning"
    resources.update(feat_sheet_resources(character))
    if "Lucky" in active_origin_feats(character):
        resources["luck_points"] = character.get("proficiency_bonus", 2)
    if "Bardic Inspiration" in class_data.get("level_1_features", []):
        resources["bardic_inspiration_uses"] = max(1, character["ability_modifiers"].get("Charisma", 0))
    subclass_data = selected_subclass_data(class_data, character.get("subclass", ""))
    if subclass_data.get("short_name") == "Battle Master" and character.get("level", 1) >= 3:
        resources.update(battle_master_resources(character))
    resources.update(subclass_resources(character, class_data, subclass_data))
    spellcasting = effective_spellcasting(class_data, character.get("subclass", ""), character.get("level", 1))
    if spellcasting:
        resources.update(spellcasting_resources(character, spellcasting))
    return resources


def action_surge_uses(fighter_level):
    if int(fighter_level or 0) >= 17:
        return 2
    if int(fighter_level or 0) >= 2:
        return 1
    return 0


def aura_of_protection_range(paladin_level):
    if int(paladin_level or 0) >= 18:
        return 30
    if int(paladin_level or 0) >= 6:
        return 10
    return 0


def paladin_subclass_aura_names(character, class_data, level):
    if class_data.get("name", character.get("class", "")) != "Paladin" or int(level or 0) < 7:
        return []
    return [
        feature
        for feature in subclass_features_up_to_level(class_data, character.get("subclass", ""), level)
        if feature.startswith("Aura ") or feature.startswith("Aura of ")
    ]


def calculate_senses(character, class_data):
    records = []
    if has_general_feat(character, "Skulker"):
        records.append(sense_record(
            sense_type="Blindsight",
            range_feet=10,
            source={
                "type": "feat",
                "source_name": "Skulker",
            },
        ))
    if class_data.get("name", character.get("class", "")) == "Ranger" and int(character.get("level", 1) or 1) >= 18:
        records.append(sense_record(
            sense_type="Blindsight",
            range_feet=30,
            source={
                "type": "class_feature",
                "class_name": "Ranger",
                "feature_name": "Feral Senses",
                "level": 18,
            },
        ))
    if has_general_feat(character, "Boon of Truesight"):
        records.append(sense_record(
            sense_type="Truesight",
            range_feet=60,
            source={
                "type": "feat",
                "source_name": "Boon of Truesight",
            },
        ))
    return merge_sense_records(records)


def sense_record(sense_type, range_feet, source):
    return {
        "type": sense_type,
        "range": int(range_feet or 0),
        "source": source,
    }


def merge_sense_records(records):
    merged = {}
    for record in records or []:
        sense_type = record.get("type", "")
        if not sense_type:
            continue
        current = merged.setdefault(sense_type, {
            "type": sense_type,
            "range": 0,
            "sources": [],
            "source_names": [],
        })
        current["range"] = max(current["range"], int(record.get("range", 0) or 0))
        source = record.get("source", {})
        if source and source not in current["sources"]:
            current["sources"].append(source)
        source_name = source.get("source_name") or source.get("feature_name") or source.get("type", "")
        if source_name and source_name not in current["source_names"]:
            current["source_names"].append(source_name)
    return list(merged.values())


def sense_resource_summary(senses):
    resources = {}
    for sense in senses or []:
        if sense.get("type") == "Blindsight":
            resources["blindsight_range"] = sense.get("range", 0)
            resources["blindsight_sources"] = sense.get("source_names", [])
            resources["blindsight_source"] = ", ".join(sense.get("source_names", []))
        if sense.get("type") == "Truesight":
            resources["truesight_range"] = sense.get("range", 0)
            resources["truesight_sources"] = sense.get("source_names", [])
            resources["truesight_source"] = ", ".join(sense.get("source_names", []))
    return resources


def calculate_damage_resistances(character, class_data):
    records = []
    subclass_data = selected_subclass_data(class_data, character.get("subclass", ""))
    if (
        class_data.get("name", character.get("class", "")) == "Cleric"
        and subclass_data.get("short_name") == "War"
        and int(character.get("level", 1) or 1) >= 17
    ):
        for damage_type in ("Bludgeoning", "Piercing", "Slashing"):
            records.append(resistance_record(
                damage_type,
                {
                    "type": "subclass_feature",
                    "class_name": "Cleric",
                    "subclass_name": subclass_data.get("name", "War Domain"),
                    "feature_name": "Avatar of Battle",
                    "level": 17,
                },
            ))
    for feat in character.get("general_feats", []) or []:
        feat_name = feat.get("name") if isinstance(feat, dict) else feat
        choices = feat.get("choices", {}) if isinstance(feat, dict) else {}
        if feat_name == "Boon of Energy Resistance":
            for damage_type in choices.get("damage_types", []):
                records.append(resistance_record(
                    damage_type,
                    {
                        "type": "feat",
                        "source_name": "Boon of Energy Resistance",
                    },
                ))
    return merge_resistance_records(records)


def resistance_record(damage_type, source):
    return {
        "type": damage_type,
        "source": source,
    }


def merge_resistance_records(records):
    merged = {}
    for record in records or []:
        damage_type = record.get("type", "")
        if not damage_type:
            continue
        current = merged.setdefault(damage_type, {
            "type": damage_type,
            "sources": [],
            "source_names": [],
        })
        source = record.get("source", {})
        if source and source not in current["sources"]:
            current["sources"].append(source)
        source_name = source.get("source_name") or source.get("feature_name") or source.get("type", "")
        if source_name and source_name not in current["source_names"]:
            current["source_names"].append(source_name)
    return list(merged.values())


def resistance_resource_summary(resistances):
    if not resistances:
        return {}
    return {
        "damage_resistances": [
            resistance.get("type", "")
            for resistance in resistances
            if resistance.get("type")
        ],
        "damage_resistance_sources": {
            resistance.get("type", ""): resistance.get("source_names", [])
            for resistance in resistances
            if resistance.get("type")
        },
    }


def battle_master_resources(character):
    save_ability = character.get("class_options", {}).get("battle_master_save_ability")
    if save_ability not in {"Strength", "Dexterity"}:
        strength = character["ability_modifiers"].get("Strength", 0)
        dexterity = character["ability_modifiers"].get("Dexterity", 0)
        save_ability = "Strength" if strength >= dexterity else "Dexterity"
    save_modifier = character["ability_modifiers"].get(save_ability, 0)
    progression = battle_master_progression(character.get("level", 1))
    return {
        "battle_master": {
            "maneuvers_known": progression["maneuvers_known"],
            "superiority_dice_max": progression["superiority_dice"],
            "superiority_die": progression["superiority_die"],
        },
        "maneuvers_known": progression["maneuvers_known"],
        "superiority_dice": progression["superiority_dice"],
        "superiority_die": progression["superiority_die"],
        "maneuver_save_ability": save_ability,
        "maneuver_save_dc": 8 + character.get("proficiency_bonus", 2) + save_modifier,
    }


def calculate_speed_details(character, class_data, species_data):
    base_speed = int(species_data.get("speed", 30) or 30)
    modifiers = []
    equipment = set(character.get("equipment", []))
    has_shield = "Shield" in equipment
    armor_categories = [
        formula["category"]
        for armor_name, formula in ARMOR_FORMULAS.items()
        if armor_name in equipment
    ]

    speed_bonus = feat_speed_bonus(character)
    if speed_bonus:
        modifiers.append(speed_modifier("feat_speed_bonus", "Feat speed bonus", speed_bonus, "feat", True))

    class_name = class_data.get("name", character.get("class", ""))
    level = int(character.get("level", 1) or 1)
    if class_name == "Barbarian" and level >= 5:
        modifiers.append(speed_modifier(
            "barbarian_fast_movement",
            "Fast Movement",
            10,
            "class_feature",
            "heavy" not in armor_categories,
            {"maximum_armor_category": "medium"},
        ))

    monk_bonus = int(get_class_resources(class_data, level).get("unarmored_movement", 0) or 0)
    if class_name == "Monk" and monk_bonus:
        modifiers.append(speed_modifier(
            "monk_unarmored_movement",
            "Unarmored Movement",
            monk_bonus,
            "class_feature",
            not armor_categories and not has_shield,
            {"requires_no_armor": True, "requires_no_shield": True},
        ))

    return {
        "base": base_speed,
        "value": base_speed + sum(modifier["amount"] for modifier in modifiers if modifier["applies"]),
        "modifiers": modifiers,
    }


def speed_modifier(modifier_id, name, amount, source_type, applies, conditions=None):
    return {
        "id": modifier_id,
        "name": name,
        "amount": amount,
        "source": {"type": source_type, "source_name": name},
        "conditions": conditions or {},
        "applies": applies,
    }


def spellcasting_resources(character, spellcasting):
    ability = spellcasting.get("ability", "")
    modifier = character["ability_modifiers"].get(ability, 0)
    resources = {
        "spellcasting_ability": ability,
        "spell_save_dc": 8 + character.get("proficiency_bonus", 2) + modifier,
        "spell_attack_bonus": character.get("proficiency_bonus", 2) + modifier,
    }
    if spellcasting.get("spell_slots"):
        resources["spell_slots"] = spellcasting.get("spell_slots", {})
    return resources


def subclass_resources(character, class_data, subclass_data):
    if character.get("level", 1) < 3 or not subclass_data:
        return {}

    active_grants = get_active_subclass_grants(subclass_data, character.get("level", 1))
    resources = dict(active_grants.get("resources", {}))
    short_name = subclass_data.get("short_name", "")
    class_name = class_data.get("name", character.get("class", ""))
    modifiers = character.get("ability_modifiers", {})

    if short_name == "Assassin":
        resources["initiative_advantage"] = True
        resources["assassinate_extra_damage"] = character.get("level", 3)
    if short_name == "Thief":
        resources["climb_speed"] = character.get("speed", 30)
        resources["jump_ability"] = "Dexterity"
    if class_name == "Cleric":
        if "Preserve Life" in subclass_features_up_to_level(class_data, short_name, character.get("level", 1)):
            resources["preserve_life_pool"] = character.get("level", 1) * 5
        if short_name in {"Light", "War"}:
            key = "warding_flare_uses" if short_name == "Light" else "war_priest_uses"
            resources[key] = max(1, modifiers.get("Wisdom", 0))
        if short_name == "Light" and character.get("level", 1) >= 17:
            resources["corona_of_light_uses"] = max(1, modifiers.get("Wisdom", 0))
            resources["corona_of_light_recharge"] = "long_rest"
    if class_name == "Wizard":
        if short_name == "Abjurer":
            resources["arcane_ward_max_hp"] = (character.get("level", 1) * 2) + modifiers.get("Intelligence", 0)
        if short_name == "Diviner":
            resources["portent_dice"] = 3 if character.get("level", 1) >= 14 else 2
    if class_name == "Paladin" and short_name == "Glory" and character.get("level", 1) >= 15:
        resources["glorious_defense_uses"] = max(1, modifiers.get("Charisma", 0))
        resources["glorious_defense_recharge"] = "long_rest"
    if class_name == "Barbarian" and short_name == "Berserker" and character.get("level", 1) >= 14:
        resources["intimidating_presence_free_uses"] = 1
        resources["intimidating_presence_recharge"] = "long_rest"
        resources["intimidating_presence_alternate_recovery_resource"] = "Rage"
    if class_name == "Rogue" and short_name == "Soulknife" and character.get("level", 1) >= 13:
        resources["psychic_veil_free_uses"] = 1
        resources["psychic_veil_recharge"] = "long_rest"
        resources["psychic_veil_alternate_recovery_resource"] = "Psionic Energy Die"
    if class_name == "Fighter" and short_name == "Psi Warrior" and character.get("level", 1) >= 15:
        resources["bulwark_of_force_free_uses"] = 1
        resources["bulwark_of_force_targets"] = max(1, modifiers.get("Intelligence", 0))
        resources["bulwark_of_force_recharge"] = "long_rest"
        resources["bulwark_of_force_alternate_recovery_resource"] = "Psionic Energy Die"
    paladin_capstones = {
        "Devotion": "holy_nimbus",
        "Glory": "living_legend",
        "Vengeance": "avenging_angel",
        "Ancients": "elder_champion",
    }
    if class_name == "Paladin" and short_name in paladin_capstones and character.get("level", 1) >= 20:
        key = paladin_capstones[short_name]
        resources[f"{key}_free_uses"] = 1
        resources[f"{key}_recharge"] = "long_rest"
        resources[f"{key}_alternate_recovery_resource"] = "Level 5 spell slot"

    return resources


def class_feature_saving_throw_proficiencies(character, class_data):
    class_name = class_data.get("name", character.get("class", ""))
    level = int(character.get("level", 1) or 1)
    if class_name == "Monk" and level >= 14:
        return list(ABILITIES)
    if class_name == "Rogue" and level >= 15:
        return ["Wisdom", "Charisma"]
    return []


def subclass_tool_proficiencies(subclass_data):
    if subclass_data.get("short_name") == "Assassin":
        return ["Disguise Kit", "Poisoner's Kit"]
    if subclass_data.get("short_name") == "Mercy":
        return ["Herbalism Kit"]
    return []


def subclass_armor_proficiencies(subclass_data):
    if subclass_data.get("short_name") == "Valor":
        return ["Medium Armor", "Shields"]
    return []


def subclass_weapon_proficiencies(subclass_data):
    if subclass_data.get("short_name") == "Valor":
        return ["Martial Weapons"]
    return []


def subclass_skill_proficiencies(subclass_data):
    if subclass_data.get("short_name") == "Mercy":
        return ["Insight", "Medicine"]
    return []


def selected_structured_subclass_spells(character, subclass_data):
    rule = subclass_data.get("subclass_options", {}).get("structured_spell_choice", {})
    selected = active_structured_spell_choice(character, subclass_data)
    if not rule or not selected:
        return []
    for option in rule.get("options", []):
        if selected in {option.get("id"), option.get("name")}:
            return option_spells_for_level(option, character.get("level", 1))
    return []


def active_structured_spell_choice(character, subclass_data):
    rule = subclass_data.get("subclass_options", {}).get("structured_spell_choice", {})
    selected = ""
    for config in character.get("feature_configurations", []) or []:
        if config.get("feature_id") == "structured_spell_choice":
            selected = config.get("current_value", "")
            break
    return selected or character.get("class_options", {}).get("structured_spell_choice", "")


def option_spells_for_level(option, character_level):
    spells_by_level = option.get("granted_spells_by_level", {})
    if not spells_by_level:
        return list(option.get("granted_spells", []))
    spells = []
    for level, level_spells in spells_by_level.items():
        if int(level) <= int(character_level or 1):
            spells.extend(level_spells)
    return merge_unique(spells)


def structured_subclass_spell_grant_records(character, subclass_data):
    spells = selected_structured_subclass_spells(character, subclass_data)
    if not spells:
        return []
    return [
        {
            "name": spell,
            "source": {
                "type": "subclass",
                "subclass_name": subclass_data.get("name", ""),
                "subclass_id": subclass_data.get("id", ""),
                "source": subclass_data.get("source", ""),
            },
            "spellcasting_ability": character.get("spellcasting_ability", ""),
            "grant_type": "structured_subclass_spell",
            "always_prepared": True,
            "counts_against_limit": False,
        }
        for spell in spells
    ]


CLASS_OPTION_SPELL_GRANTS = {
    "blessed_warrior_cantrips": {
        "source_name": "Blessed Warrior",
        "grant_type": "fighting_style_cantrip",
        "level_gained": 2,
    },
    "druidic_warrior_cantrips": {
        "source_name": "Druidic Warrior",
        "grant_type": "fighting_style_cantrip",
        "level_gained": 2,
    },
    "magical_discoveries": {
        "source_name": "Magical Discoveries",
        "grant_type": "magical_discoveries",
        "level_gained": 6,
    },
    "mystic_arcanum": {
        "source_name": "Mystic Arcanum",
        "grant_type": "mystic_arcanum",
        "level_gained": 11,
    },
    "spell_mastery_level_1": {
        "source_name": "Spell Mastery",
        "grant_type": "spell_mastery",
        "level_gained": 18,
        "casting_rules": {"at_will_lowest_level": True, "can_use_spell_slots": True},
    },
    "spell_mastery_level_2": {
        "source_name": "Spell Mastery",
        "grant_type": "spell_mastery",
        "level_gained": 18,
        "casting_rules": {"at_will_lowest_level": True, "can_use_spell_slots": True},
    },
    "signature_spells": {
        "source_name": "Signature Spells",
        "grant_type": "signature_spells",
        "level_gained": 20,
        "casting_rules": {
            "free_casts": 1,
            "free_cast_spell_level": 3,
            "recharge": "short_or_long_rest",
            "can_use_spell_slots": True,
        },
    },
}


def class_option_spell_grant_records(character):
    sync_mystic_arcanum_class_options(character)
    records = []
    class_options = character.get("class_options", {})
    for key, grant_rule in CLASS_OPTION_SPELL_GRANTS.items():
        selected = active_class_option_value(character, key, class_options.get(key, []))
        if isinstance(selected, str):
            selected = [selected] if selected else []
        for spell in selected or []:
            if not spell:
                continue
            records.append({
                "name": spell,
                "source": {
                    "type": "class_option",
                    "source_name": grant_rule["source_name"],
                    "class_name": character.get("class", ""),
                    "level_gained": grant_rule["level_gained"],
                },
                "spellcasting_ability": character.get("spellcasting_ability", ""),
                "grant_type": grant_rule["grant_type"],
                "always_prepared": True,
                "counts_against_limit": False,
                "casting_rules": grant_rule.get("casting_rules", {}),
            })
    return records


def active_class_option_value(character, key, default_value):
    config = next(
        (
            item
            for item in character.get("feature_configurations", []) or []
            if item.get("feature_id") == key and item.get("current_value")
        ),
        None,
    )
    if config:
        return config.get("current_value", default_value)
    return default_value


def merge_spell_grant_records(*record_lists):
    merged = []
    seen = set()
    for records in record_lists:
        for record in records or []:
            key = (
                record.get("name", ""),
                record.get("source", {}).get("type", ""),
                record.get("source", {}).get("subclass_name", ""),
                record.get("grant_type", ""),
            )
            if record.get("name") and key not in seen:
                merged.append(dict(record))
                seen.add(key)
    return merged


def spell_grant_records_with_ability(records, fallback_ability):
    updated = []
    for record in records or []:
        item = dict(record)
        if not item.get("spellcasting_ability"):
            item["spellcasting_ability"] = fallback_ability
        updated.append(item)
    return updated


def recalculate_character(character, data):
    classes_by_name = data["classes_by_name"]
    species_by_name = data["species_by_name"]
    backgrounds_by_name = data["backgrounds_by_name"]
    skill_to_ability = data["rules"]["skills"]

    class_data = classes_by_name.get(character.get("class"), {})
    species_data = species_by_name.get(character.get("species"), {})
    background_data = backgrounds_by_name.get(character.get("background"), {})

    character["level"] = normalize_level(character.get("level", 1))
    base_scores = character.get("base_ability_scores") or character.get("ability_scores", {})
    for ability in ABILITIES:
        base_scores.setdefault(ability, 10)
    character["base_ability_scores"] = base_scores
    background_bonuses = calculate_background_ability_bonuses(character, background_data)
    automatic_ability_adjustments = class_feature_ability_adjustments(character, class_data)
    character["ability_scores"], source_bonuses = apply_source_ability_adjustments(
        character["base_ability_scores"],
        background_bonuses,
        [
            *character.get("ability_score_adjustments", []),
            *automatic_ability_adjustments,
        ],
    )
    character["ability_score_adjustment_bonuses"] = source_bonuses
    character["ability_score_bonuses"] = {
        ability: int(background_bonuses.get(ability, 0)) + int(source_bonuses.get(ability, 0))
        for ability in ABILITIES
    }
    character["ability_modifiers"] = calculate_ability_modifiers(character["ability_scores"])
    character["proficiency_bonus"] = proficiency_bonus_for_level(character["level"])
    ensure_level_tracking(character)
    refresh_feature_configurations(character, class_data, data)

    speed_details = calculate_speed_details(character, class_data, species_data)
    character["speed"] = speed_details["value"]
    character["speed_details"] = speed_details
    character["speed_modifiers"] = speed_details["modifiers"]
    character["size"] = species_data.get("size", "")
    character["species_traits"] = species_data.get("traits", [])
    character["languages"] = merge_unique(
        species_data.get("languages", []),
        background_data.get("languages", []),
        class_choice_languages(character),
    )

    character["background_feature"] = background_data.get("feature", "")
    character["origin_feats"] = merge_unique(
        background_data.get("origin_feats", []),
        character.get("background_options", {}).get("origin_feats", []),
    )
    feat_grants = feat_grants_for_character(character)
    subclass_data = selected_subclass_data(class_data, character.get("subclass", ""))
    character["saving_throw_proficiencies"] = merge_unique(
        class_data.get("saving_throw_proficiencies", []),
        class_choice_saving_throw_proficiencies(character),
        feat_grants.get("saving_throw_proficiencies", []),
        class_feature_saving_throw_proficiencies(character, class_data),
    )
    character["armor_proficiencies"] = merge_unique(
        class_data.get("armor_proficiencies", []),
        feat_grants.get("armor_proficiencies", []),
        subclass_armor_proficiencies(subclass_data),
    )
    character["weapon_proficiencies"] = merge_unique(
        class_data.get("weapon_proficiencies", []),
        feat_grants.get("weapon_proficiencies", []),
        subclass_weapon_proficiencies(subclass_data),
    )
    if class_data.get("name") == "Cleric" and character.get("class_options", {}).get("divine_order") == "Protector":
        character["armor_proficiencies"] = merge_unique(character["armor_proficiencies"], ["Heavy Armor"])
        character["weapon_proficiencies"] = merge_unique(character["weapon_proficiencies"], ["Martial Weapons"])
    if class_data.get("name") == "Druid" and character.get("class_options", {}).get("primal_order") == "Warden":
        character["armor_proficiencies"] = merge_unique(character["armor_proficiencies"], ["Medium Armor"])
        character["weapon_proficiencies"] = merge_unique(character["weapon_proficiencies"], ["Martial Weapons"])
    character["tool_proficiencies"] = merge_unique(
        background_data.get("tool_proficiencies", []),
        character.get("background_options", {}).get("tool_proficiencies", []),
        character.get("origin_feat_choices", {}).get("tools", []),
        class_data.get("tool_proficiencies", []),
        feat_grants.get("tool_proficiencies", []),
        [character.get("class_options", {}).get("student_of_war_tool", "")],
        subclass_tool_proficiencies(subclass_data),
    )
    spellcasting = effective_spellcasting(class_data, character.get("subclass", ""), character.get("level", 1))
    character["spellcasting_ability"] = spellcasting.get("ability", "") if spellcasting else ""
    if character.get("class") == "Wizard":
        character.setdefault("spells", {}).setdefault("spellbook", [])
        if character["spells"].get("known"):
            character["spells"]["spellbook"] = merge_unique(
                character["spells"].get("spellbook", []),
                character["spells"].get("known", []),
            )
            character["spells"]["known"] = []
        character["spellbook_spells"] = wizard_spellbook_spells(character)
        character["prepared_spells"] = character.get("spells", {}).get("prepared", [])
        character["prepared_spell_limit"] = spellcasting.get("prepared_spells", 0) if spellcasting else 0
    active_subclass_grants = get_active_subclass_grants(subclass_data, character.get("level", 1))
    character["subclass_granted_spells"] = merge_unique(
        spellcasting.get("granted_cantrips", []) if spellcasting else [],
        active_subclass_grants.get("granted_cantrips", []),
        active_subclass_grants.get("always_known_spells", []),
        active_subclass_grants.get("always_prepared_spells", []),
        selected_structured_subclass_spells(character, subclass_data),
    )
    character["feat_spell_grant_details"] = feat_spell_grant_records(character)
    character["class_option_spell_grant_details"] = merge_spell_grant_records(
        class_option_spell_grant_records(character),
        mystic_arcanum_grant_records(character),
    )
    character["subclass_spell_grant_details"] = merge_spell_grant_records(
        spell_grant_records_with_ability(
            active_subclass_grants.get("spell_grants", []),
            character.get("spellcasting_ability", ""),
        ),
        structured_subclass_spell_grant_records(character, subclass_data),
    )
    character["spell_grant_details"] = merge_spell_grant_records(
        character["subclass_spell_grant_details"],
        character["class_option_spell_grant_details"],
        character["feat_spell_grant_details"],
        feature_spell_grant_records(character, class_data),
    )
    character["spellcasting_sources"] = spellcasting_sources_for_character(character, spellcasting)
    character["savant_spell_records"] = merge_spell_grant_records(
        character.get("savant_spell_records", []),
        savant_spell_source_records(character),
    )
    character["subclass_known_spells"] = [] if character.get("class") == "Wizard" else character.get("class_options", {}).get("savant_spells", [])
    character["features"] = merge_unique(
        species_data.get("traits", []),
        [background_data.get("feature", "")],
        character.get("origin_feats", []),
        character.get("species_options", {}).get("origin_feats", []),
        general_feat_names(character),
        [
            value
            for key, value in character.get("species_options", {}).items()
            if key.endswith("_ancestry") or key.endswith("_lineage")
        ],
        [character.get("species_options", {}).get("lineage", "")],
        character.get("species_options", {}).get("lineage_spells", []),
        spell_grants(character),
        class_features_up_to_level(class_data, character["level"]),
        subclass_features_up_to_level(class_data, character.get("subclass", ""), character["level"]),
        selected_maneuver_features(character.get("class_options", {})),
        selected_class_option_features(character.get("class_options", {}), character.get("feature_configurations", [])),
        configured_feature_values(character),
    )
    character["feature_descriptions"] = feature_descriptions_for_character(
        character,
        data,
        class_data,
        species_data,
        background_data,
    )
    character["feature_related_features"] = related_features_for_character(character, class_data, subclass_data)

    background_skills = background_data.get("skill_proficiencies", [])
    class_skills = character.get("class_options", {}).get("class_skills", [])
    subclass_skills = merge_unique(
        [character.get("class_options", {}).get("student_of_war_skill", "")],
        character.get("class_options", {}).get("lore_skills", []),
        subclass_skill_proficiencies(subclass_data),
    )
    class_choice_skills = class_choice_skill_proficiencies(character)
    species_skills = character.get("species_options", {}).get("skill_proficiencies", [])
    feat_skills = character.get("origin_feat_choices", {}).get("skills", [])
    base_skill_proficiencies = merge_unique(
        background_skills,
        species_skills,
        class_skills,
        subclass_skills,
        class_choice_skills,
        feat_skills,
    )
    skill_feat_grants = feat_grants_for_character(character, base_skill_proficiencies)
    character["skill_proficiencies"] = merge_unique(
        base_skill_proficiencies,
        skill_feat_grants.get("skill_proficiencies", []),
    )
    character["expertise"] = merge_unique(
        character.get("expertise", []),
        class_choice_expertise(character),
        skill_feat_grants.get("expertise", []),
    )

    recalculate_hit_points(character, class_data, species_data)

    character["saving_throw_bonuses"] = calculate_saving_throw_bonuses(
        character["ability_modifiers"],
        character["saving_throw_proficiencies"],
        character["proficiency_bonus"],
    )
    character["skill_bonuses"] = calculate_skill_bonuses(
        skill_to_ability,
        character["ability_modifiers"],
        character["skill_proficiencies"],
        character.get("expertise", []),
        character["proficiency_bonus"],
    )
    character["initiative"] = character["ability_modifiers"].get("Dexterity", 0)
    if "Alert" in active_origin_feats(character):
        character["initiative"] += character["proficiency_bonus"]
    character["derived_resources"] = calculate_class_resources(character, class_data)
    character["senses"] = calculate_senses(character, class_data)
    character["derived_resources"].update(sense_resource_summary(character["senses"]))
    character["damage_resistances"] = calculate_damage_resistances(character, class_data)
    character["derived_resources"].update(resistance_resource_summary(character["damage_resistances"]))
    character["armor_class"] = calculate_armor_class(character)
    character["spell_metadata"] = spell_metadata_for_character(character, data)
    character["spell_descriptions"] = spell_descriptions_for_character(character, data)
    return character


def feature_descriptions_for_character(character, data, class_data, species_data, background_data):
    descriptions = {}
    descriptions.update(data.get("rules", {}).get("feature_descriptions", {}))
    descriptions.update(species_data.get("trait_descriptions", {}))
    descriptions.update(background_data.get("feature_descriptions", {}))
    descriptions.update(class_data.get("feature_descriptions", {}))
    descriptions.update({
        feat.get("name"): feat.get("description", "")
        for feat in data.get("feats", [])
        if feat.get("description")
    })
    subclass_data = selected_subclass_data(class_data, character.get("subclass", ""))
    descriptions.update(subclass_data.get("feature_descriptions", {}))

    for feat in active_origin_feats(character):
        description = descriptions.get(feat)
        if description:
            descriptions[f"Origin Feat: {feat}"] = description
    return descriptions


def related_features_for_character(character, class_data, subclass_data):
    related = {}
    related.update(class_data.get("feature_related_features", {}))
    related.update(subclass_data.get("feature_related_features", {}))
    return related


def spell_descriptions_for_character(character, data):
    spell_lookup = {
        spell.get("name"): spell
        for spell in data.get("spells", [])
    }
    return {
        name: spell_lookup.get(name, {}).get("description", "")
        for name in selected_spell_names(character)
        if spell_lookup.get(name, {}).get("description", "")
    }


def spell_metadata_for_character(character, data):
    spell_lookup = {
        spell.get("name"): spell
        for spell in data.get("spells", [])
    }
    metadata = {}
    for name in selected_spell_names(character):
        spell = spell_lookup.get(name, {})
        if not spell:
            continue
        metadata[name] = {
            "level": spell.get("level"),
            "school": spell.get("school", ""),
            "casting_time": spell.get("casting_time", ""),
            "range": spell.get("range", ""),
            "duration": spell.get("duration", ""),
        }
    return metadata


def selected_spell_names(character):
    return merge_unique(
        character.get("spells", {}).get("cantrips", []),
        wizard_spellbook_spells(character),
        character.get("spells", {}).get("known", []),
        character.get("subclass_known_spells", []),
        selected_savant_spells(character),
        character.get("spells", {}).get("prepared", []),
        spell_grants(character),
    )


def selected_maneuver_features(class_options):
    return [
        f"Maneuver: {maneuver}"
        for maneuver in class_options.get("maneuvers", [])
    ]


def spellcasting_sources_for_character(character, class_spellcasting):
    sources = []
    if class_spellcasting and character.get("spellcasting_ability"):
        class_name = character.get("class", "")
        sources.append(spellcasting_source_record(
            f"{class_name} Spellcasting" if class_name else "Spellcasting",
            "class",
            character.get("spellcasting_ability", ""),
            character,
        ))
    seen = {(source["source_name"], source["ability"]) for source in sources}
    for record in character.get("spell_grant_details", []):
        ability = record.get("spellcasting_ability", "")
        source = record.get("source", {})
        source_name = source.get("source_name") or source.get("subclass_name") or source.get("type", "")
        key = (source_name, ability)
        if ability and source_name and key not in seen:
            sources.append(spellcasting_source_record(source_name, source.get("type", ""), ability, character))
            seen.add(key)
    return sources


def spellcasting_source_record(source_name, source_type, ability, character):
    modifier = character.get("ability_modifiers", {}).get(ability, 0)
    proficiency = character.get("proficiency_bonus", 2)
    return {
        "source_name": source_name,
        "source_type": source_type,
        "ability": ability,
        "spell_save_dc": 8 + proficiency + modifier,
        "spell_attack_bonus": proficiency + modifier,
    }


def slug(value):
    return "".join(char.lower() if char.isalnum() else "_" for char in str(value)).strip("_")


def recalculate_hit_points(character, class_data, species_data):
    hit_die = class_data.get("hit_die", 0)
    class_name = class_data.get("name", character.get("class", ""))
    if hit_die and class_name:
        ensure_hp_history(character, class_name, hit_die)
    maximum_hp = calculate_max_hit_points(
        character.get("hp_history", []),
        character["ability_modifiers"].get("Constitution", 0),
        active_origin_feats(character),
        species_data.get("traits", []),
    )
    maximum_hp += subclass_hit_point_bonus(character, class_data)
    if has_general_feat(character, "Boon of Fortitude"):
        maximum_hp += 40
    previous = character.get("hit_points", {})
    previous_max = int(previous.get("max", previous.get("maximum", maximum_hp)) or 0)
    previous_current = int(previous.get("current", maximum_hp) or 0)
    pending_increase = int(character.pop("_pending_current_hp_increase", 0) or 0)
    if pending_increase:
        current_hp = min(maximum_hp, previous_current + pending_increase)
    elif previous_max == 0 and previous_current == 0:
        current_hp = maximum_hp
    else:
        current_hp = min(previous_current, maximum_hp)
    character["hit_points"] = {
        "max": maximum_hp,
        "maximum": maximum_hp,
        "current": max(0, current_hp),
        "temporary": int(previous.get("temporary", 0) or 0),
        "hit_die": hit_die_label(hit_die),
    }
    if class_name:
        character.setdefault("hit_dice", {})[class_name] = character["level"]


def subclass_hit_point_bonus(character, class_data):
    if (
        class_data.get("name", character.get("class", "")) == "Sorcerer"
        and character.get("subclass") == "Draconic Sorcery"
        and int(character.get("level", 1) or 1) >= 3
    ):
        return int(character.get("level", 1) or 1)
    return 0
