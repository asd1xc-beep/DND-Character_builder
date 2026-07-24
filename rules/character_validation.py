from rules.class_choice_rules import (
    battle_master_maneuver_total,
    eligible_spell_lists_for_prepared_spells,
    required_class_choice_messages,
)
from rules.leveling import (
    SUPPORTED_LEVELS,
    effective_spellcasting,
    available_spell_levels_from_slots,
    get_available_spell_levels,
    get_class_resources,
    get_casting_type,
    selected_subclass_options,
    supported_levels_message,
)
from rules.weapon_mastery import eligible_weapon_mastery_names
from rules.wizard_spellbook import wizard_spellbook_spells
from rules.wizard_savant import (
    savant_spell_choice_keys_up_to_level,
    savant_spell_choice_rule,
    selected_savant_spells,
)


def build_validation_report(character, class_data=None, species_data=None, background_data=None, spells=None, weapons=None):
    missing = []
    warnings = []
    unsupported = []

    if not character.get("name"):
        missing.append("Enter character name")
    if not character.get("species"):
        missing.append("Choose species")
    if not character.get("background"):
        missing.append("Choose background")
    if not character.get("class"):
        missing.append("Choose class")

    if class_data:
        skill_rule = class_data.get("skill_choices", {})
        required_skills = skill_rule.get("choose", 0)
        selected_class_skills = character.get("class_options", {}).get("class_skills", [])
        if len(selected_class_skills) < required_skills:
            missing.append(f"Choose {required_skills} class skills")

        level = int(character.get("level", 1) or 1)
        spellcasting = effective_spellcasting(class_data, character.get("subclass", ""), level) or {}
        cantrips_needed = spellcasting.get("cantrips_known", 0)
        if cantrips_needed and len(character.get("spells", {}).get("cantrips", [])) < cantrips_needed:
            missing.append(f"Choose {cantrips_needed} cantrips")
        prepared_needed = spellcasting.get("prepared_spells", 0)
        prepared_spells = character.get("spells", {}).get("prepared", [])
        if class_data.get("name") == "Wizard":
            savant_spells = selected_savant_spells(character)
            spellbook_needed = spellcasting.get("spellbook_spells", 0) + len(savant_spells)
            spellbook_spells = wizard_spellbook_spells(character)
            if spellbook_needed and len(spellbook_spells) < spellbook_needed:
                missing.append(f"Choose {spellbook_needed} spellbook spells")
            if spellbook_needed and len(spellbook_spells) > spellbook_needed:
                missing.append(f"Choose no more than {spellbook_needed} spellbook spells")
            if prepared_needed and len(prepared_spells) > prepared_needed:
                missing.append(f"Choose no more than {prepared_needed} prepared spells")
        else:
            if prepared_needed and len(prepared_spells) < prepared_needed:
                missing.append(f"Choose {prepared_needed} prepared spells")
            if prepared_needed and len(prepared_spells) > prepared_needed:
                missing.append(f"Choose no more than {prepared_needed} prepared spells")
            known_needed = spellcasting.get("known_spells", 0)
            if known_needed and len(character.get("spells", {}).get("known", [])) < known_needed:
                missing.append(f"Choose {known_needed} known spells")
        if spells and spellcasting:
            missing.extend(invalid_spell_choice_messages(character, class_data, spellcasting, level, spells))

        mastery_needed = get_class_resources(class_data, level).get("weapon_mastery_count", 0)
        if mastery_needed and len(character.get("weapon_masteries", [])) < mastery_needed:
            missing.append(f"Choose {mastery_needed} Weapon Mastery weapons")
        if mastery_needed and weapons is not None:
            eligible_masteries = set(eligible_weapon_mastery_names(character, weapons))
            if eligible_masteries:
                invalid_masteries = [
                    weapon
                    for weapon in character.get("weapon_masteries", [])
                    if weapon not in eligible_masteries
                ]
                if invalid_masteries:
                    missing.append("Choose valid Weapon Mastery weapons")

        class_options = class_data.get("class_options", {})
        selected_class_options = character.get("class_options", {})
        if "divine_order" in class_options and not selected_class_options.get("divine_order"):
            missing.append("Choose Divine Order")
        if "primal_order" in class_options and not selected_class_options.get("primal_order"):
            missing.append("Choose Primal Order")
        if selected_class_options.get("divine_order") == "Thaumaturge" and not selected_class_options.get("extra_cantrips"):
            missing.append("Choose Thaumaturge cantrip")
        if selected_class_options.get("primal_order") == "Magician" and not selected_class_options.get("extra_cantrips"):
            missing.append("Choose Magician cantrip")
        missing.extend(required_class_choice_messages(character, class_data, level))

        subclass_options = selected_subclass_options(class_data, character.get("subclass", ""))
        maneuver_rule = subclass_options.get("maneuvers", {})
        if maneuver_rule:
            maneuver_total = maneuver_rule.get("choose", 0)
            if class_data.get("name") == "Fighter" and character.get("subclass") == "Battle Master":
                maneuver_total = battle_master_maneuver_total(level)
            if len(selected_class_options.get("maneuvers", [])) < maneuver_total:
                missing.append(f"Choose {maneuver_total} Battle Master maneuvers")
        if "student_of_war_skill" in subclass_options and not selected_class_options.get("student_of_war_skill"):
            missing.append("Choose Student of War skill")
        if "student_of_war_tool" in subclass_options and not selected_class_options.get("student_of_war_tool"):
            missing.append("Choose Student of War artisan tool")
        lore_skill_rule = subclass_options.get("lore_skills", {})
        if lore_skill_rule and len(selected_class_options.get("lore_skills", [])) < lore_skill_rule.get("choose", 0):
            missing.append(f"Choose {lore_skill_rule.get('choose', 0)} College of Lore skills")
        hunter_rule = subclass_options.get("hunters_prey", {})
        if hunter_rule and not selected_class_options.get("hunters_prey"):
            missing.append("Choose Hunter's Prey")
        companion_rule = subclass_options.get("primal_companion", {})
        if companion_rule and not selected_class_options.get("primal_companion"):
            missing.append("Choose Primal Companion")
        savant_rule = subclass_options.get("savant_spells", {})
        if savant_rule and len(selected_class_options.get("savant_spells", [])) < savant_rule.get("choose", 0):
            missing.append(f"Choose {savant_rule.get('choose', 0)} subclass spells")
        if class_data.get("name") == "Wizard":
            for key in savant_spell_choice_keys_up_to_level(level):
                if key == "savant_spells":
                    continue
                source_level = int(key.rsplit("_", 1)[-1])
                rule = savant_spell_choice_rule(subclass_options, character.get("subclass", ""), source_level)
                if rule and len(selected_class_options.get(key, [])) < rule.get("choose", 0):
                    missing.append(f"Choose {rule.get('choose', 0)} {character.get('subclass', '')} Savant spell")
        structured_spell_rule = subclass_options.get("structured_spell_choice", {})
        if structured_spell_rule and not selected_class_options.get("structured_spell_choice"):
            missing.append(f"Choose {structured_spell_rule.get('name', 'subclass spell group')}")

    if species_data:
        skill_rule = species_data.get("skill_choices", {})
        selected_species_skills = character.get("species_options", {}).get("skill_proficiencies", [])
        if skill_rule.get("choose", 0) and len(selected_species_skills) < skill_rule["choose"]:
            missing.append(f"Choose {skill_rule['choose']} species skill")

        if species_data.get("lineage_options", []) and not character.get("species_options", {}).get("lineage"):
            missing.append("Choose species lineage")

        choice_options = species_data.get("choice_options")
        if choice_options and not character.get("species_options", {}).get(choice_options["key"]):
            missing.append(f"Choose {choice_options['name']}")

        if "Versatile" in species_data.get("traits", []) and not character.get("species_options", {}).get("origin_feats"):
            missing.append("Choose Human Origin feat")

    if background_data:
        ability_options = background_data.get("ability_options", {})
        if ability_options.get("mode") == "choose_weighted":
            background_options = character.get("background_options", {})
            if not background_options.get("primary_ability") or not background_options.get("secondary_ability"):
                missing.append("Choose background ability score bonuses")

    feats = []
    if background_data:
        feats.extend(background_data.get("origin_feats", []))
    feats.extend(character.get("species_options", {}).get("origin_feats", []))
    choices = character.get("origin_feat_choices", {})

    if "Skilled" in feats and len(choices.get("skills", []) + choices.get("tools", [])) < 3:
        missing.append("Choose 3 Skilled proficiencies")
    if "Crafter" in feats and len(choices.get("tools", [])) < 3:
        missing.append("Choose 3 Crafter tools")
    if "Musician" in feats and len(choices.get("tools", [])) < 3:
        missing.append("Choose 3 Musician instruments")

    magic_feats = [feat for feat in feats if feat.startswith("Magic Initiate")]
    if magic_feats:
        if len(choices.get("cantrips", [])) < 2:
            missing.append("Choose 2 Magic Initiate cantrips")
        if not choices.get("spell"):
            missing.append("Choose Magic Initiate Level 1 spell")
        if not choices.get("spellcasting_ability"):
            missing.append("Choose Magic Initiate spellcasting ability")

    if int(character.get("level", 1)) not in SUPPORTED_LEVELS:
        unsupported.append(supported_levels_message().removesuffix("."))
    unresolved_choices = [
        choice
        for choice in character.get("pending_choices", [])
        if choice.get("status") != "resolved"
    ]
    if unresolved_choices:
        missing.append(f"Resolve {len(unresolved_choices)} pending level-up choice(s)")
    if character.get("subclass"):
        warnings.append("Subclass features are tracked; detailed subclass mechanics are still in progress")

    if "Savage Attacker" in feats:
        warnings.append("Savage Attacker is tracked as a feature; attack reroll workflow is not automated")
    if "Tavern Brawler" in feats:
        warnings.append("Tavern Brawler is tracked as a feature; unarmed strike/combat workflow is not automated")

    return {
        "complete": not missing and not unsupported,
        "missing": missing,
        "warnings": warnings,
        "unsupported": unsupported,
    }


