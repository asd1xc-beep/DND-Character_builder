from models.character import ABILITIES
from rules.leveling import effective_spellcasting
from rules.proficiencies import proficiency_bonus_for_level
from rules.weapon_mastery import eligible_weapon_mastery_names


ACTIVE_PLAY_FEATS = {
    "Charger": "Charge movement and once-per-turn attack effects are descriptive.",
    "Defensive Duelist": "Reaction timing is descriptive; temporary AC is not applied to the standing Armor Class.",
    "Dual Wielder": "Bonus-action attack and drawing rules are descriptive.",
    "Durable": "Death save and Hit Point Dice spending workflow is descriptive.",
    "Great Weapon Master": "Critical Hit and Bonus Action attack triggers are descriptive.",
    "Heavy Armor Master": "Damage reduction is descriptive because it applies when hit, not as a standing sheet value.",
    "Inspiring Leader": "Temporary Hit Point distribution is descriptive because it is granted after a rest performance.",
    "Mage Slayer": "Concentration and saving throw trigger automation is descriptive.",
    "Mounted Combatant": "Mounted combat triggers are descriptive.",
    "Polearm Master": "Bonus Action and Reaction attack timing is descriptive.",
    "Sentinel": "Opportunity Attack triggers and turn-specific Speed reduction are descriptive.",
    "Sharpshooter": "Attack-roll cover and range exceptions are descriptive.",
    "Shield Master": "Shield Bash use timing and Interpose Shield reaction timing are descriptive.",
    "Skulker": "Combat Hide advantage and hidden attack reveal timing are descriptive.",
}

DAMAGE_TYPE_OPTIONS = ["Acid", "Cold", "Fire", "Lightning", "Thunder"]
EPIC_RESISTANCE_DAMAGE_TYPES = [
    "Acid",
    "Cold",
    "Fire",
    "Lightning",
    "Necrotic",
    "Poison",
    "Psychic",
    "Radiant",
    "Thunder",
]
EPIC_BOON_FEATS = {
    "Boon of Combat Prowess",
    "Boon of Dimensional Travel",
    "Boon of Energy Resistance",
    "Boon of Fate",
    "Boon of Fortitude",
    "Boon of Irresistible Offense",
    "Boon of Recovery",
    "Boon of Skill",
    "Boon of Speed",
    "Boon of Spell Recall",
    "Boon of the Night Spirit",
    "Boon of Truesight",
}
SHEET_VALUE_FEATS = {
    "Elemental Adept",
    "Fey-Touched",
    "Keen Mind",
    "Observant",
    "Resilient",
    "Ritual Caster",
    "Shadow-Touched",
    "Skill Expert",
    "Telekinetic",
    "Telepathic",
    "Weapon Master",
    "Medium Armor Master",
    "Speedy",
    "Great Weapon Master",
    "Shield Master",
    "Skulker",
    "Boon of Energy Resistance",
    "Boon of Fortitude",
    "Boon of Skill",
    "Boon of Speed",
    "Boon of Truesight",
}

CHOICE_SUPPORTED_FEATS = SHEET_VALUE_FEATS | {
    "Boon of Energy Resistance",
}

PARTIAL_EPIC_BOON_NOTES = {
    "Boon of Fate": "Improve Fate is tracked as descriptive text; its initiative/short-rest recovery timing is not modeled as a resource pool.",
    "Boon of Recovery": "Last Stand and the ten-d10 recovery pool are descriptive; the recovery pool is not yet tracked as spendable dice.",
    "Boon of the Night Spirit": "Dim-light invisibility and conditional resistance are descriptive because they depend on current lighting.",
}

PERMANENT_GRANT_FEATS = SHEET_VALUE_FEATS | {
    "Actor",
    "Athlete",
    "Chef",
    "Crossbow Expert",
    "Crusher",
    "Fey-Touched",
    "Grappler",
    "Heavily Armored",
    "Lightly Armored",
    "Mage Slayer",
    "Martial Weapon Training",
    "Moderately Armored",
    "Piercer",
    "Poisoner",
    "Resilient",
    "Ritual Caster",
    "Shadow-Touched",
    "Slasher",
    "Spell Sniper",
    "War Caster",
    *EPIC_BOON_FEATS,
}
RITUAL_CASTER_SPELLS = [
    "Alarm",
    "Comprehend Languages",
    "Detect Magic",
    "Detect Poison and Disease",
    "Find Familiar",
    "Identify",
    "Illusory Script",
    "Purify Food and Drink",
    "Speak with Animals",
    "Tenser's Floating Disk",
    "Unseen Servant",
]


def feat_by_id(feats, feat_id):
    return next((feat for feat in feats or [] if feat.get("id") == feat_id), {})


def character_feat_names(character):
    names = []
    for source in (
        character.get("origin_feats", []),
        character.get("background_options", {}).get("origin_feats", []),
        character.get("species_options", {}).get("origin_feats", []),
        character.get("general_feats", []),
    ):
        for feat in source or []:
            name = feat.get("name") if isinstance(feat, dict) else feat
            if name and name not in names:
                names.append(name)
    return names


