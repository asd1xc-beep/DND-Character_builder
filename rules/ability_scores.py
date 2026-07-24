def ability_modifier(score):
    return (int(score) - 10) // 2


def calculate_ability_modifiers(ability_scores):
    return {
        ability: ability_modifier(score)
        for ability, score in ability_scores.items()
    }


def format_modifier(value):
    return f"{value:+d}"
