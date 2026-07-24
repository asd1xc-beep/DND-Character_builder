from copy import deepcopy

from models.character import ABILITIES, merge_unique
from rules.ability_scores import format_modifier
from rules.attack_profiles import build_attack_profiles
from rules.feat_grants import feat_grants_for_character
from rules.feat_rules import general_feat_names
from rules.mystic_arcanum import mystic_arcanum_grant_records
from rules.wizard_spellbook import wizard_spellbook_spells


def active_origin_feats(character):
    return merge_unique(
        character.get("origin_feats", []),
        character.get("background_options", {}).get("origin_feats", []),
        character.get("species_options", {}).get("origin_feats", []),
    )


def spell_grants(character):
    choices = character.get("origin_feat_choices", {})
    grants = []
    if choices.get("cantrips"):
        grants.extend(choices["cantrips"])
    if choices.get("spell"):
        grants.append(choices["spell"])
    grants.extend(character.get("species_options", {}).get("lineage_spells", []))
    grants.extend(character.get("class_options", {}).get("extra_cantrips", []))
    grants.extend(character.get("class_options", {}).get("blessed_warrior_cantrips", []))
    grants.extend(character.get("class_options", {}).get("druidic_warrior_cantrips", []))
    grants.extend(character.get("class_options", {}).get("magical_discoveries", []))
    grants.extend(character.get("class_options", {}).get("mystic_arcanum", []))
    grants.extend(character.get("subclass_granted_spells", []))
    grants.extend(record.get("name", "") for record in character.get("spell_grant_details", []))
    grants.extend(record.get("name", "") for record in mystic_arcanum_grant_records(character))
    grants.extend(feat_grants_for_character(character).get("spell_grants", []))
    return merge_unique(grants)


def build_character_sheet(character, data=None):
    character = deepcopy(character)
    return {
        "identity": {
            "name": character.get("name", ""),
            "level": character.get("level", 1),
            "species": character.get("species", ""),
            "background": character.get("background", ""),
            "class": character.get("class", ""),
            "subclass": character.get("subclass", ""),
            "size": character.get("size", ""),
            "speed": character.get("speed", 30),
            "notes": character.get("notes", ""),
        },
        "core_stats": {
            "armor_class": character.get("armor_class", 10),
            "armor_class_details": character.get("armor_class_details", {}),
            "initiative": character.get("initiative", 0),
            "initiative_display": format_modifier(character.get("initiative", 0)),
            "proficiency_bonus": character.get("proficiency_bonus", 2),
            "proficiency_bonus_display": format_modifier(character.get("proficiency_bonus", 2)),
            "hit_points": character.get("hit_points", {}),
            "hit_die": character.get("hit_points", {}).get("hit_die", ""),
        },
        "abilities": [
            {
                "name": ability,
                "base": character.get("base_ability_scores", {}).get(ability, 10),
                "bonus": character.get("ability_score_bonuses", {}).get(ability, 0),
                "score": character.get("ability_scores", {}).get(ability, 10),
                "modifier": character.get("ability_modifiers", {}).get(ability, 0),
                "modifier_display": format_modifier(character.get("ability_modifiers", {}).get(ability, 0)),
            }
            for ability in ABILITIES
        ],
        "saving_throws": [
            {
                "name": name,
                "bonus": bonus,
                "bonus_display": format_modifier(bonus),
                "proficient": name in character.get("saving_throw_proficiencies", []),
            }
            for name, bonus in character.get("saving_throw_bonuses", {}).items()
        ],
        "skills": [
            {
                "name": name,
                "bonus": bonus,
                "bonus_display": format_modifier(bonus),
                "proficient": name in character.get("skill_proficiencies", []),
                "expertise": name in character.get("expertise", []),
            }
            for name, bonus in character.get("skill_bonuses", {}).items()
        ],
        "proficiencies": {
            "armor": character.get("armor_proficiencies", []),
            "weapons": character.get("weapon_proficiencies", []),
            "tools": character.get("tool_proficiencies", []),
            "languages": character.get("languages", []),
        },
        "features": character.get("features", []),
        "feature_details": feature_details(character),
        "origin_feats": active_origin_feats(character),
        "general_feats": general_feat_names(character),
        "general_feat_details": general_feat_details(character),
        "resources": character.get("derived_resources", {}),
        "senses": character.get("senses", []),
        "damage_resistances": character.get("damage_resistances", []),
        "weapon_masteries": character.get("weapon_masteries", []),
        "spells": {
            "cantrips": character.get("spells", {}).get("cantrips", []),
            "spellbook": wizard_spellbook_spells(character),
            "prepared_limit": character.get("prepared_spell_limit", 0),
            "known": merge_unique(
                character.get("spells", {}).get("known", []),
                character.get("subclass_known_spells", []),
            ),
            "prepared": character.get("spells", {}).get("prepared", []),
            "granted": spell_grants(character),
            "grant_details": spell_grant_details(character),
            "by_level": spells_by_level(character),
            "spellcasting_ability": spellcasting_ability(character),
            "spellcasting_sources": character.get("spellcasting_sources", []),
        },
        "spell_details": spell_details(character),
        "equipment": character.get("equipment", []),
        "attack_profiles": build_attack_profiles(character, data),
        "raw_choices": {
            "species_options": character.get("species_options", {}),
            "background_options": character.get("background_options", {}),
            "class_options": character.get("class_options", {}),
            "origin_feat_choices": character.get("origin_feat_choices", {}),
        },
    }


