from services.spell_labels import (
    is_spell_choice,
    known_spell_choice_label,
    selected_spell_options_for_display,
    sort_spell_options_by_level,
    spell_metadata_by_name,
    spell_option_label,
    uses_generic_prepared_control,
    uses_spellbook_prepared_control,
)


def test_spell_labels_include_spell_level_and_sort_by_level():
    spells = [
        {"name": "Fireball", "level": 3},
        {"name": "Light", "level": 0},
        {"name": "Cure Wounds", "level": 1},
    ]
    lookup = spell_metadata_by_name(spells)

    assert spell_option_label("Light", lookup) == "Cantrip - Light"
    assert spell_option_label("Cure Wounds", lookup) == "Level 1 - Cure Wounds"
    assert sort_spell_options_by_level(["Fireball", "Light", "Cure Wounds"], lookup) == [
        "Light",
        "Cure Wounds",
        "Fireball",
    ]


def test_selected_spell_options_for_display_uses_selected_names_not_spell_dicts():
    spells = [
        {"name": "Magic Missile", "level": 1},
        {"name": "Fireball", "level": 3},
        {"name": "Light", "level": 0},
    ]

    assert selected_spell_options_for_display(
        ["Fireball", "Missing Spell", "Magic Missile"],
        spells,
    ) == [
        "Magic Missile",
        "Fireball",
    ]


def test_spell_choice_detection_covers_level_up_spell_sources():
    assert is_spell_choice({"type": "spell_selection"})
    assert is_spell_choice({"type": "spell_mastery_selection"})
    assert is_spell_choice({"type": "class_option_selection", "apply_to": "spell_grants"})
    assert is_spell_choice({"type": "class_option_selection", "class_option_key": "mystic_arcanum"})
    assert is_spell_choice({"type": "class_option_selection", "class_option_key": "mystic_arcanum_6"})
    assert not is_spell_choice({"type": "class_option_selection", "class_option_key": "metamagic"})


def test_spellbook_casters_use_only_spellbook_prepared_control():
    wizard_spellcasting = {"spellbook_spells": 8, "prepared_spells": 5}
    cleric_spellcasting = {"prepared_spells": 5}

    assert uses_spellbook_prepared_control(wizard_spellcasting)
    assert not uses_generic_prepared_control(wizard_spellcasting)
    assert not uses_spellbook_prepared_control(cleric_spellcasting)
    assert uses_generic_prepared_control(cleric_spellcasting)


def test_known_spell_label_does_not_use_spellbook_wording():
    assert known_spell_choice_label(4) == "Choose 4 known spells"
