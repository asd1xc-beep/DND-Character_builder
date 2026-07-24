import pytest

from models.character import new_character
from rules.level_up import (
    commit_level_up_draft,
    create_level_up_draft,
    refresh_level_up_draft_choices,
    resolve_pending_choice,
)
from services.character_engine import recalculate_character
from services.character_sheet import build_character_sheet
from tests.test_level_one_builds import app_data


@pytest.fixture
def enable_level_17_20_for_test(monkeypatch):
    levels = list(range(1, 21))
    import rules.character_validation as character_validation
    import rules.leveling as leveling

    monkeypatch.setattr(leveling, "SUPPORTED_LEVELS", levels)
    monkeypatch.setattr(character_validation, "SUPPORTED_LEVELS", levels)


def level_twenty_character(class_name, subclass=""):
    character = new_character()
    character.update({
        "name": f"Level 20 {class_name}",
        "species": "Human",
        "background": "Sage",
        "class": class_name,
        "subclass": subclass,
        "level": 20,
    })
    character["background_options"] = {
        "primary_ability": "Intelligence",
        "secondary_ability": "Charisma",
    }
    character["species_options"] = {
        "skill_proficiencies": ["Perception"],
        "origin_feats": ["Tough"],
    }
    character["class_options"] = {"class_skills": ["Arcana", "Investigation"]}
    return character


def wizard_spell_names(data, levels, count, exclude=None):
    excluded = set(exclude or [])
    level_set = set(levels)
    names = [
        spell["name"]
        for spell in data["spells"]
        if "Wizard" in spell.get("classes", [])
        and spell.get("level") in level_set
        and spell["name"] not in excluded
    ]
    assert len(names) >= count
    return names[:count]


def test_level_twenty_ability_capstones_apply_with_25_maximum(enable_level_17_20_for_test):
    data = app_data()
    barbarian = level_twenty_character("Barbarian", "Berserker")
    barbarian["base_ability_scores"].update({"Strength": 22, "Constitution": 18})
    monk = level_twenty_character("Monk", "Warrior of Mercy")
    monk["base_ability_scores"].update({"Dexterity": 22, "Wisdom": 18})

    recalculate_character(barbarian, data)
    recalculate_character(monk, data)

    assert barbarian["ability_scores"]["Strength"] == 25
    assert barbarian["ability_scores"]["Constitution"] == 22
    assert barbarian["ability_score_adjustment_bonuses"]["Strength"] == 3
    assert monk["ability_scores"]["Dexterity"] == 25
    assert monk["ability_scores"]["Wisdom"] == 22
    assert monk["ability_score_adjustment_bonuses"]["Dexterity"] == 3


def test_level_twenty_class_capstone_resources_are_sheet_ready(enable_level_17_20_for_test):
    data = app_data()
    cases = [
        ("Cleric", "Life", {"greater_divine_intervention_wish_recharge": "2d4 long rests"}),
        ("Druid", "Circle of the Land", {"archdruid_wild_shape_slot_conversion": True}),
        ("Fighter", "Champion", {"attacks_per_attack_action": 4}),
        ("Ranger", "Hunter", {"hunters_mark_damage_die": "1d10"}),
        ("Rogue", "Thief", {"stroke_of_luck_recharge": "short_or_long_rest"}),
        ("Sorcerer", "Draconic Sorcery", {"arcane_apotheosis_free_metamagic_per_turn": 1}),
        ("Warlock", "Fiend Patron", {"eldritch_master_pact_slot_recovery": "all"}),
    ]

    for class_name, subclass, expected in cases:
        character = level_twenty_character(class_name, subclass)
        recalculate_character(character, data)
        resources = character["derived_resources"]
        for key, value in expected.items():
            assert resources.get(key) == value


def test_level_twenty_paladin_subclass_capstones_track_free_use_and_slot_recovery(enable_level_17_20_for_test):
    data = app_data()
    cases = [
        ("Oath of Devotion", "holy_nimbus"),
        ("Oath of Glory", "living_legend"),
        ("Oath of Vengeance", "avenging_angel"),
        ("Oath of the Ancients", "elder_champion"),
    ]

    for subclass, key in cases:
        character = level_twenty_character("Paladin", subclass)
        recalculate_character(character, data)
        resources = character["derived_resources"]
        assert resources[f"{key}_free_uses"] == 1
        assert resources[f"{key}_recharge"] == "long_rest"
        assert resources[f"{key}_alternate_recovery_resource"] == "Level 5 spell slot"