def get_required_choices(character, class_data=None, species_data=None, background_data=None):
    return build_validation_report(character, class_data, species_data, background_data)["missing"]


def invalid_spell_choice_messages(character, class_data, spellcasting, level, spells):
    spell_lookup = {spell.get("name"): spell for spell in spells}
    spell_list = spellcasting.get("spell_list", class_data.get("name", ""))
    available_levels = set(
        available_spell_levels_from_slots(
            spellcasting.get("spell_slots", {}),
            get_casting_type(class_data, level),
        )
    ) or set(get_available_spell_levels(class_data, level))
    messages = []

    for spell_name in character.get("spells", {}).get("cantrips", []):
        spell = spell_lookup.get(spell_name)
        if not spell:
            continue
        if spell.get("level") != 0 or spell_list not in spell.get("classes", []):
            messages.append(f"{spell_name} is not an eligible {spell_list} cantrip")

    if class_data.get("name") == "Wizard":
        return wizard_spell_choice_messages(
            character,
            spell_lookup,
            spellcasting,
            available_levels,
            messages,
        )

    for field, label in (("prepared", "prepared spell"), ("known", "known spell")):
        eligible_lists = {spell_list}
        if field == "prepared":
            eligible_lists = set(eligible_spell_lists_for_prepared_spells(class_data, level, spellcasting))
        for spell_name in character.get("spells", {}).get(field, []):
            spell = spell_lookup.get(spell_name)
            if not spell:
                continue
            if not eligible_lists.intersection(spell.get("classes", [])):
                list_label = ", ".join(sorted(eligible_lists)) or spell_list
                messages.append(f"{spell_name} is not on the {list_label} spell list")
            elif spell.get("level") not in available_levels:
                messages.append(f"{spell_name} is not an eligible Level {spell.get('level')} {label}")

    return messages


