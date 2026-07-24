SUPPORTED_LEVELS = list(range(1, 21))


def normalize_level(level):
    try:
        return int(level)
    except (TypeError, ValueError):
        return 1


def is_supported_level(level):
    return normalize_level(level) in SUPPORTED_LEVELS


def supported_levels_message():
    return f"Only Levels {min(SUPPORTED_LEVELS)}-{max(SUPPORTED_LEVELS)} are supported right now."


def validate_supported_level(level):
    if not is_supported_level(level):
        raise ValueError(f"Level {level} is not supported yet")
    return normalize_level(level)


def supported_level(level):
    try:
        parsed = int(level)
    except (TypeError, ValueError):
        return 1
    return min(max(parsed, min(SUPPORTED_LEVELS)), max(SUPPORTED_LEVELS))


def class_features_by_level(class_data):
    features = class_data.get("level_features") or {}
    if features:
        return {int(level): list(names) for level, names in features.items()}
    return {1: list(class_data.get("level_1_features", []))}


def class_features_at_level(class_data, level):
    return class_features_by_level(class_data).get(int(level), [])


def class_features_up_to_level(class_data, level):
    features_by_level = class_features_by_level(class_data)
    features = []
    for current_level in range(1, int(level) + 1):
        for feature in features_by_level.get(current_level, []):
            if feature and feature not in features:
                features.append(feature)
    return features


def selected_subclass_data(class_data, subclass_name):
    for subclass in class_data.get("subclasses", []):
        if subclass_name in {subclass.get("name"), subclass.get("short_name")}:
            return subclass
    return {}


def selected_subclass_options(class_data, subclass_name):
    return selected_subclass_data(class_data, subclass_name).get("subclass_options", {})


def effective_spellcasting(class_data, subclass_name="", level=1):
    class_spellcasting = class_data.get("spellcasting")
    if class_spellcasting:
        spellcasting = dict(class_spellcasting)
        cantrips_known = get_cantrip_limit(class_data, level)
        prepared_spells = get_prepared_spell_limit(class_data, level)
        known_spells = get_known_spell_limit(class_data, level)
        spell_slots = get_spell_slots(class_data, level)
        if cantrips_known:
            spellcasting["cantrips_known"] = cantrips_known
        if class_data.get("name") == "Wizard" and known_spells:
            spellcasting["spellbook_spells"] = known_spells
            spellcasting.pop("known_spells", None)
            if prepared_spells:
                spellcasting["prepared_spells"] = prepared_spells
        elif prepared_spells:
            spellcasting["prepared_spells"] = prepared_spells
            spellcasting.pop("known_spells", None)
        elif known_spells:
            spellcasting["known_spells"] = known_spells
            spellcasting.pop("prepared_spells", None)
        if spell_slots:
            spellcasting["spell_slots"] = spell_slots
        return spellcasting
    subclass_data = selected_subclass_data(class_data, subclass_name)
    return subclass_spellcasting_at_level(subclass_data, level)


def subclass_spellcasting_at_level(subclass_data, level):
    progression = subclass_data.get("spellcasting_progression", {}) if subclass_data else {}
    if progression:
        entry = progression.get(str(int(level)))
        if entry:
            return dict(entry)
        eligible_levels = [
            int(progression_level)
            for progression_level in progression
            if int(progression_level) <= int(level)
        ]
        if eligible_levels:
            return dict(progression[str(max(eligible_levels))])
    spellcasting = subclass_data.get("spellcasting") if subclass_data else None
    return dict(spellcasting) if spellcasting else None


def get_active_subclass_grants(subclass_data, character_level):
    if not subclass_data:
        return empty_subclass_grants()
    grants_by_level = subclass_data.get("grants_by_level", {})
    if not grants_by_level:
        return {
            "always_prepared_spells": list(subclass_data.get("always_prepared_spells", [])),
            "always_known_spells": list(subclass_data.get("always_known_spells", [])),
            "granted_cantrips": list(subclass_data.get("granted_cantrips", [])),
            "resources": dict(subclass_data.get("resources", {})),
            "spell_grants": [],
        }

    active = empty_subclass_grants()
    for level in sorted(int(level) for level in grants_by_level if int(level) <= int(character_level)):
        grant = grants_by_level.get(str(level), {})
        active["always_prepared_spells"] = merge_unique(
            active["always_prepared_spells"],
            grant.get("always_prepared_spells", []),
        )
        active["always_known_spells"] = merge_unique(
            active["always_known_spells"],
            grant.get("always_known_spells", []),
        )
        active["granted_cantrips"] = merge_unique(
            active["granted_cantrips"],
            grant.get("granted_cantrips", []),
        )
        active["spell_grants"] = merge_unique_records(
            active["spell_grants"],
            grant.get("spell_grants", []),
        )
        active["resources"].update(grant.get("resources", {}))
    return active


