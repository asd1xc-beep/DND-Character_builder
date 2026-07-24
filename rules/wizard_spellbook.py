from rules.wizard_savant import selected_savant_spells


def character_is_wizard(character):
    return character.get("class") == "Wizard"


def wizard_spellbook_spells(character):
    if not character_is_wizard(character):
        return list(character.get("spells", {}).get("spellbook", []))
    spells = character.get("spells", {})
    spellbook = list(spells.get("spellbook", []))
    legacy_known = list(spells.get("known", []))
    return merge_unique(spellbook, legacy_known, selected_savant_spells(character))


def merge_unique(*lists):
    merged = []
    for items in lists:
        for item in items or []:
            if item and item not in merged:
                merged.append(item)
    return merged
