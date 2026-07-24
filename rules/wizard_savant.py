SAVANT_SPELL_CHOICES_BY_LEVEL = {
    "3": {"choose": 2, "maximum_spell_level": 2},
    "5": {"choose": 1, "maximum_spell_level": 3},
    "7": {"choose": 1, "maximum_spell_level": 4},
    "9": {"choose": 1, "maximum_spell_level": 5},
    "11": {"choose": 1, "maximum_spell_level": 6},
    "13": {"choose": 1, "maximum_spell_level": 7},
    "15": {"choose": 1, "maximum_spell_level": 8},
    "17": {"choose": 1, "maximum_spell_level": 9},
}

SAVANT_SCHOOL_CODES = {
    "Abjurer": "A",
    "Diviner": "D",
    "Evoker": "V",
    "Illusionist": "I",
}


def savant_spell_choice_key(level):
    return "savant_spells" if int(level) == 3 else f"savant_spells_level_{int(level)}"


def savant_spell_choice_source_level(key):
    if key == "savant_spells":
        return 3
    if key.startswith("savant_spells_level_"):
        return int(key.rsplit("_", 1)[-1] or 0)
    return 0


def savant_spell_source_level(key):
    return savant_spell_choice_source_level(key)


def is_savant_spell_choice_key(key):
    return key == "savant_spells" or key.startswith("savant_spells_level_")


def savant_spell_choice_rule(subclass_options, subclass_name, level):
    by_level = subclass_options.get("savant_spell_choices_by_level", {})
    rule = by_level.get(str(int(level)))
    if not rule:
        return {}
    school = (
        rule.get("from", {}).get("school")
        or subclass_options.get("savant_spells", {}).get("from", {}).get("school")
        or SAVANT_SCHOOL_CODES.get(subclass_name, "")
    )
    maximum_spell_level = int(rule.get("maximum_spell_level", 0) or 0)
    return {
        "choose": int(rule.get("choose", 0) or 0),
        "from": {
            "levels": list(range(1, maximum_spell_level + 1)),
            "class": "Wizard",
            "school": school,
        },
        "label": rule.get("label") or f"Choose {subclass_name} Savant spell",
        "source_level": int(level),
    }


def savant_spell_choice_keys_up_to_level(level):
    return [
        savant_spell_choice_key(choice_level)
        for choice_level in sorted(int(item) for item in SAVANT_SPELL_CHOICES_BY_LEVEL)
        if choice_level <= int(level)
    ]


def selected_savant_spells(character):
    class_options = character.get("class_options", {})
    spells = []
    for key in savant_spell_choice_keys_up_to_level(character.get("level", 1)):
        value = class_options.get(key, [])
        values = value if isinstance(value, list) else [value]
        for spell in values:
            if spell and spell not in spells:
                spells.append(spell)
    return spells


def savant_spell_source_records(character):
    class_options = character.get("class_options", {})
    records = []
    for key in savant_spell_choice_keys_up_to_level(character.get("level", 1)):
        value = class_options.get(key, [])
        values = value if isinstance(value, list) else [value]
        level = savant_spell_choice_source_level(key)
        for spell in values:
            if not spell:
                continue
            records.append({
                "name": spell,
                "source": {
                    "type": "subclass_feature",
                    "subclass_name": character.get("subclass", ""),
                    "feature_name": "Savant",
                    "level": level,
                },
            })
    return records
