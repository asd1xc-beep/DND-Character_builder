from rules.leveling import selected_subclass_data


CLASS_FEATURE_SPELL_GRANTS = [
    {
        "grant_id": "bard_words_of_creation_power_word_heal",
        "class_name": "Bard",
        "level": 20,
        "feature_name": "Words of Creation",
        "spell": "Power Word Heal",
        "spellcasting_ability": "Charisma",
        "always_prepared": True,
        "counts_against_limit": False,
        "casting_rules": {
            "can_target_second_creature_within_10_feet": True,
        },
    },
    {
        "grant_id": "bard_words_of_creation_power_word_kill",
        "class_name": "Bard",
        "level": 20,
        "feature_name": "Words of Creation",
        "spell": "Power Word Kill",
        "spellcasting_ability": "Charisma",
        "always_prepared": True,
        "counts_against_limit": False,
        "casting_rules": {
            "can_target_second_creature_within_10_feet": True,
        },
    },
    {
        "grant_id": "warlock_contact_patron",
        "class_name": "Warlock",
        "level": 9,
        "feature_name": "Contact Patron",
        "spell": "Contact Other Plane",
        "spellcasting_ability": "Charisma",
        "always_prepared": True,
        "counts_against_limit": False,
        "casting_rules": {
            "free_casts": 1,
            "recharge": "long_rest",
            "uses_spell_slots": False,
            "auto_success": True,
            "special_target": "patron",
        },
    },
]


SUBCLASS_FEATURE_SPELL_GRANTS = [
    {
        "grant_id": "wild_heart_nature_speaker",
        "class_name": "Barbarian",
        "subclass_short_name": "Wild Heart",
        "level": 10,
        "feature_name": "Nature Speaker",
        "spell": "Commune with Nature",
        "spellcasting_ability": "Wisdom",
        "always_prepared": True,
        "counts_against_limit": False,
        "casting_rules": {
            "ritual_only": True,
            "uses_spell_slots": False,
        },
    },
    {
        "grant_id": "fey_wanderer_misty_wanderer",
        "class_name": "Ranger",
        "subclass_short_name": "Fey Wanderer",
        "level": 15,
        "feature_name": "Misty Wanderer",
        "spell": "Misty Step",
        "spellcasting_ability": "Wisdom",
        "always_prepared": True,
        "counts_against_limit": False,
        "free_casts_from": {"ability": "Wisdom", "minimum": 1},
        "casting_rules": {
            "recharge": "long_rest",
            "uses_spell_slots": False,
            "can_bring_willing_creature": True,
        },
    },
    {
        "grant_id": "psi_warrior_telekinetic_master",
        "class_name": "Fighter",
        "subclass_short_name": "Psi Warrior",
        "level": 18,
        "feature_name": "Telekinetic Master",
        "spell": "Telekinesis",
        "spellcasting_ability": "Intelligence",
        "always_prepared": True,
        "counts_against_limit": False,
        "casting_rules": {
            "free_casts": 1,
            "recharge": "long_rest",
            "uses_spell_slots": False,
            "alternate_recovery_resource": "Psionic Energy Die",
            "bonus_action_weapon_attack_while_concentrating": True,
        },
    },
    {
        "grant_id": "draconic_sorcery_dragon_companion",
        "class_name": "Sorcerer",
        "subclass_short_name": "Draconic",
        "level": 18,
        "feature_name": "Dragon Companion",
        "spell": "Summon Dragon",
        "spellcasting_ability": "Charisma",
        "always_prepared": True,
        "counts_against_limit": False,
        "casting_rules": {
            "free_casts": 1,
            "recharge": "long_rest",
            "uses_spell_slots": True,
            "material_component_required": False,
            "can_remove_concentration": True,
            "duration_when_no_concentration": "1 minute",
        },
    },
]


def feature_spell_grant_records(character, class_data):
    records = []
    class_name = class_data.get("name", character.get("class", ""))
    level = int(character.get("level", 1) or 1)
    subclass_data = selected_subclass_data(class_data, character.get("subclass", ""))
    subclass_short_name = subclass_data.get("short_name", "")

    for grant in CLASS_FEATURE_SPELL_GRANTS:
        if grant["class_name"] == class_name and level >= grant["level"]:
            records.append(spell_grant_record(character, grant, source_type="class_feature"))

    for grant in SUBCLASS_FEATURE_SPELL_GRANTS:
        if (
            grant["class_name"] == class_name
            and grant["subclass_short_name"] == subclass_short_name
            and level >= grant["level"]
        ):
            records.append(spell_grant_record(character, grant, source_type="subclass_feature", subclass_data=subclass_data))

    return records


def spell_grant_record(character, grant, source_type, subclass_data=None):
    casting_rules = dict(grant.get("casting_rules", {}))
    free_casts_from = grant.get("free_casts_from", {})
    if free_casts_from:
        ability = free_casts_from.get("ability", "")
        minimum = int(free_casts_from.get("minimum", 0) or 0)
        casting_rules["free_casts"] = max(
            minimum,
            int(character.get("ability_modifiers", {}).get(ability, 0) or 0),
        )
    source = {
        "type": source_type,
        "class_name": character.get("class", grant.get("class_name", "")),
        "feature_name": grant["feature_name"],
        "source_name": grant["feature_name"],
        "level": grant["level"],
    }
    if subclass_data:
        source.update({
            "subclass_id": subclass_data.get("id", ""),
            "subclass_name": subclass_data.get("name", ""),
        })
    return {
        "grant_id": grant["grant_id"],
        "spell_id": slug_spell_id(grant["spell"]),
        "name": grant["spell"],
        "source": source,
        "spellcasting_ability": grant["spellcasting_ability"],
        "grant_type": "feature_spell_grant",
        "always_prepared": grant.get("always_prepared", True),
        "counts_against_limit": grant.get("counts_against_limit", False),
        "casting_rules": casting_rules,
    }


def slug_spell_id(spell_name):
    return "".join(char.lower() if char.isalnum() else "_" for char in str(spell_name)).strip("_") + "_xphb"
