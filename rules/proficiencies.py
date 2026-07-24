def proficiency_bonus_for_level(level):
    level = int(level)
    if level >= 17:
        return 6
    if level >= 13:
        return 5
    if level >= 9:
        return 4
    if level >= 5:
        return 3
    return 2


def calculate_saving_throw_bonuses(ability_modifiers, saving_throw_proficiencies, proficiency_bonus):
    return {
        ability: modifier + (proficiency_bonus if ability in saving_throw_proficiencies else 0)
        for ability, modifier in ability_modifiers.items()
    }


def calculate_skill_bonuses(skill_to_ability, ability_modifiers, skill_proficiencies, expertise, proficiency_bonus):
    bonuses = {}
    for skill, ability in skill_to_ability.items():
        bonus = ability_modifiers.get(ability, 0)
        if skill in skill_proficiencies:
            bonus += proficiency_bonus
        if skill in expertise:
            bonus += proficiency_bonus
        bonuses[skill] = bonus
    return bonuses


def available_class_skill_options(class_data, background_skills):
    choices = class_data.get("skill_choices", {})
    return [
        skill
        for skill in choices.get("from", [])
        if skill not in set(background_skills)
    ]