def empty_subclass_grants():
    return {
        "always_prepared_spells": [],
        "always_known_spells": [],
        "granted_cantrips": [],
        "resources": {},
        "spell_grants": [],
    }


def merge_unique(*lists):
    merged = []
    for items in lists:
        for item in items or []:
            if item and item not in merged:
                merged.append(item)
    return merged


def merge_unique_records(*lists):
    merged = []
    seen = set()
    for items in lists:
        for item in items or []:
            key = (
                item.get("name"),
                item.get("level_gained"),
                item.get("grant_type"),
                item.get("source", {}).get("subclass_id"),
            )
            if item and key not in seen:
                merged.append(dict(item))
                seen.add(key)
    return merged


def subclass_features_by_level(subclass_data):
    features = subclass_data.get("level_features") or {}
    return {int(level): list(names) for level, names in features.items()}


def subclass_features_at_level(class_data, subclass_name, level):
    subclass_data = selected_subclass_data(class_data, subclass_name)
    return subclass_features_by_level(subclass_data).get(int(level), [])


def subclass_features_up_to_level(class_data, subclass_name, level):
    subclass_data = selected_subclass_data(class_data, subclass_name)
    features_by_level = subclass_features_by_level(subclass_data)
    features = []
    for current_level in range(1, int(level) + 1):
        for feature in features_by_level.get(current_level, []):
            if feature and feature not in features:
                features.append(feature)
    return features


def class_progression_by_level(class_data):
    progression = class_data.get("progression") or {}
    if progression:
        by_level = {}
        for level, entry in progression.items():
            if isinstance(entry, dict):
                by_level[int(level)] = list(entry.get("features", []))
            else:
                by_level[int(level)] = list(entry)
        return by_level
    return {
        level: [
            {
                "id": f"{slug(class_data.get('name', 'class'))}_{level}_{slug(feature)}",
                "type": "automatic_feature",
                "name": feature,
                "source": class_data.get("name", ""),
                "level": level,
            }
            for feature in features
        ]
        for level, features in class_features_by_level(class_data).items()
    }


def class_progression_at_level(class_data, level):
    return class_progression_by_level(class_data).get(int(level), [])


def get_class_progression(class_data, level):
    progression = class_data.get("progression") or {}
    entry = progression.get(str(int(level)), {})
    if isinstance(entry, dict):
        return entry
    return {"features": list(entry or [])}


def get_class_resources(class_data, level):
    progression = get_class_progression(class_data, level)
    resources = dict(class_data.get("level_1_rules", {}))
    resources.update(progression.get("resources", {}))
    if progression.get("spell_slots"):
        resources["spell_slots"] = progression.get("spell_slots", {})
    return resources


def get_spell_slots(class_data, level):
    progression = get_class_progression(class_data, level)
    slots = progression.get("spell_slots", {})
    if slots:
        return slots
    resources = get_class_resources(class_data, level)
    return resources.get("spell_slots", {})


def get_available_spell_levels(class_data_or_slots, level=None, casting_type=None):
    if level is None:
        spell_slots = class_data_or_slots or {}
    else:
        spell_slots = get_spell_slots(class_data_or_slots, level)
        casting_type = casting_type or get_casting_type(class_data_or_slots, level)
    return available_spell_levels_from_slots(spell_slots, casting_type or "standard")


def available_spell_levels_from_slots(spell_slots, casting_type="standard"):
    active_levels = sorted(
        int(spell_level)
        for spell_level, slots in (spell_slots or {}).items()
        if int(slots or 0)
    )
    if casting_type == "pact" and active_levels:
        return list(range(1, max(active_levels) + 1))
    return active_levels


def get_casting_type(class_data, level=None):
    resources = get_class_resources(class_data, level or 1)
    if resources.get("pact_slot_level"):
        return "pact"
    spellcasting = class_data.get("spellcasting") or {}
    return spellcasting.get("type", "standard")


def get_prepared_spell_limit(class_data, level):
    return int(get_class_progression(class_data, level).get("prepared_spells", 0) or 0)


def get_known_spell_limit(class_data, level):
    return int(get_class_progression(class_data, level).get("known_spells", 0) or 0)


def get_cantrip_limit(class_data, level):
    return int(get_class_progression(class_data, level).get("cantrips_known", 0) or 0)


def slug(value):
    return "".join(char.lower() if char.isalnum() else "_" for char in str(value)).strip("_")
