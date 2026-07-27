DEFAULT_ABILITY_SCORE_MAXIMUM = 20

# Class features that raise the rule-supported ceiling for specific abilities.
# Keep this as the single source of truth so the character sheet's manual
# entry cap and the level-up ASI validation never drift apart.
CLASS_ABILITY_SCORE_MAXIMUM_FEATURES = {
    "Barbarian": {"level": 20, "abilities": ["Strength", "Constitution"], "maximum": 25},
    "Monk": {"level": 20, "abilities": ["Dexterity", "Wisdom"], "maximum": 25},
}


def ability_score_maximums_for_class(class_name, level):
    maximums = {}
    rule = CLASS_ABILITY_SCORE_MAXIMUM_FEATURES.get(class_name)
    if rule and int(level or 0) >= int(rule["level"]):
        for ability in rule["abilities"]:
            maximums[ability] = int(rule["maximum"])
    return maximums


def ability_modifier(score):
    return (int(score) - 10) // 2


def calculate_ability_modifiers(ability_scores):
    return {
        ability: ability_modifier(score)
        for ability, score in ability_scores.items()
    }


def format_modifier(value):
    return f"{value:+d}"