def spellcasting_ability(character):
    class_ability = character.get("spellcasting_ability", "")
    if class_ability:
        return class_ability
    origin_ability = character.get("origin_feat_choices", {}).get("spellcasting_ability", "")
    if origin_ability:
        return origin_ability
    lineage_ability = character.get("species_options", {}).get("lineage_spellcasting_ability", "")
    if lineage_ability:
        return lineage_ability
    return ""


def feature_details(character):
    descriptions = character.get("feature_descriptions", {})
    related_features = character.get("feature_related_features", {})
    return [
        {
            "name": feature,
            "description": descriptions.get(feature, ""),
            "related_features": related_features.get(feature, []),
        }
        for feature in character.get("features", [])
    ]


def spell_details(character):
    descriptions = character.get("spell_descriptions", {})
    metadata = character.get("spell_metadata", {})
    spell_groups = character.get("spells", {})
    spell_names = merge_unique(
        spell_groups.get("cantrips", []),
        spell_groups.get("spellbook", []),
        spell_groups.get("known", []),
        character.get("subclass_known_spells", []),
        spell_groups.get("prepared", []),
        spell_grants(character),
    )
    return [
        {
            "name": spell,
            "level": metadata.get(spell, {}).get("level"),
            "level_label": spell_level_label(metadata.get(spell, {}).get("level")),
            "school": metadata.get(spell, {}).get("school", ""),
            "sources": spell_sources(spell, character),
            "description": descriptions.get(spell, ""),
        }
        for spell in spell_names
    ]


def spell_grant_details(character):
    return list(character.get("spell_grant_details", [])) or list(character.get("subclass_spell_grant_details", []))


def spell_sources(spell, character):
    sources = []
    for grant in spell_grant_details(character) + list(character.get("savant_spell_records", [])):
        if grant.get("name") != spell:
            continue
        source = grant.get("source", {})
        if source.get("feature_name") == "Savant" and source.get("level"):
            source_name = f"{source.get('subclass_name', '')} {source['feature_name']} Level {source['level']}".strip()
        else:
            source_name = source.get("feature_name") or source.get("source_name") or source.get("subclass_name") or source.get("type", "")
        if source_name and source_name not in sources:
            sources.append(source_name)
    return sources


def general_feat_details(character):
    details = []
    for feat in character.get("general_feats", []) or []:
        if isinstance(feat, dict):
            details.append({
                "instance_id": feat.get("instance_id", ""),
                "feat_id": feat.get("feat_id", ""),
                "name": feat.get("name", ""),
                "source": feat.get("source", {}),
                "choices": {
                    key: value
                    for key, value in feat.get("choices", {}).items()
                    if value not in ("", [], {})
                },
            })
        elif feat:
            details.append({
                "instance_id": "",
                "feat_id": "",
                "name": feat,
                "source": {"type": "legacy"},
                "choices": {},
            })
    return details


def spells_by_level(character):
    metadata = character.get("spell_metadata", {})
    grouped = {}
    for spell in merge_unique(
        character.get("spells", {}).get("cantrips", []),
        wizard_spellbook_spells(character),
        character.get("spells", {}).get("known", []),
        character.get("subclass_known_spells", []),
        character.get("spells", {}).get("prepared", []),
        spell_grants(character),
    ):
        level = metadata.get(spell, {}).get("level")
        key = level if isinstance(level, int) else "unknown"
        grouped.setdefault(key, []).append(spell)
    return grouped


def spell_level_label(level):
    if level == 0:
        return "Cantrip"
    if isinstance(level, int):
        return f"Level {level}"
    return "Unknown level"
