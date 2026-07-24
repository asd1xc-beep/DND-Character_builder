LIMITED_MARTIAL_WEAPON_NAMES = {
    "Hand Crossbow",
    "Rapier",
    "Scimitar",
    "Shortsword",
    "Whip",
}


def eligible_weapon_mastery_names(character, weapons):
    proficiencies = character.get("weapon_proficiencies", [])
    return [
        weapon.get("name", "")
        for weapon in weapons or []
        if weapon.get("mastery")
        and character_is_proficient_with_weapon(proficiencies, weapon)
    ]


def character_is_proficient_with_weapon(proficiencies, weapon):
    name = weapon.get("name", "")
    category = weapon.get("category", "")
    if name in proficiencies:
        return True
    if category == "Simple" and "Simple Weapons" in proficiencies:
        return True
    if category == "Martial" and "Martial Weapons" in proficiencies:
        return True
    if category == "Martial" and limited_martial_proficiency_applies(proficiencies, name):
        return True
    return False


def limited_martial_proficiency_applies(proficiencies, weapon_name):
    return (
        weapon_name in LIMITED_MARTIAL_WEAPON_NAMES
        and any(
            "Martial Weapons That Have" in proficiency
            or "Finesse Or Light" in proficiency
            for proficiency in proficiencies or []
        )
    )
