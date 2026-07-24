def calculate_level_one_hit_points(hit_die, constitution_modifier):
    return max(1, int(hit_die) + int(constitution_modifier))


def fixed_hit_die_gain(hit_die):
    return (int(hit_die) // 2) + 1


def fixed_hit_points_per_level(hit_die, constitution_modifier):
    return max(1, fixed_hit_die_gain(hit_die) + int(constitution_modifier))


def calculate_hit_points(hit_die, constitution_modifier, level):
    if int(level) <= 1:
        return calculate_level_one_hit_points(hit_die, constitution_modifier)
    return calculate_level_one_hit_points(hit_die, constitution_modifier) + (
        (int(level) - 1) * fixed_hit_points_per_level(hit_die, constitution_modifier)
    )


def ensure_hp_history(character, class_name, hit_die):
    level = int(character.get("level", 1) or 1)
    history = list(character.get("hp_history", []))
    existing_levels = {
        int(entry.get("character_level", 0))
        for entry in history
        if entry.get("class_name") == class_name
    }
    if 1 not in existing_levels:
        history.append({
            "character_level": 1,
            "class_name": class_name,
            "method": "maximum",
            "base_gain": int(hit_die),
        })
        existing_levels.add(1)
    for character_level in range(2, level + 1):
        if character_level not in existing_levels:
            history.append({
                "character_level": character_level,
                "class_name": class_name,
                "method": "fixed",
                "base_gain": fixed_hit_die_gain(hit_die),
            })
            existing_levels.add(character_level)
    character["hp_history"] = sorted(history, key=lambda entry: int(entry.get("character_level", 0)))
    return character["hp_history"]


def calculate_max_hit_points(hp_history, constitution_modifier, origin_feats=None, species_traits=None):
    history = hp_history or []
    level = len(history)
    base_hp = sum(int(entry.get("base_gain", 0) or 0) for entry in history)
    maximum = base_hp + (int(constitution_modifier) * level)
    if "Tough" in set(origin_feats or []):
        maximum += 2 * level
    if "Dwarven Toughness" in set(species_traits or []):
        maximum += level
    return max(1, maximum) if level else 0


def hit_die_label(hit_die):
    return f"d{hit_die}" if hit_die else ""