def wizard_spell_choice_messages(character, spell_lookup, spellcasting, available_levels, messages):
    spellbook = wizard_spellbook_spells(character)
    raw_spellbook = list(character.get("spells", {}).get("spellbook", []))
    if not raw_spellbook:
        raw_spellbook = list(character.get("spells", {}).get("known", []))
    prepared = character.get("spells", {}).get("prepared", [])
    spellbook_set = set(spellbook)

    if len(raw_spellbook) != len(set(raw_spellbook)):
        messages.append("Choose each Wizard spellbook spell only once")
    if len(prepared) != len(set(prepared)):
        messages.append("Choose each Wizard prepared spell only once")

    for spell_name in spellbook:
        spell = spell_lookup.get(spell_name)
        if not spell:
            continue
        if "Wizard" not in spell.get("classes", []):
            messages.append(f"{spell_name} is not on the Wizard spell list")
        elif spell.get("level") == 0:
            messages.append(f"{spell_name} cannot be a Wizard spellbook cantrip")
        elif spell.get("level") not in available_levels:
            messages.append(f"{spell_name} is not an eligible Level {spell.get('level')} spellbook spell")

    for spell_name in prepared:
        spell = spell_lookup.get(spell_name)
        if not spell:
            continue
        if spell_name not in spellbook_set:
            messages.append(f"{spell_name} must be in your Wizard spellbook before it can be prepared")
        if spell.get("level") == 0:
            messages.append(f"{spell_name} cannot be a prepared Wizard cantrip")
        elif "Wizard" not in spell.get("classes", []):
            messages.append(f"{spell_name} is not on the Wizard spell list")
        elif spell.get("level") not in available_levels:
            messages.append(f"{spell_name} is not an eligible Level {spell.get('level')} prepared spell")
    return messages
