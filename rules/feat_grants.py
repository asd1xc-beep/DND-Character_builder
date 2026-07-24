FEAT_GRANTS = {
    "Chef": {
        "tool_proficiencies": ["Cook's Utensils"],
    },
    "Heavily Armored": {
        "armor_proficiencies": ["Heavy Armor"],
    },
    "Lightly Armored": {
        "armor_proficiencies": ["Light Armor", "Shields"],
    },
    "Martial Weapon Training": {
        "weapon_proficiencies": ["Martial Weapons"],
    },
    "Moderately Armored": {
        "armor_proficiencies": ["Medium Armor"],
    },
    "Poisoner": {
        "tool_proficiencies": ["Poisoner's Kit"],
    },
    "Telekinetic": {
        "spell_grants": ["Mage Hand"],
    },
    "Telepathic": {
        "spell_grants": ["Detect Thoughts"],
    },
}


def feat_grants_for_character(character, known_skill_proficiencies=None):
    grants = {
        "armor_proficiencies": [],
        "weapon_proficiencies": [],
        "tool_proficiencies": [],
        "skill_proficiencies": [],
        "expertise": [],
        "saving_throw_proficiencies": [],
        "spell_grants": [],
    }
    known_skills = merge_unique(known_skill_proficiencies or character.get("skill_proficiencies", []))
    for feat in character.get("general_feats", []) or []:
        feat_name = feat.get("name") if isinstance(feat, dict) else feat
        for key, values in FEAT_GRANTS.get(feat_name, {}).items():
            grants[key] = merge_unique(grants.get(key, []), values)
        choices = feat.get("choices", {}) if isinstance(feat, dict) else {}
        if feat_name == "Skill Expert":
            grants["skill_proficiencies"] = merge_unique(
                grants["skill_proficiencies"],
                [choices.get("skill_proficiency", "")],
            )
            known_skills = merge_unique(known_skills, [choices.get("skill_proficiency", "")])
            grants["expertise"] = merge_unique(
                grants["expertise"],
                [choices.get("expertise", "")],
            )
        if feat_name in {"Keen Mind", "Observant"} and choices.get("skill"):
            if choices["skill"] in known_skills:
                grants["expertise"] = merge_unique(grants["expertise"], [choices["skill"]])
            else:
                grants["skill_proficiencies"] = merge_unique(grants["skill_proficiencies"], [choices["skill"]])
                known_skills = merge_unique(known_skills, [choices["skill"]])
        if feat_name == "Resilient" and choices.get("ability"):
            grants["saving_throw_proficiencies"] = merge_unique(
                grants["saving_throw_proficiencies"],
                [choices["ability"]],
            )
        if feat_name == "Fey-Touched":
            grants["spell_grants"] = merge_unique(
                grants["spell_grants"],
                ["Misty Step", choices.get("spell", "")],
            )
        if feat_name == "Shadow-Touched":
            grants["spell_grants"] = merge_unique(
                grants["spell_grants"],
                ["Invisibility", choices.get("spell", "")],
            )
        if feat_name == "Ritual Caster":
            grants["spell_grants"] = merge_unique(
                grants["spell_grants"],
                choices.get("spells", []),
            )
        if feat_name == "Boon of Skill":
            grants["skill_proficiencies"] = merge_unique(
                grants["skill_proficiencies"],
                all_skill_names(),
            )
            grants["expertise"] = merge_unique(
                grants["expertise"],
                [choices.get("expertise", "")],
            )
    return grants


def feat_sheet_resources(character):
    resources = {}
    proficiency = int(character.get("proficiency_bonus", 2) or 2)
    strength = int(character.get("ability_modifiers", {}).get("Strength", 0) or 0)
    if has_general_feat(character, "Great Weapon Master"):
        resources["great_weapon_master_damage_bonus"] = proficiency
    if has_general_feat(character, "Shield Master"):
        resources["shield_master_bash_dc"] = 8 + proficiency + strength
        resources["shield_master_bash_ability"] = "Strength"
    if has_general_feat(character, "Skulker"):
        resources["blindsight_range"] = 10
        resources["blindsight_source"] = "Skulker"
    return resources


