def spell_metadata_by_name(spells):
    return {
        spell.get("name", ""): spell
        for spell in spells or []
        if spell.get("name")
    }


def spell_level_label(level):
    if level == 0:
        return "Cantrip"
    if isinstance(level, int):
        return f"Level {level}"
    return "Unknown level"


def spell_option_label(spell_name, metadata_by_name):
    spell = metadata_by_name.get(spell_name, {})
    level = spell.get("level")
    if level is None:
        return spell_name
    return f"{spell_level_label(level)} - {spell_name}"


def sort_spell_options_by_level(spell_names, metadata_by_name):
    return sorted(
        spell_names or [],
        key=lambda name: (
            metadata_by_name.get(name, {}).get("level", 99),
            name,
        ),
    )


def selected_spell_options_for_display(selected_spell_names, spells):
    metadata_by_name = spell_metadata_by_name(spells)
    return sort_spell_options_by_level(
        [
            name
            for name in selected_spell_names or []
            if name in metadata_by_name
        ],
        metadata_by_name,
    )


def uses_spellbook_prepared_control(spellcasting):
    return "spellbook_spells" in (spellcasting or {})


def uses_generic_prepared_control(spellcasting):
    spellcasting = spellcasting or {}
    return "prepared_spells" in spellcasting and "spellbook_spells" not in spellcasting


def known_spell_choice_label(limit):
    return f"Choose {limit} known spells"


def is_spell_choice(choice):
    class_option_key = choice.get("class_option_key", "")
    return (
        choice.get("type") in {
            "spell_selection",
            "spellbook_spells",
            "feat_spell_selection",
            "spell_mastery_selection",
            "signature_spells_selection",
        }
        or choice.get("apply_to") == "spell_grants"
        or class_option_key.startswith("mystic_arcanum_")
        or class_option_key.startswith("savant_spells_level_")
        or choice.get("class_option_key") in {
            "blessed_warrior_cantrips",
            "druidic_warrior_cantrips",
            "magical_discoveries",
            "mystic_arcanum",
            "savant_spells",
        }
    )