def character_has_spellcasting(character, class_data=None):
    if character.get("spellcasting_ability"):
        return True
    spellcasting = effective_spellcasting(
        class_data or {},
        character.get("subclass", ""),
        character.get("level", 1),
    )
    return bool(spellcasting)


def feat_is_eligible(feat, character, class_data=None):
    if not feat:
        return False
    if not feat.get("repeatable") and feat.get("name") in character_feat_names(character):
        return False
    groups = feat.get("prerequisites", {}).get("any", [])
    return any(prerequisite_group_met(character, class_data, group) for group in groups)


def eligible_feats(feats, character, class_data=None):
    return [
        feat
        for feat in feats or []
        if feat_is_eligible(feat, character, class_data)
    ]


def feat_support_status(feat):
    name = feat.get("name", "")
    notes = []
    if feat.get("required_choices") and name not in CHOICE_SUPPORTED_FEATS:
        notes.append("Requires choices that are not automated yet.")
    if name not in SHEET_VALUE_FEATS:
        notes.extend(feat.get("unsupported_choices", []))
    if name in ACTIVE_PLAY_FEATS:
        notes.append(ACTIVE_PLAY_FEATS[name])
    if name not in PERMANENT_GRANT_FEATS and name not in ACTIVE_PLAY_FEATS:
        notes.append("Permanent sheet effects have not been audited yet.")

    if name in PARTIAL_EPIC_BOON_NOTES:
        notes.append(PARTIAL_EPIC_BOON_NOTES[name])

    selection = "supported" if not feat.get("required_choices") or name in CHOICE_SUPPORTED_FEATS else "unsupported"
    permanent = "supported" if name in PERMANENT_GRANT_FEATS else "partial"
    sheet_calculation = "supported" if name in SHEET_VALUE_FEATS or name in PERMANENT_GRANT_FEATS else "partial"
    if name in ACTIVE_PLAY_FEATS and name not in SHEET_VALUE_FEATS:
        sheet_calculation = "description_only"
    if name in PARTIAL_EPIC_BOON_NOTES:
        permanent = "partial"
        sheet_calculation = "description_only" if name == "Boon of the Night Spirit" else "partial"
    return {
        "selection": selection,
        "permanent_grants": permanent,
        "sheet_calculation": sheet_calculation,
        "active_play": "description_only" if name in ACTIVE_PLAY_FEATS else "supported",
        "grants": permanent,
        "prerequisites": "supported",
        "notes": notes,
    }


def feat_is_supported_for_selection(feat):
    support = feat_support_status(feat)
    return support["selection"] == "supported" and support["permanent_grants"] != "unsupported"


def feat_choice_schema(feat, character=None, data=None):
    name = feat.get("name", "")
    character = character or {}
    data = data or {}
    if name == "Elemental Adept":
        return [{
            "id": "damage_type",
            "type": "single",
            "label": "Damage type",
            "options": available_elemental_adept_damage_types(character),
        }]
    if name == "Skill Expert":
        skill_names = list(data.get("rules", {}).get("skills", {}).keys())
        expertise_options = [
            skill
            for skill in character.get("skill_proficiencies", [])
            if skill not in character.get("expertise", [])
        ]
        return [
            {
                "id": "skill_proficiency",
                "type": "single",
                "label": "Skill proficiency",
                "options": [skill for skill in skill_names if skill not in character.get("skill_proficiencies", [])] or skill_names,
            },
            {
                "id": "expertise",
                "type": "single",
                "label": "Expertise",
                "options": expertise_options,
            },
        ]
    if name == "Keen Mind":
        return [{
            "id": "skill",
            "type": "single",
            "label": "Skill",
            "options": ["Arcana", "History", "Investigation", "Nature", "Religion"],
        }]
    if name == "Observant":
        return [{
            "id": "skill",
            "type": "single",
            "label": "Skill",
            "options": ["Insight", "Investigation", "Perception"],
        }]
    if name == "Fey-Touched":
        return [{
            "id": "spell",
            "type": "single",
            "label": "Level 1 Divination or Enchantment spell",
            "options": spell_options(data.get("spells", []), levels={1}, schools={"D", "E"}),
        }]
    if name == "Shadow-Touched":
        return [{
            "id": "spell",
            "type": "single",
            "label": "Level 1 Illusion or Necromancy spell",
            "options": spell_options(data.get("spells", []), levels={1}, schools={"I", "N"}),
        }]
    if name == "Ritual Caster":
        selected_spells = ritual_caster_spells(character)
        choose = max(1, proficiency_bonus_for_level(character.get("level", 1)) - len(selected_spells))
        return [{
            "id": "spells",
            "type": "multi",
            "label": "Level 1 ritual spells",
            "choose": choose,
            "options": [
                spell
                for spell in ritual_spell_options(data.get("spells", []))
                if spell not in selected_spells
            ],
        }]
    if name == "Weapon Master":
        return [{
            "id": "weapon_mastery",
            "type": "single",
            "label": "Weapon Mastery",
            "options": [
                weapon
                for weapon in eligible_weapon_mastery_names(character, data.get("weapons", []))
                if weapon not in character.get("weapon_masteries", [])
            ],
        }]
    if name == "Boon of Skill":
        expertise_options = [
            skill
            for skill in data.get("rules", {}).get("skills", {}).keys()
            if skill not in character.get("expertise", [])
        ]
        return [{
            "id": "expertise",
            "type": "single",
            "label": "Expertise",
            "options": expertise_options,
        }]
    if name == "Boon of Energy Resistance":
        return [{
            "id": "damage_types",
            "type": "multi",
            "label": "Damage resistances",
            "choose": 2,
            "options": EPIC_RESISTANCE_DAMAGE_TYPES,
        }]
    return []