def feat_speed_bonus(character):
    bonus = 0
    if has_general_feat(character, "Speedy"):
        bonus += 10
    if has_general_feat(character, "Boon of Speed"):
        bonus += 30
    return bonus


def medium_armor_dexterity_cap(character, dexterity_score):
    if has_general_feat(character, "Medium Armor Master") and int(dexterity_score or 0) >= 16:
        return 3
    return 2


def feat_spell_grant_records(character):
    records = []
    for feat in character.get("general_feats", []) or []:
        if not isinstance(feat, dict):
            continue
        feat_name = feat.get("name", "")
        choices = feat.get("choices", {})
        ability = choices.get("ability", "")
        source = {
            "type": "feat",
            "instance_id": feat.get("instance_id", ""),
            "feat_id": feat.get("feat_id", ""),
            "source_name": feat_name,
        }
        if feat_name == "Telekinetic":
            records.append(spell_grant_record("Mage Hand", source, ability, "feat_cantrip"))
        if feat_name == "Telepathic":
            records.append(spell_grant_record(
                "Detect Thoughts",
                source,
                ability,
                "feat_spell",
                always_prepared=True,
                casting_rules={"free_casts": 1, "recharge": "long_rest", "can_use_spell_slots": True},
            ))
        if feat_name == "Fey-Touched":
            records.append(spell_grant_record(
                "Misty Step",
                source,
                ability,
                "feat_spell",
                always_prepared=True,
                casting_rules={"free_casts": 1, "recharge": "long_rest", "can_use_spell_slots": True},
            ))
            if choices.get("spell"):
                records.append(spell_grant_record(
                    choices["spell"],
                    source,
                    ability,
                    "feat_spell",
                    always_prepared=True,
                    casting_rules={"free_casts": 1, "recharge": "long_rest", "can_use_spell_slots": True},
                ))
        if feat_name == "Shadow-Touched":
            records.append(spell_grant_record(
                "Invisibility",
                source,
                ability,
                "feat_spell",
                always_prepared=True,
                casting_rules={"free_casts": 1, "recharge": "long_rest", "can_use_spell_slots": True},
            ))
            if choices.get("spell"):
                records.append(spell_grant_record(
                    choices["spell"],
                    source,
                    ability,
                    "feat_spell",
                    always_prepared=True,
                    casting_rules={"free_casts": 1, "recharge": "long_rest", "can_use_spell_slots": True},
                ))
        if feat_name == "Ritual Caster":
            for spell in choices.get("spells", []):
                records.append(spell_grant_record(
                    spell,
                    source,
                    ability,
                    "feat_ritual",
                    casting_rules={"ritual_only": True},
                ))
    return records


def spell_grant_record(name, source, ability, grant_type, always_prepared=False, casting_rules=None):
    return {
        "name": name,
        "source": source,
        "spellcasting_ability": ability,
        "grant_type": grant_type,
        "always_prepared": always_prepared,
        "counts_against_limit": False,
        "casting_rules": casting_rules or {},
    }


def has_general_feat(character, feat_name):
    for feat in character.get("general_feats", []) or []:
        name = feat.get("name") if isinstance(feat, dict) else feat
        if name == feat_name:
            return True
    return False


def feat_grants_are_supported(feat):
    return feat.get("name", "") in FEAT_GRANTS


def general_feat_names(character):
    names = []
    for entry in character.get("general_feats", []) or []:
        name = entry.get("name") if isinstance(entry, dict) else entry
        if name and name not in names:
            names.append(name)
    return names


def merge_unique(*lists):
    merged = []
    for items in lists:
        for item in items or []:
            if item and item not in merged:
                merged.append(item)
    return merged


def all_skill_names():
    return [
        "Acrobatics",
        "Animal Handling",
        "Arcana",
        "Athletics",
        "Deception",
        "History",
        "Insight",
        "Intimidation",
        "Investigation",
        "Medicine",
        "Nature",
        "Perception",
        "Performance",
        "Persuasion",
        "Religion",
        "Sleight of Hand",
        "Stealth",
        "Survival",
    ]
