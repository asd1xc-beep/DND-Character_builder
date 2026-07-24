from models.character import new_character
from rules.attack_profiles import (
    build_attack_profiles,
    cantrip_attack_profile,
    cantrip_damage_multiplier,
    weapon_attack_profile,
)
from services.save_load import migrate_character


WEAPONS = [
    {"name": "Longsword", "category": "Martial", "damage": "1d8", "damage_type": "S"},
    {"name": "Longbow", "category": "Martial", "damage": "1d8", "damage_type": "P"},
    {"name": "Rapier", "category": "Martial", "damage": "1d8", "damage_type": "P"},
]


def character(**overrides):
    built = new_character()
    built.update({
        "level": 1,
        "proficiency_bonus": 2,
        "ability_scores": {
            "Strength": 16,
            "Dexterity": 14,
            "Constitution": 10,
            "Intelligence": 10,
            "Wisdom": 10,
            "Charisma": 10,
        },
        "ability_modifiers": {
            "Strength": 3,
            "Dexterity": 2,
            "Constitution": 0,
            "Intelligence": 0,
            "Wisdom": 0,
            "Charisma": 0,
        },
        "weapon_proficiencies": ["Martial Weapons"],
        "equipment": [],
        "spells": {"cantrips": [], "known": [], "prepared": [], "spellbook": []},
    })
    for key, value in overrides.items():
        built[key] = value
    return built


def weapon(name):
    return next(item for item in WEAPONS if item["name"] == name)


def test_proficient_strength_melee_weapon_profile():
    profile = weapon_attack_profile(character(), weapon("Longsword"))

    assert profile.as_dict() == {
        "name": "Longsword",
        "attack_display": "+5",
        "damage_display": "1d8+3 Slashing",
        "kind": "weapon",
    }


def test_dexterity_ranged_weapon_profile():
    archer = character(ability_modifiers={**character()["ability_modifiers"], "Dexterity": 3})

    profile = weapon_attack_profile(archer, weapon("Longbow"))

    assert profile.attack_display == "+5"
    assert profile.damage_display == "1d8+3 Piercing"


def test_finesse_weapon_uses_higher_strength_or_dexterity_modifier():
    duelist = character(ability_modifiers={**character()["ability_modifiers"], "Strength": 0, "Dexterity": 3})

    profile = weapon_attack_profile(duelist, weapon("Rapier"))

    assert profile.attack_display == "+5"
    assert profile.damage_display == "1d8+3 Piercing"


def test_non_proficient_weapon_omits_proficiency_from_attack_and_damage():
    novice = character(weapon_proficiencies=[])

    profile = weapon_attack_profile(novice, weapon("Longsword"))

    assert profile.attack_display == "+3"
    assert profile.damage_display == "1d8+3 Slashing"


def test_attack_roll_cantrip_profile_uses_spell_attack_bonus():
    caster = character(
        spellcasting_ability="Charisma",
        ability_modifiers={**character()["ability_modifiers"], "Charisma": 3},
    )

    profile = cantrip_attack_profile(caster, "Fire Bolt")

    assert profile.attack_display == "+5"
    assert profile.damage_display == "1d10 Fire"


def test_saving_throw_cantrip_profile_uses_save_dc():
    caster = character(
        spellcasting_ability="Wisdom",
        ability_modifiers={**character()["ability_modifiers"], "Wisdom": 3},
    )

    profile = cantrip_attack_profile(caster, "Sacred Flame")

    assert profile.attack_display == "DC 13 DEX"
    assert profile.damage_display == "1d8 Radiant"


def test_cantrip_damage_scaling_by_total_character_level():
    assert cantrip_damage_multiplier(1) == 1
    assert cantrip_damage_multiplier(5) == 2
    assert cantrip_damage_multiplier(11) == 3
    assert cantrip_damage_multiplier(17) == 4

    caster = character(
        level=17,
        spellcasting_ability="Charisma",
        ability_modifiers={**character()["ability_modifiers"], "Charisma": 3},
    )

    assert cantrip_attack_profile(caster, "Fire Bolt").damage_display == "4d10 Fire"


def test_non_caster_export_has_only_valid_weapon_profile():
    fighter = character(equipment=["Longsword"])

    profiles = build_attack_profiles(fighter, {"weapons": WEAPONS})

    assert profiles == [{
        "name": "Longsword",
        "attack_display": "+5",
        "damage_display": "1d8+3 Slashing",
        "kind": "weapon",
    }]


def test_caster_with_no_damaging_cantrip_leaves_cantrip_row_unavailable():
    caster = character(
        spellcasting_ability="Charisma",
        ability_modifiers={**character()["ability_modifiers"], "Charisma": 3},
        spells={"cantrips": ["Light"], "known": [], "prepared": [], "spellbook": []},
    )

    assert build_attack_profiles(caster, {"weapons": WEAPONS}) == []


def test_export_preferences_select_valid_profiles_without_core_choice_changes():
    caster = character(
        spellcasting_ability="Charisma",
        ability_modifiers={**character()["ability_modifiers"], "Charisma": 3},
        equipment=["Longsword", "Longbow"],
        spells={"cantrips": ["Light", "Fire Bolt"], "known": [], "prepared": [], "spellbook": []},
        presentation_preferences={"primary_weapon": "Longbow", "featured_cantrip": "Fire Bolt"},
    )

    profiles = build_attack_profiles(caster, {"weapons": WEAPONS})

    assert profiles[0]["name"] == "Longbow"
    assert profiles[1]["name"] == "Fire Bolt"
    assert caster["spells"]["cantrips"] == ["Light", "Fire Bolt"]


def test_streamlit_pdf_export_options_smoke_sets_presentation_preferences():
    from streamlit.testing.v1 import AppTest

    script = '''
import streamlit as st
from ui.pdf_export_options import render_pdf_export_options

if "character" not in st.session_state:
    st.session_state.character = {
        "level": 1,
        "proficiency_bonus": 2,
        "ability_modifiers": {"Strength": 3, "Dexterity": 2, "Charisma": 3},
        "ability_scores": {"Strength": 16, "Dexterity": 14, "Charisma": 16},
        "weapon_proficiencies": ["Martial Weapons"],
        "equipment": ["Longsword"],
        "spellcasting_ability": "Charisma",
        "spells": {"cantrips": ["Fire Bolt"], "known": [], "prepared": [], "spellbook": []},
        "presentation_preferences": {},
    }

render_pdf_export_options(
    st.session_state.character,
    {"weapons": [{"name": "Longsword", "category": "Martial", "damage": "1d8", "damage_type": "S"}]},
)
'''
    at = AppTest.from_string(script, default_timeout=10).run()

    assert not at.exception
    assert at.session_state["character"]["presentation_preferences"]["primary_weapon"] == "Longsword"
    assert at.session_state["character"]["presentation_preferences"]["featured_cantrip"] == "Fire Bolt"


def test_old_saves_gain_pdf_presentation_preferences_without_rules_choices():
    migrated = migrate_character({"name": "Old Export Save"})

    assert migrated["presentation_preferences"] == {
        "primary_weapon": "",
        "featured_cantrip": "",
        "weapon_wielding_modes": {},
    }
    assert migrated["name"] == "Old Export Save"
