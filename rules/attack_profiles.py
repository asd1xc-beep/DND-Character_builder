from dataclasses import dataclass
from typing import Iterable, Mapping

from models.character import merge_unique
from rules.ability_scores import ability_modifier, format_modifier
from rules.weapon_mastery import character_is_proficient_with_weapon


DAMAGE_TYPES = {
    "A": "Acid",
    "B": "Bludgeoning",
    "C": "Cold",
    "F": "Fire",
    "L": "Lightning",
    "N": "Necrotic",
    "P": "Piercing",
    "Po": "Poison",
    "R": "Radiant",
    "S": "Slashing",
    "T": "Thunder",
    "Y": "Psychic",
}


WEAPON_RULES = {
    "Battleaxe": {"kind": "melee", "properties": {"versatile"}, "versatile_damage": "1d10"},
    "Blowgun": {"kind": "ranged", "properties": set()},
    "Club": {"kind": "melee", "properties": {"light"}},
    "Dagger": {"kind": "melee", "properties": {"finesse", "light", "thrown"}},
    "Dart": {"kind": "ranged", "properties": {"finesse", "thrown"}},
    "Flail": {"kind": "melee", "properties": set()},
    "Glaive": {"kind": "melee", "properties": {"heavy", "reach", "two_handed"}},
    "Greataxe": {"kind": "melee", "properties": {"heavy", "two_handed"}},
    "Greatclub": {"kind": "melee", "properties": {"two_handed"}},
    "Greatsword": {"kind": "melee", "properties": {"heavy", "two_handed"}},
    "Halberd": {"kind": "melee", "properties": {"heavy", "reach", "two_handed"}},
    "Hand Crossbow": {"kind": "ranged", "properties": {"light", "loading"}},
    "Handaxe": {"kind": "melee", "properties": {"light", "thrown"}},
    "Heavy Crossbow": {"kind": "ranged", "properties": {"heavy", "loading", "two_handed"}},
    "Javelin": {"kind": "melee", "properties": {"thrown"}},
    "Lance": {"kind": "melee", "properties": {"reach"}},
    "Light Crossbow": {"kind": "ranged", "properties": {"loading", "two_handed"}},
    "Light Hammer": {"kind": "melee", "properties": {"light", "thrown"}},
    "Longbow": {"kind": "ranged", "properties": {"heavy", "two_handed"}},
    "Longsword": {"kind": "melee", "properties": {"versatile"}, "versatile_damage": "1d10"},
    "Mace": {"kind": "melee", "properties": set()},
    "Maul": {"kind": "melee", "properties": {"heavy", "two_handed"}},
    "Morningstar": {"kind": "melee", "properties": set()},
    "Musket": {"kind": "ranged", "properties": {"loading", "two_handed"}},
    "Pike": {"kind": "melee", "properties": {"heavy", "reach", "two_handed"}},
    "Pistol": {"kind": "ranged", "properties": {"loading"}},
    "Psychic Blade": {"kind": "melee", "properties": {"finesse", "thrown"}},
    "Quarterstaff": {"kind": "melee", "properties": {"versatile"}, "versatile_damage": "1d8"},
    "Rapier": {"kind": "melee", "properties": {"finesse"}},
    "Scimitar": {"kind": "melee", "properties": {"finesse", "light"}},
    "Shortbow": {"kind": "ranged", "properties": {"two_handed"}},
    "Shortsword": {"kind": "melee", "properties": {"finesse", "light"}},
    "Sickle": {"kind": "melee", "properties": {"light"}},
    "Sling": {"kind": "ranged", "properties": set()},
    "Spear": {"kind": "melee", "properties": {"thrown", "versatile"}, "versatile_damage": "1d8"},
    "Staff": {"kind": "melee", "properties": {"versatile"}, "versatile_damage": "1d8"},
    "Trident": {"kind": "melee", "properties": {"thrown", "versatile"}, "versatile_damage": "1d8"},
    "War Pick": {"kind": "melee", "properties": set()},
    "Warhammer": {"kind": "melee", "properties": {"versatile"}, "versatile_damage": "1d10"},
    "Whip": {"kind": "melee", "properties": {"finesse", "reach"}},
    "Wooden Staff": {"kind": "melee", "properties": {"versatile"}, "versatile_damage": "1d8"},
}