def test_words_of_creation_grants_power_word_spells_to_sheet(enable_level_17_20_for_test):
    data = app_data()
    character = level_twenty_character("Bard", "College of Lore")
    recalculate_character(character, data)
    sheet = build_character_sheet(character)
    grants = {
        grant["name"]: grant
        for grant in sheet["spells"]["grant_details"]
        if grant["source"].get("source_name") == "Words of Creation"
    }

    assert set(grants) == {"Power Word Heal", "Power Word Kill"}
    assert grants["Power Word Heal"]["always_prepared"] is True
    assert grants["Power Word Heal"]["counts_against_limit"] is False
    assert grants["Power Word Heal"]["casting_rules"]["can_target_second_creature_within_10_feet"] is True
    assert "Words of Creation" in next(
        detail["sources"]
        for detail in sheet["spell_details"]
        if detail["name"] == "Power Word Kill"
    )


def test_wizard_signature_spells_are_chosen_during_level_up_and_granted(enable_level_17_20_for_test):
    data = app_data()
    spellbook = [
        "Fireball",
        "Fly",
        *wizard_spell_names(data, range(1, 10), 36, exclude={"Fireball", "Fly"}),
    ]
    character = level_twenty_character("Wizard", "Evoker")
    character["level"] = 19
    character["spells"] = {
        "cantrips": wizard_spell_names(data, {0}, 5),
        "spellbook": spellbook,
        "known": [],
        "prepared": spellbook[:24],
    }
    recalculate_character(character, data)

    draft = create_level_up_draft(character, 20, data)
    signature_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "signature_spells_selection")
    spellbook_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "spellbook_spells")
    savant_choice = next(
        (
            choice
            for choice in draft["pending_choices"]
            if choice.get("class_option_key", "") == "savant_spells"
        ),
        None,
    )

    assert signature_choice["choose"] == 2
    assert "Fireball" in signature_choice["options"]
    assert "Fly" in signature_choice["options"]

    assert resolve_pending_choice(draft, spellbook_choice["id"], spellbook_choice["options"][:2], spellbook_choice)
    if savant_choice:
        assert resolve_pending_choice(draft, savant_choice["id"], savant_choice["options"][:2], savant_choice)
    assert resolve_pending_choice(draft, signature_choice["id"], ["Fireball", "Fly"], signature_choice)
    result = commit_level_up_draft(character, draft, data)
    assert result["ok"], result

    recalculate_character(character, data)
    sheet = build_character_sheet(character)
    grants = {
        grant["name"]: grant
        for grant in sheet["spells"]["grant_details"]
        if grant["source"].get("source_name") == "Signature Spells"
    }

    assert character["class_options"]["signature_spells"] == ["Fireball", "Fly"]
    assert set(grants) == {"Fireball", "Fly"}
    assert grants["Fireball"]["casting_rules"]["free_cast_spell_level"] == 3
    assert grants["Fireball"]["casting_rules"]["recharge"] == "short_or_long_rest"


def test_wizard_signature_spells_can_use_level_three_spells_added_in_same_draft(enable_level_17_20_for_test):
    data = app_data()
    new_signature_spell = "Fireball"
    spellbook = [
        "Fly",
        *wizard_spell_names(data, range(1, 10), 37, exclude={"Fireball", "Fly"}),
    ]
    character = level_twenty_character("Wizard", "Evoker")
    character["level"] = 19
    character["spells"] = {
        "cantrips": wizard_spell_names(data, {0}, 5),
        "spellbook": spellbook,
        "known": [],
        "prepared": spellbook[:24],
    }
    recalculate_character(character, data)

    draft = create_level_up_draft(character, 20, data)
    spellbook_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "spellbook_spells")
    signature_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "signature_spells_selection")
    other_spell = next(spell for spell in spellbook_choice["options"] if spell != new_signature_spell)

    assert new_signature_spell not in signature_choice["options"]
    assert resolve_pending_choice(draft, spellbook_choice["id"], [new_signature_spell, other_spell], spellbook_choice)

    refresh_level_up_draft_choices(character, draft, data)
    refreshed_signature = next(choice for choice in draft["pending_choices"] if choice["type"] == "signature_spells_selection")

    assert new_signature_spell in refreshed_signature["options"]
    assert resolve_pending_choice(
        draft,
        refreshed_signature["id"],
        [new_signature_spell, "Fly"],
        refreshed_signature,
    )