def spell_options(spells, levels=None, schools=None):
    return sorted({
        spell.get("name", "")
        for spell in spells or []
        if spell.get("name")
        and (not levels or spell.get("level") in levels)
        and (not schools or spell.get("school_code") in schools)
    })


def ritual_spell_options(spells):
    available = {spell.get("name", "") for spell in spells or []}
    return [spell for spell in RITUAL_CASTER_SPELLS if spell in available]


def ritual_caster_spells(character):
    spells = []
    for feat in character.get("general_feats", []) or []:
        if not isinstance(feat, dict) or feat.get("name") != "Ritual Caster":
            continue
        choices = feat.get("choices", {})
        spells.extend(choices.get("spells", []))
    return [spell for spell in spells if spell]


def feat_ability_choice_is_valid(feat, character, ability_choice):
    if feat.get("name") == "Resilient":
        return ability_choice and ability_choice not in character.get("saving_throw_proficiencies", [])
    return True


def available_elemental_adept_damage_types(character):
    used = {
        entry.get("choices", {}).get("damage_type")
        for entry in character.get("general_feats", [])
        if isinstance(entry, dict) and entry.get("name") == "Elemental Adept"
    }
    return [damage_type for damage_type in DAMAGE_TYPE_OPTIONS if damage_type not in used]


def feat_extra_choices_are_valid(feat, character, feat_choices, data=None):
    schema = feat_choice_schema(feat, character, data)
    if feat.get("name") == "Skill Expert":
        selected_skill = (feat_choices or {}).get("skill_proficiency", "")
        skill_options = set(next((field.get("options", []) for field in schema if field["id"] == "skill_proficiency"), []))
        if not selected_skill or selected_skill not in skill_options:
            return False
        expertise = (feat_choices or {}).get("expertise", "")
        expertise_options = set(next((field.get("options", []) for field in schema if field["id"] == "expertise"), []))
        expertise_options.add(selected_skill)
        return expertise in expertise_options
    for field in schema:
        value = (feat_choices or {}).get(field["id"], "")
        options = field.get("options", [])
        if field.get("type") == "multi":
            choose = int(field.get("choose", 0) or 0)
            if (
                not isinstance(value, list)
                or len(value) != choose
                or len(set(value)) != len(value)
                or any(item not in options for item in value)
            ):
                return False
        elif not value or value not in options:
            return False
    return True


def general_feat_names(character):
    return feat_names_from_entries(character.get("general_feats", []))


def feat_names_from_entries(entries):
    names = []
    for entry in entries or []:
        name = entry.get("name") if isinstance(entry, dict) else entry
        if name and name not in names:
            names.append(name)
    return names


def prerequisite_group_met(character, class_data, group):
    if character.get("level", 1) < int(group.get("minimum_level", 0) or 0):
        return False
    if not ability_prerequisites_met(character, group.get("ability_scores", [])):
        return False
    if group.get("spellcasting") and not character_has_spellcasting(character, class_data):
        return False
    if not proficiencies_met(character, group.get("proficiencies", [])):
        return False
    if not features_met(character, group.get("features", [])):
        return False
    return not group.get("other")


def ability_prerequisites_met(character, ability_options):
    if not ability_options:
        return True
    scores = character.get("ability_scores", {})
    for option in ability_options:
        if all(int(scores.get(ability, 0)) >= int(score) for ability, score in option.items()):
            return True
    return False


def proficiencies_met(character, proficiencies):
    for proficiency in proficiencies or []:
        category = proficiency.get("type")
        value = proficiency.get("value")
        if value not in character.get(f"{category}_proficiencies", []):
            return False
    return True


def features_met(character, features):
    owned = set(character.get("features", [])) | set(character_feat_names(character))
    return all(feature in owned for feature in features or [])


def feat_ability_options(feat):
    ability_increase = feat.get("ability_increase", {})
    if ability_increase.get("mode") == "multi_mode":
        return ability_increase.get("modes", [])
    return [ability_increase] if ability_increase else []


def valid_ability_name(ability):
    return ability in ABILITIES