CANTRIP_ATTACK_RULES = {
    "Acid Splash": {"mode": "save", "save_ability": "DEX", "damage_die": "d6", "damage_type": "Acid"},
    "Chill Touch": {"mode": "attack", "damage_die": "d10", "damage_type": "Necrotic"},
    "Eldritch Blast": {"mode": "attack", "damage_die": "d10", "damage_type": "Force"},
    "Fire Bolt": {"mode": "attack", "damage_die": "d10", "damage_type": "Fire"},
    "Mind Sliver": {"mode": "save", "save_ability": "INT", "damage_die": "d6", "damage_type": "Psychic"},
    "Poison Spray": {"mode": "save", "save_ability": "CON", "damage_die": "d12", "damage_type": "Poison"},
    "Produce Flame": {"mode": "attack", "damage_die": "d8", "damage_type": "Fire"},
    "Ray of Frost": {"mode": "attack", "damage_die": "d8", "damage_type": "Cold"},
    "Sacred Flame": {"mode": "save", "save_ability": "DEX", "damage_die": "d8", "damage_type": "Radiant"},
    "Shocking Grasp": {"mode": "attack", "damage_die": "d8", "damage_type": "Lightning"},
    "Sorcerous Burst": {"mode": "attack", "damage_die": "d8", "damage_type": "Variable"},
    "Starry Wisp": {"mode": "attack", "damage_die": "d8", "damage_type": "Radiant"},
    "Thorn Whip": {"mode": "attack", "damage_die": "d6", "damage_type": "Piercing"},
    "Thunderclap": {"mode": "save", "save_ability": "CON", "damage_die": "d6", "damage_type": "Thunder"},
    "Toll the Dead": {"mode": "save", "save_ability": "WIS", "damage_die": "d8", "damage_type": "Necrotic"},
    "Vicious Mockery": {"mode": "save", "save_ability": "WIS", "damage_die": "d6", "damage_type": "Psychic"},
    "Word of Radiance": {"mode": "save", "save_ability": "CON", "damage_die": "d6", "damage_type": "Radiant"},
}


@dataclass(frozen=True)
class AttackProfile:
    name: str
    attack_display: str
    damage_display: str
    kind: str

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "attack_display": self.attack_display,
            "damage_display": self.damage_display,
            "kind": self.kind,
        }


def build_attack_profiles(character: Mapping, data: Mapping | None = None) -> list[dict]:
    profiles = []
    weapon = selected_weapon_attack_profile(character, data)
    if weapon:
        profiles.append(weapon.as_dict())
    cantrip = selected_cantrip_attack_profile(character)
    if cantrip:
        profiles.append(cantrip.as_dict())
    return profiles


def weapon_attack_profile_options(character: Mapping, data: Mapping | None = None) -> list[dict]:
    weapon_lookup = _weapon_lookup(data)
    profiles = []
    for name in merge_unique(character.get("equipment", [])):
        profile = weapon_attack_profile(character, weapon_lookup.get(name))
        if profile:
            profiles.append(profile.as_dict())
    return profiles


def cantrip_attack_profile_options(character: Mapping) -> list[dict]:
    profiles = []
    for name in merge_unique(character.get("spells", {}).get("cantrips", []), spell_grant_names(character)):
        profile = cantrip_attack_profile(character, name)
        if profile:
            profiles.append(profile.as_dict())
    return profiles


def selected_weapon_attack_profile(character: Mapping, data: Mapping | None = None) -> AttackProfile | None:
    profiles = weapon_attack_profile_options(character, data)
    return _selected_profile(
        profiles,
        character.get("presentation_preferences", {}).get("primary_weapon", ""),
        "weapon",
    )


def selected_cantrip_attack_profile(character: Mapping) -> AttackProfile | None:
    profiles = cantrip_attack_profile_options(character)
    return _selected_profile(
        profiles,
        character.get("presentation_preferences", {}).get("featured_cantrip", ""),
        "cantrip",
    )


def weapon_attack_profile(character: Mapping, weapon: Mapping | None) -> AttackProfile | None:
    if not weapon or not weapon.get("name"):
        return None
    name = str(weapon.get("name"))
    rules = WEAPON_RULES.get(name)
    if not rules:
        return None

    ability = weapon_attack_ability(character, rules)
    ability_mod = character_ability_modifier(character, ability)
    attack_bonus = ability_mod + (int(character.get("proficiency_bonus", 2) or 2) if proficient_with_weapon(character, weapon) else 0)
    attack_bonus += weapon_attack_modifier_bonus(character, rules)

    damage_bonus = ability_mod + weapon_damage_modifier_bonus(character, rules)
    damage_type = full_damage_type(weapon.get("damage_type", ""))
    return AttackProfile(
        name=name,
        attack_display=format_modifier(attack_bonus),
        damage_display=f"{weapon_damage_dice(character, weapon, rules)}{format_damage_bonus(damage_bonus)} {damage_type}".strip(),
        kind="weapon",
    )


def weapon_attack_ability(character: Mapping, rules: Mapping) -> str:
    properties = set(rules.get("properties", set()))
    if "finesse" in properties:
        strength = character_ability_modifier(character, "Strength")
        dexterity = character_ability_modifier(character, "Dexterity")
        return "Dexterity" if dexterity > strength else "Strength"
    if rules.get("kind") == "ranged":
        return "Dexterity"
    return "Strength"


def weapon_damage_dice(character: Mapping, weapon: Mapping, rules: Mapping) -> str:
    name = str(weapon.get("name") or "")
    wielding_modes = character.get("presentation_preferences", {}).get("weapon_wielding_modes", {})
    if rules.get("versatile_damage") and wielding_modes.get(name) == "two_handed":
        return str(rules["versatile_damage"])
    # No wielding mode is tracked yet, so versatile weapons export their one-handed damage.
    return str(weapon.get("damage") or "")


def proficient_with_weapon(character: Mapping, weapon: Mapping) -> bool:
    return character_is_proficient_with_weapon(character.get("weapon_proficiencies", []), weapon)


def weapon_attack_modifier_bonus(character: Mapping, rules: Mapping) -> int:
    if rules.get("kind") != "ranged":
        return 0
    styles = merge_unique(
        [character.get("class_options", {}).get("fighting_style", "")],
        character.get("class_options", {}).get("champion_additional_fighting_styles", []),
    )
    return 2 if "Archery" in styles else 0


def weapon_damage_modifier_bonus(character: Mapping, rules: Mapping) -> int:
    return 0


def cantrip_attack_profile(character: Mapping, spell_name: str) -> AttackProfile | None:
    rule = CANTRIP_ATTACK_RULES.get(str(spell_name or ""))
    if not rule:
        return None
    source = spellcasting_source_for_spell(character, spell_name)
    if not source:
        return None
    multiplier = cantrip_damage_multiplier(character.get("level", 1))
    damage_display = f"{multiplier}{rule['damage_die']} {rule['damage_type']}"
    if rule["mode"] == "save":
        attack_display = f"DC {source['spell_save_dc']} {rule['save_ability']}"
    else:
        attack_display = format_modifier(int(source["spell_attack_bonus"]))
    return AttackProfile(
        name=str(spell_name),
        attack_display=attack_display,
        damage_display=damage_display,
        kind="cantrip",
    )


def spellcasting_source_for_spell(character: Mapping, spell_name: str) -> dict | None:
    for record in character.get("spell_grant_details", []):
        if record.get("name") != spell_name:
            continue
        ability = record.get("spellcasting_ability", "")
        if ability:
            return spellcasting_source_record(character, ability)
    ability = character.get("spellcasting_ability", "") or character.get("origin_feat_choices", {}).get("spellcasting_ability", "")
    if not ability:
        ability = character.get("species_options", {}).get("lineage_spellcasting_ability", "")
    return spellcasting_source_record(character, ability) if ability else None


def spellcasting_source_record(character: Mapping, ability: str) -> dict:
    modifier = character_ability_modifier(character, ability)
    proficiency = int(character.get("proficiency_bonus", 2) or 2)
    return {
        "ability": ability,
        "spell_save_dc": 8 + proficiency + modifier,
        "spell_attack_bonus": proficiency + modifier,
    }


def cantrip_damage_multiplier(level: int) -> int:
    level = int(level or 1)
    if level >= 17:
        return 4
    if level >= 11:
        return 3
    if level >= 5:
        return 2
    return 1


def damaging_cantrip_names(character: Mapping) -> list[str]:
    return [profile["name"] for profile in cantrip_attack_profile_options(character)]


def spell_grant_names(character: Mapping) -> list[str]:
    return [record.get("name", "") for record in character.get("spell_grant_details", []) if record.get("name")]


def character_ability_modifier(character: Mapping, ability: str) -> int:
    modifiers = character.get("ability_modifiers", {})
    if ability in modifiers:
        return int(modifiers.get(ability) or 0)
    return ability_modifier(character.get("ability_scores", {}).get(ability, 10))


def full_damage_type(value: str) -> str:
    text = str(value or "")
    return DAMAGE_TYPES.get(text, text)


def format_damage_bonus(value: int) -> str:
    if value > 0:
        return f"+{value}"
    if value < 0:
        return str(value)
    return ""


def _selected_profile(profiles: Iterable[dict], preferred_name: str, kind: str) -> AttackProfile | None:
    profiles = list(profiles or [])
    if not profiles:
        return None
    selected = next((profile for profile in profiles if profile.get("name") == preferred_name), profiles[0])
    return AttackProfile(
        name=selected.get("name", ""),
        attack_display=selected.get("attack_display", ""),
        damage_display=selected.get("damage_display", ""),
        kind=selected.get("kind", kind),
    )


def _weapon_lookup(data: Mapping | None) -> dict:
    return {
        weapon.get("name", ""): weapon
        for weapon in (data or {}).get("weapons", [])
        if weapon.get("name")
    }
