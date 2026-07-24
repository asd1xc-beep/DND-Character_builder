import streamlit as st

from models.character import ABILITIES, merge_unique, new_character
from presentation.compact_catalog import (
    build_class_feature_choice_catalog,
    build_equipment_package_catalog,
    build_lineage_catalog,
    build_species_choice_catalog,
    build_subclass_catalog,
    option_value,
    subclass_stable_id,
)
from presentation.equipment_catalog import build_equipment_catalog
from presentation.feat_catalog import build_feat_catalog
from presentation.optional_feature_catalog import build_optional_feature_catalog
from presentation.option_catalog import (
    SpellSelectionGroupSpec,
    build_grouped_spell_option_catalog,
    build_spell_option_catalog,
)
from presentation.proficiency_catalog import (
    build_language_catalog,
    build_prefixed_skill_tool_catalog,
    build_skill_catalog,
    build_tool_catalog,
    compact_selected_ids,
    values_from_ids,
)
from presentation.weapon_mastery_catalog import build_weapon_mastery_catalog
from rules.ability_assignment import normalize_score_assignments, swap_score_assignment
from rules.ability_generation import STANDARD_ARRAY, roll_ability_scores
from rules.ability_scores import format_modifier
from rules.character_validation import build_validation_report
from rules.class_choice_rules import (
    LANGUAGE_OPTIONS,
    battle_master_maneuver_total,
    cantrip_options,
    eligible_spell_lists_for_prepared_spells,
    fighting_style_options,
)
from rules.feature_configurations import update_feature_configuration
from rules.invocations import (
    eligible_invocation_names,
    invocation_eligibility_reasons,
    invocation_is_eligible,
    normalize_invocation_options,
)
from rules.level_up import (
    choice_option_labels,
    commit_level_up_draft,
    create_level_up_draft,
    refresh_level_up_draft_choices,
    resolve_pending_choice,
    update_level_up_draft_status,
    validate_level_up_plan,
)
from rules.leveling import (
    SUPPORTED_LEVELS,
    class_features_at_level,
    effective_spellcasting,
    get_active_subclass_grants,
    selected_subclass_data,
    selected_subclass_options,
    get_available_spell_levels,
    get_class_resources,
)
from rules.proficiencies import (
    available_class_skill_options,
)
from rules.weapon_mastery import eligible_weapon_mastery_names
from rules.wizard_savant import savant_spell_choice_key, savant_spell_choice_rule
from services.data_loader import (
    FIVETOOLS_SOURCE,
    SAMPLE_SOURCE,
    available_data_sources,
    by_name,
    load_backgrounds,
    load_beasts,
    load_classes,
    load_equipment,
    load_feats,
    load_metadata,
    load_rules,
    load_skills,
    load_species,
    load_spells,
    load_weapon_masteries,
    load_weapons,
)
from services.character_sheet import build_character_sheet, spell_grants
from services.character_engine import active_origin_feats, recalculate_character, selected_structured_subclass_spells
from services.character_state import (
    change_background,
    change_character_class,
    change_origin_feat,
    change_species,
)
from services.equipment_state import derive_equipment, selected_default_equipment, sync_equipment_state
from services.pdf_export import export_character_pdf
from services.save_load import list_saved_characters, load_character, save_character
from services.spell_labels import (
    is_spell_choice,
    selected_spell_options_for_display,
    sort_spell_options_by_level,
    spell_metadata_by_name,
    spell_option_label,
    uses_generic_prepared_control,
    uses_spellbook_prepared_control,
)
from ui.option_browser import render_spell_option_browser, render_unified_spell_picker
from ui.spell_choice_browser import render_spell_choice_browser
from ui.compact_choice import render_compact_multi_choice, render_compact_single_choice
from ui.equipment_browser import render_equipment_browser
from ui.medium_option_browser import BrowserFilter, render_medium_option_browser, render_medium_single_option_browser
from ui.pdf_export_options import render_pdf_export_options
from ui.subclass_choice import render_subclass_choice


st.set_page_config(page_title="D&D Character Builder", page_icon="D20", layout="wide")

ABILITY_SCORE_METHODS = ["Manual entry", "Standard array", "Roll 4d6"]


@st.cache_data
def load_app_data(source_name):
    classes = load_classes(source_name)
    species = load_species(source_name)
    backgrounds = load_backgrounds(source_name)
    feats = load_feats(source_name)
    spells = load_spells(source_name)
    equipment = load_equipment(source_name)
    weapons = load_weapons(source_name)
    weapon_masteries = load_weapon_masteries(source_name)
    beasts = load_beasts(source_name)
    rules = load_rules(source_name)
    skills = load_skills(source_name)
    metadata = load_metadata(source_name)
    return {
        "source_name": source_name,
        "metadata": metadata,
        "classes": classes,
        "classes_by_name": by_name(classes),
        "species": species,
        "species_by_name": by_name(species),
        "backgrounds": backgrounds,
        "backgrounds_by_name": by_name(backgrounds),
        "feats": feats,
        "spells": spells,
        "equipment": equipment,
        "weapons": weapons,
        "weapon_masteries": weapon_masteries,
        "beasts": beasts,
        "rules": rules,
        "skills": skills,
    }


def initialize_session():
    if "character" not in st.session_state:
        st.session_state.character = new_character()
    st.session_state.setdefault("level_up_draft", None)


def select_index(options, current_value):
    try:
        return options.index(current_value)
    except ValueError:
        return 0


def optional_select_index(options, current_value):
    return options.index(current_value) if current_value in options else None


def clamp_multiselect(selection, limit):
    if limit and len(selection) > limit:
        st.warning(f"Choose up to {limit}. Using the first {limit} selected for calculations.")
        return selection[:limit]
    return selection


def spell_format_func(spells):
    lookup = spell_metadata_by_name(spells)
    return lambda spell_name: spell_option_label(spell_name, lookup)


def leveled_spell_options_for_display(spell_names, spells):
    return sort_spell_options_by_level(spell_names, spell_metadata_by_name(spells))


def choice_context_spells(choice_context):
    if isinstance(choice_context, dict):
        return choice_context.get("spells", [])
    return choice_context or []


def choice_context_data(choice_context):
    if isinstance(choice_context, dict) and "classes_by_name" in choice_context:
        return choice_context
    return {}


def selected_option_id(options, value):
    return next((option.stable_id for option in options if option_value(option) == value), None)


def compact_value_choice(
    options,
    current_value,
    *,
    state_key,
    label,
    placeholder="Choose an option",
    control="selectbox",
    detail_label="View full details",
):
    selected_id = selected_option_id(options, current_value)
    updated_id = render_compact_single_choice(
        options,
        selected_id,
        state_key=state_key,
        label=label,
        placeholder=placeholder,
        control=control,
        detail_label=detail_label,
    )
    selected_option = next((option for option in options if option.stable_id == updated_id), None)
    return option_value(selected_option) if selected_option else None


def compact_values_choice(
    options,
    current_values,
    *,
    selection_limit,
    state_key,
    label,
    detail_label="About selected options",
):
    selected_ids = compact_selected_ids(options, current_values)
    updated_ids = render_compact_multi_choice(
        options,
        selected_ids,
        selection_limit=selection_limit,
        state_key=state_key,
        label=label,
        detail_label=detail_label,
    )
    return values_from_ids(options, updated_ids)


def proficiency_choice_catalog(data, choice, options, selected):
    key = choice.get("class_option_key", "")
    label = (choice.get("name") or "").casefold()
    apply_to = choice.get("apply_to", "")
    if apply_to in {"expertise", "skill_proficiencies"} or "expertise" in label or "skill" in label:
        return build_skill_catalog(data.get("skills", []), options, selected)
    if apply_to == "languages" or "language" in label:
        return build_language_catalog(options, selected, source_label="XPHB")
    if "tool" in label or key.endswith("_tool"):
        return build_tool_catalog(options, selected, source_label="XPHB")
    return build_class_feature_choice_catalog(options, selected_name="", kind="choice")


def optional_feature_records(option_names, *, category="Optional feature", source_label="XPHB"):
    records = []
    for option in option_names or []:
        if isinstance(option, dict):
            name = option.get("name", "")
            if not name:
                continue
            records.append({
                "name": name,
                "category": option.get("category", category),
                "source": option.get("source", source_label),
                "raw_ref": option.get("raw_ref", name),
                "description": option.get("description", ""),
                "eligible": option.get("eligible", True),
                "prerequisite_labels": option.get("prerequisite_labels", []),
                "support": option.get("support", {}),
            })
            continue
        name = option
        if name:
            records.append({
                "name": name,
                "category": category,
                "source": source_label,
                "description": "",
                "eligible": True,
            })
    return records


def invocation_records(character, invocation_rule, level):
    records = []
    for invocation in normalize_invocation_options(invocation_rule):
        name = invocation.get("name", "")
        if not name:
            continue
        reasons = invocation_eligibility_reasons(character, invocation, level)
        records.append({
            "name": name,
            "category": "Eldritch Invocation",
            "source": invocation.get("source", "XPHB"),
            "raw_ref": invocation.get("raw_ref", name),
            "description": invocation.get("description", ""),
            "eligible": invocation_is_eligible(character, invocation, level),
            "eligibility_reasons": reasons,
            "prerequisite_labels": invocation.get("prerequisite_labels") or reasons,
            "support": invocation.get("support", {}),
        })
    return records


def related_features_for(class_or_subclass_data, feature_name):
    return (class_or_subclass_data.get("feature_related_features") or {}).get(feature_name, [])


def feature_descriptions_for(data, *records):
    descriptions = {}
    descriptions.update((data or {}).get("rules", {}).get("feature_descriptions", {}))
    for record in records:
        descriptions.update((record or {}).get("feature_descriptions", {}))
    return descriptions


def ability_score_widget_key(ability):
    return f"base_ability_score_{ability.lower()}"


def ability_score_slot_widget_key(ability):
    return f"ability_score_slot_{ability.lower()}"


def clear_ability_score_widgets():
    for ability in ABILITIES:
        st.session_state.pop(ability_score_widget_key(ability), None)
        st.session_state.pop(ability_score_slot_widget_key(ability), None)


def ensure_ability_score_widgets(character):
    base_scores = character.setdefault("base_ability_scores", {})
    for ability in ABILITIES:
        key = ability_score_widget_key(ability)
        if key not in st.session_state:
            st.session_state[key] = int(base_scores.get(ability, 10))


def apply_ability_scores(character, scores):
    character.setdefault("base_ability_scores", {})
    for ability, score in zip(ABILITIES, scores):
        character["base_ability_scores"][ability] = int(score)
        st.session_state[ability_score_widget_key(ability)] = int(score)


def reset_score_assignments(character, scores):
    character["ability_score_assignments"] = normalize_score_assignments(ABILITIES, scores)
    for ability, slot in character["ability_score_assignments"].items():
        st.session_state[ability_score_slot_widget_key(ability)] = slot
    apply_assigned_scores(character, scores)


def ensure_score_assignments(character, scores):
    assignments = normalize_score_assignments(
        ABILITIES,
        scores,
        character.setdefault("ability_score_assignments", {}),
    )
    character["ability_score_assignments"] = assignments
    for ability, slot in assignments.items():
        key = ability_score_slot_widget_key(ability)
        if key not in st.session_state or st.session_state[key] not in range(len(scores)):
            st.session_state[key] = slot


def apply_assigned_scores(character, scores):
    character.setdefault("base_ability_scores", {})
    for ability in ABILITIES:
        slot = character.get("ability_score_assignments", {}).get(ability, 0)
        score = scores[slot] if 0 <= slot < len(scores) else 10
        character["base_ability_scores"][ability] = int(score)
        st.session_state[ability_score_widget_key(ability)] = int(score)


def score_slot_labels(scores):
    labels = []
    seen = {}
    duplicates = {score for score in scores if scores.count(score) > 1}
    for score in scores:
        seen[score] = seen.get(score, 0) + 1
        labels.append(f"{score} #{seen[score]}" if score in duplicates else str(score))
    return labels


def update_score_assignment(character, ability, scores):
    key = ability_score_slot_widget_key(ability)
    selected_slot = st.session_state.get(key, 0)
    character["ability_score_assignments"] = swap_score_assignment(
        ABILITIES,
        scores,
        character.get("ability_score_assignments", {}),
        ability,
        selected_slot,
    )
    for score_ability, slot in character["ability_score_assignments"].items():
        st.session_state[ability_score_slot_widget_key(score_ability)] = slot
    apply_assigned_scores(character, scores)


def render_score_assignment_controls(character, scores):
    ensure_score_assignments(character, scores)
    labels = score_slot_labels(scores)
    assignments = character["ability_score_assignments"]
    cols = st.columns(3)
    for index, ability in enumerate(ABILITIES):
        with cols[index % 3]:
            key = ability_score_slot_widget_key(ability)
            if st.session_state.get(key) not in range(len(scores)):
                st.session_state[key] = assignments.get(ability, index)
            st.selectbox(
                ability,
                list(range(len(scores))),
                format_func=lambda slot: labels[slot],
                key=key,
                on_change=update_score_assignment,
                args=(character, ability, scores),
            )
    apply_assigned_scores(character, scores)


def score_method_control(label, options, current_value):
    if hasattr(st, "segmented_control"):
        return st.segmented_control(
            label,
            options,
            default=current_value if current_value in options else options[0],
        )
    return st.selectbox(label, options, index=select_index(options, current_value))


def spell_options(spells, class_name, level):
    return [
        spell["name"]
        for spell in spells
        if class_name in spell.get("classes", []) and spell.get("level") == level
    ]


def spell_options_for_lists(spells, class_names, level):
    class_names = set(class_names or [])
    return [
        spell["name"]
        for spell in spells
        if class_names.intersection(spell.get("classes", [])) and spell.get("level") == level
    ]


def subclass_spell_options(spells, spellcasting, level):
    spell_list = (spellcasting or {}).get("spell_list", "")
    granted = set((spellcasting or {}).get("granted_cantrips", [])) if level == 0 else set()
    return [
        spell
        for spell in spell_options(spells, spell_list, level)
        if spell not in granted
    ]


def leveled_spell_options(spells, spellcasting, levels, class_data=None, character_level=1):
    names = []
    spell_lists = eligible_spell_lists_for_prepared_spells(class_data or {}, character_level, spellcasting)
    for level in levels:
        names.extend(spell_options_for_lists(spells, spell_lists, level))
    return merge_unique(names)


def filtered_spell_options(spells, rule):
    spell_class = rule.get("class", "")
    levels = set(rule.get("levels", []))
    school = rule.get("school", "")
    return [
        spell["name"]
        for spell in spells
        if (not spell_class or spell_class in spell.get("classes", []))
        and (not levels or spell.get("level") in levels)
        and (not school or spell.get("school_code") == school)
    ]


def render_subclass_option_controls(character, class_data, data):
    subclass_options = selected_subclass_options(class_data, character.get("subclass", ""))
    if not subclass_options:
        return False

    rendered = False
    class_options = character.setdefault("class_options", {})
    subclass_data = selected_subclass_data(class_data, character.get("subclass", ""))
    subclass_descriptions = feature_descriptions_for(data, subclass_data)

    maneuver_rule = subclass_options.get("maneuvers", {})
    if maneuver_rule:
        rendered = True
        maneuver_total = maneuver_rule.get("choose", 0)
        if class_data.get("name") == "Fighter" and character.get("subclass") == "Battle Master":
            maneuver_total = battle_master_maneuver_total(character.get("level", 1))
        current_maneuvers = [
            maneuver
            for maneuver in class_options.get("maneuvers", [])
            if maneuver in maneuver_rule.get("from", [])
        ]
        maneuver_catalog = build_optional_feature_catalog(
            optional_feature_records(
                maneuver_rule.get("options") or maneuver_rule.get("from", []),
                category="Battle Master maneuver",
            ),
            selected_names=current_maneuvers,
            selection_limit=maneuver_total,
            kind="maneuver",
        )
        selected_maneuvers = render_medium_option_browser(
            maneuver_catalog,
            current_maneuvers,
            selection_limit=maneuver_total,
            state_key=f"battle_master_maneuvers_{character.get('level', 1)}",
            label=f"Choose {maneuver_total} Battle Master maneuvers",
            search_label="Search maneuvers by name",
            filters=(BrowserFilter("Filter by status", "category", "All categories"),),
            add_label="Add maneuver",
            remove_label="Remove maneuver",
        )
        selected_maneuvers = clamp_multiselect(selected_maneuvers, maneuver_total)
        if selected_maneuvers != class_options.get("maneuvers", []):
            class_options["maneuvers"] = selected_maneuvers
            st.rerun()
        save_options = subclass_options.get("maneuver_save_ability", ["Strength", "Dexterity"])
        selected_save_ability = st.selectbox(
            "Maneuver save ability",
            save_options,
            index=optional_select_index(save_options, class_options.get("battle_master_save_ability")),
            placeholder="Choose an ability",
        )
        if selected_save_ability:
            class_options["battle_master_save_ability"] = selected_save_ability

    if "student_of_war_skill" in subclass_options:
        rendered = True
        selected_skill = class_options.get("student_of_war_skill")
        known_skills = set(character.get("skill_proficiencies", []))
        skill_options = [
            skill
            for skill in class_data.get("skill_choices", {}).get("from", [])
            if skill == selected_skill or skill not in known_skills
        ]
        if skill_options:
            selected_skill = st.selectbox(
                "Student of War skill",
                skill_options,
                index=optional_select_index(skill_options, selected_skill),
                placeholder="Choose a skill",
            )
            if selected_skill:
                class_options["student_of_war_skill"] = selected_skill
        tool_options = subclass_options.get("student_of_war_tool", {}).get("from", [])
        if tool_options:
            selected_tool = st.selectbox(
                "Student of War artisan tool",
                tool_options,
                index=optional_select_index(tool_options, class_options.get("student_of_war_tool")),
                placeholder="Choose a tool",
            )
            if selected_tool:
                class_options["student_of_war_tool"] = selected_tool

    lore_skill_rule = subclass_options.get("lore_skills", {})
    if lore_skill_rule:
        rendered = True
        current_lore_skills = [
            skill
            for skill in class_options.get("lore_skills", [])
            if skill in lore_skill_rule.get("from", [])
        ]
        lore_skill_catalog = build_skill_catalog(
            data.get("skills", []),
            lore_skill_rule.get("from", []),
            current_lore_skills,
        )
        selected_lore_skills = compact_values_choice(
            lore_skill_catalog,
            current_lore_skills,
            selection_limit=lore_skill_rule.get("choose", 0),
            state_key="subclass_lore_skills",
            label=f"Choose {lore_skill_rule.get('choose', 0)} College of Lore skills",
        )
        class_options["lore_skills"] = clamp_multiselect(selected_lore_skills, lore_skill_rule.get("choose", 0))
        if len(class_options["lore_skills"]) != lore_skill_rule.get("choose", 0):
            st.info(f"Choose {lore_skill_rule.get('choose', 0)} College of Lore skills.")

    hunters_prey_rule = subclass_options.get("hunters_prey", {})
    if hunters_prey_rule:
        rendered = True
        prey_options = hunters_prey_rule.get("from", [])
        prey_catalog = build_class_feature_choice_catalog(
            prey_options,
            selected_name=class_options.get("hunters_prey"),
            kind="feature_configuration",
            source_label=subclass_data.get("source", ""),
            description_lookup=subclass_descriptions,
            parent_description=subclass_descriptions.get("Hunter's Prey", ""),
        )
        selected_prey = compact_value_choice(
            prey_catalog,
            class_options.get("hunters_prey"),
            state_key="subclass_hunters_prey",
            label="Hunter's Prey",
            placeholder="Choose an option",
            control="segmented",
        )
        if selected_prey:
            class_options["hunters_prey"] = selected_prey

    companion_rule = subclass_options.get("primal_companion", {})
    if companion_rule:
        rendered = True
        companion_options = companion_rule.get("from", [])
        companion_catalog = build_class_feature_choice_catalog(
            companion_options,
            selected_name=class_options.get("primal_companion"),
            kind="feature_configuration",
            source_label=subclass_data.get("source", ""),
            description_lookup=subclass_descriptions,
        )
        selected_companion = compact_value_choice(
            companion_catalog,
            class_options.get("primal_companion"),
            state_key="subclass_primal_companion",
            label="Primal Companion",
            placeholder="Choose an option",
        )
        if selected_companion:
            class_options["primal_companion"] = selected_companion

    savant_rule = savant_spell_choice_rule(subclass_options, character.get("subclass", ""), 3) or subclass_options.get("savant_spells", {})
    if savant_rule:
        rendered = True
        existing_spellbook = set(character.get("spells", {}).get("spellbook", []))
        spell_options_for_rule = leveled_spell_options_for_display(
            [
                spell
                for spell in filtered_spell_options(data.get("spells", []), savant_rule.get("from", {}))
                if spell not in existing_spellbook or spell in class_options.get("savant_spells", [])
            ],
            data.get("spells", []),
        )
        current_savant = [
            spell
            for spell in class_options.get("savant_spells", [])
            if spell in spell_options_for_rule
        ]
        selected_groups = render_spell_choice_browser(
            data.get("spells", []),
            (
                SpellSelectionGroupSpec(
                    key="savant_spells",
                    label="Savant spells",
                    option_names=tuple(spell_options_for_rule),
                    selected_names=tuple(current_savant),
                    selection_limit=savant_rule.get("choose", 0),
                    add_label="Add Savant spell",
                    remove_label="Remove Savant spell",
                ),
            ),
            {"savant_spells": current_savant},
            state_key="class_option_savant_spells",
            label=savant_rule.get("label", f"Choose {savant_rule.get('choose', 0)} subclass spells"),
        )
        updated_savant = clamp_multiselect(selected_groups.get("savant_spells", current_savant), savant_rule.get("choose", 0))
        if updated_savant != class_options.get("savant_spells", []):
            class_options["savant_spells"] = updated_savant
            st.rerun()
        class_options["savant_spells"] = updated_savant
        if len(class_options["savant_spells"]) != savant_rule.get("choose", 0):
            st.info(f"Choose {savant_rule.get('choose', 0)} subclass spells.")

    for savant_level in (5, 7, 9, 11, 13, 15):
        if character.get("level", 1) < savant_level:
            continue
        rule = savant_spell_choice_rule(subclass_options, character.get("subclass", ""), savant_level)
        if not rule:
            continue
        rendered = True
        key = savant_spell_choice_key(savant_level)
        existing_spellbook = set(character.get("spells", {}).get("spellbook", []))
        selected_for_key = set(class_options.get(key, []))
        selected_savant_spells = {
            spell
            for option_key, value in class_options.items()
            if option_key == "savant_spells" or option_key.startswith("savant_spells_level_")
            for spell in (value if isinstance(value, list) else [value])
            if spell
        }
        spell_options_for_rule = leveled_spell_options_for_display(
            [
                spell
                for spell in filtered_spell_options(data.get("spells", []), rule.get("from", {}))
                if (
                    spell not in existing_spellbook
                    and spell not in selected_savant_spells
                ) or spell in selected_for_key
            ],
            data.get("spells", []),
        )
        current_savant = [
            spell
            for spell in class_options.get(key, [])
            if spell in spell_options_for_rule
        ]
        selected_groups = render_spell_choice_browser(
            data.get("spells", []),
            (
                SpellSelectionGroupSpec(
                    key=key,
                    label="Savant spells",
                    option_names=tuple(spell_options_for_rule),
                    selected_names=tuple(current_savant),
                    selection_limit=rule.get("choose", 0),
                    add_label="Add Savant spell",
                    remove_label="Remove Savant spell",
                ),
            ),
            {key: current_savant},
            state_key=f"class_option_{key}",
            label=rule.get("label", f"Choose {character.get('subclass', '')} Savant spell"),
        )
        updated_savant = clamp_multiselect(selected_groups.get(key, current_savant), rule.get("choose", 0))
        if updated_savant != class_options.get(key, []):
            class_options[key] = updated_savant
            st.rerun()
        class_options[key] = updated_savant
        if len(class_options[key]) != rule.get("choose", 0):
            st.info(f"Choose {rule.get('choose', 0)} {character.get('subclass', '')} Savant spell.")

    structured_spell_rule = subclass_options.get("structured_spell_choice", {})
    if structured_spell_rule:
        rendered = True
        options = structured_spell_rule.get("options", [])
        option_names = [option.get("name", "") for option in options if option.get("name")]
        current = class_options.get("structured_spell_choice")
        metadata_lookup = {
            option.get("name", ""): {
                "Level 1 grant": ", ".join(option.get("granted_spells", [])),
                "Later grants": "; ".join(
                    f"Level {level}: {', '.join(spells)}"
                    for level, spells in (option.get("granted_spells_by_level", {}) or {}).items()
                ),
            }
            for option in options
            if option.get("name")
        }
        description_lookup = {
            option.get("name", ""): "Granted spells: " + ", ".join(option.get("granted_spells", []))
            for option in options
            if option.get("name")
        }
        structured_catalog = build_class_feature_choice_catalog(
            option_names,
            selected_name=current,
            kind="feature_configuration",
            source_label=subclass_data.get("source", ""),
            description_lookup=description_lookup,
            metadata_lookup=metadata_lookup,
            parent_description=subclass_descriptions.get("Circle of the Land Spells", ""),
        )
        selected_group = compact_value_choice(
            structured_catalog,
            current,
            state_key="subclass_structured_spell_choice",
            label=structured_spell_rule.get("name", "Subclass spell group"),
            placeholder="Choose an option",
        )
        if selected_group:
            class_options["structured_spell_choice"] = selected_group
        selected_option = next(
            (option for option in options if option.get("name") == class_options.get("structured_spell_choice")),
            None,
        )
        if selected_option:
            st.caption("Granted spells: " + ", ".join(selected_option.get("granted_spells", [])))
        else:
            st.info(f"Choose {structured_spell_rule.get('name', 'subclass spell group')}.")

    return rendered


def render_feature_configuration_controls(character, data=None):
    configurations = character.get("feature_configurations", [])
    if not configurations:
        return False
    st.subheader("Current feature configurations")
    for config in configurations:
        options = config.get("eligible_options", [])
        current = config.get("current_value", "")
        if not options:
            continue
        if str(config.get("feature_id", "")).startswith("spell_mastery_"):
            current_selected = [current] if current in options else []
            selected_groups = render_spell_choice_browser(
                (data or {}).get("spells", []),
                (
                    SpellSelectionGroupSpec(
                        key=config.get("feature_id", ""),
                        label=config.get("feature_name", "Spell Mastery"),
                        option_names=tuple(options),
                        selected_names=tuple(current_selected),
                        selection_limit=1,
                        add_label="Add mastery spell",
                        remove_label="Remove mastery spell",
                    ),
                ),
                {config.get("feature_id", ""): current_selected},
                state_key=f"feature_config_{config.get('feature_id', '')}",
                label=config.get("feature_name", "Spell Mastery"),
            )
            selected_list = clamp_multiselect(selected_groups.get(config.get("feature_id", ""), current_selected), 1)
            selected = selected_list[0] if selected_list else ""
            if selected and selected != current:
                update_feature_configuration(character, config.get("feature_id", ""), selected)
                st.rerun()
            if selected:
                st.caption(f"Current option changes on {config.get('change_timing', 'rest').replace('_', ' ')}.")
            continue
        source = config.get("source", {})
        source_class = (data or {}).get("classes_by_name", {}).get(source.get("class_name", ""), {})
        source_subclass = selected_subclass_data(source_class, source.get("subclass_name", "")) if source_class else {}
        descriptions = feature_descriptions_for(data, source_class, source_subclass)
        labels = config.get("option_labels", {})
        metadata_lookup = {
            option: {
                "Current timing": config.get("change_timing", "rest").replace("_", " "),
                "Feature": config.get("feature_name", "Feature configuration"),
            }
            for option in options
        }
        config_catalog = build_class_feature_choice_catalog(
            options,
            selected_name=current,
            kind="feature_configuration",
            source_label=source_subclass.get("source", "") or source_class.get("source", ""),
            description_lookup=descriptions,
            metadata_lookup=metadata_lookup,
            parent_description=descriptions.get(config.get("feature_name", ""), ""),
        )
        selected = compact_value_choice(
            config_catalog,
            current,
            state_key=f"feature_config_{config.get('feature_id', '')}",
            label=config.get("feature_name", "Feature configuration"),
            placeholder="Choose an option",
        )
        if selected and selected != current:
            update_feature_configuration(character, config.get("feature_id", ""), selected)
            st.caption(f"Current option changes on {config.get('change_timing', 'rest').replace('_', ' ')}.")
    return True


def render_level_choice_control(character, choice, choice_context=None):
    data_context = choice_context_data(choice_context)
    spells = choice_context_spells(choice_context)
    if choice.get("type") == "asi_or_feat":
        render_asi_or_feat_choice(character, choice, data_context)
        return
    if choice.get("type") == "feat_selection":
        current_value = choice_current_value(choice)
        render_general_feat_choice(character, choice, current_value, data_context)
        return
    if choice.get("type") == "spell_mastery_selection":
        render_spell_mastery_choice(character, choice, spells or [])
        return
    if choice.get("type") == "subclass_choice":
        render_level_subclass_choice(character, choice, data_context)
        return

    options = choice_option_labels(choice)
    spell_lookup = spell_metadata_by_name(spells or [])
    spell_choice = is_spell_choice(choice)
    if spell_choice:
        options = sort_spell_options_by_level(options, spell_lookup)
    option_format = (
        (lambda option: spell_option_label(option, spell_lookup))
        if spell_choice
        else str
    )
    label = choice.get("name") or "Required choice"
    if not options:
        st.warning(f"{label} is required, but no options are available yet.")
        return

    if is_level_spell_picker_choice(choice):
        render_level_spell_selection_choice(character, choice, spells or [], options, label)
        return

    if choice.get("type") == "weapon_mastery_selection":
        render_level_weapon_mastery_choice(character, choice, data_context, options, label)
        return

    if is_medium_level_optional_feature_choice(choice):
        render_level_optional_feature_choice(character, choice, data_context, options, label)
        return

    if is_compact_level_single_choice(choice):
        render_level_compact_single_choice(character, choice, data_context, options, label)
        return

    if is_compact_level_multi_choice(choice):
        render_level_compact_multi_choice(character, choice, data_context, options, label)
        return

    if choice.get("type") in {
        "class_option_selection",
    }:
        selected = st.multiselect(
            label,
            options,
            default=[
                item
                for item in choice.get("value", [])
                if item in options
            ],
            max_selections=choice.get("choose", 0) or None,
            format_func=option_format,
            key=f"level_choice_{choice.get('id')}",
        )
        selected = clamp_multiselect(selected, choice.get("choose", 0))
        if resolve_pending_choice(character, choice.get("id"), selected, choice):
            st.caption("Selected: " + ", ".join(selected))
        elif selected:
            st.info(f"Choose exactly {choice.get('choose', 0)} option(s).")
        return

    current_value = choice.get("value") if choice.get("status") == "resolved" else None
    selected = st.selectbox(
        label,
        options,
        index=select_index(options, current_value) if current_value else None,
        placeholder="Choose an option",
        key=f"level_choice_{choice.get('id')}",
    )
    if selected is not None and resolve_pending_choice(character, choice.get("id"), selected, choice):
        st.caption(f"Selected: {selected}")


def is_compact_level_single_choice(choice):
    phase_three_keys = {
        "fighting_style",
        "champion_additional_fighting_styles",
        "defensive_tactics",
        "hunters_prey",
        "primal_companion",
        "structured_spell_choice",
        "elemental_affinity",
    }
    if choice.get("class_option_key") not in phase_three_keys:
        return False
    if choice.get("type") == "class_option_single":
        return True
    return choice.get("type") == "class_option_selection" and int(choice.get("choose", 0) or 0) == 1


def is_compact_level_multi_choice(choice):
    if choice.get("type") != "class_option_selection":
        return False
    return choice.get("apply_to") in {"expertise", "skill_proficiencies", "languages"} or choice.get("class_option_key") in {
        "lore_skills",
        "ranger_languages",
        "bard_expertise",
        "bard_level_9_expertise",
        "ranger_deft_explorer_expertise",
        "ranger_level_9_expertise",
        "rogue_level_6_expertise",
    }


def is_medium_level_optional_feature_choice(choice):
    return choice.get("type") == "class_option_selection" and choice.get("class_option_key") in {
        "maneuvers",
        "eldritch_invocations",
    }


def render_level_compact_multi_choice(character, choice, data_context, options, label):
    current_value = choice.get("value", []) if isinstance(choice.get("value", []), list) else []
    catalog = proficiency_choice_catalog(data_context, choice, options, current_value)
    selected = compact_values_choice(
        catalog,
        current_value,
        selection_limit=choice.get("choose", 0),
        state_key=f"level_choice_{choice.get('id')}",
        label=label,
    )
    selected = clamp_multiselect(selected, choice.get("choose", 0))
    if selected == current_value:
        return
    resolved = resolve_pending_choice(character, choice.get("id"), selected, choice)
    if resolved:
        st.rerun()
    elif selected:
        st.info(f"Choose exactly {choice.get('choose', 0)} option(s).")


def render_level_optional_feature_choice(character, choice, data_context, options, label):
    current_value = choice.get("value", []) if isinstance(choice.get("value", []), list) else []
    key = choice.get("class_option_key", "")
    base_character = character.get("base_character") or {}
    existing = base_character.get("class_options", {}).get(key, [])
    if key == "eldritch_invocations":
        class_name = character.get("class_name") or base_character.get("class", "")
        class_data = (data_context or {}).get("classes_by_name", {}).get(class_name, {})
        invocation_rule = class_data.get("class_options", {}).get("eldritch_invocations", {})
        display_character = {**base_character, "class_options": dict(base_character.get("class_options", {}))}
        display_character["class_options"][key] = merge_unique(existing, current_value)
        records = invocation_records(
            display_character,
            invocation_rule,
            character.get("target_level", base_character.get("level", 1)),
        )
        kind = "eldritch_invocation"
        search_label = "Search invocations by name"
        add_label = "Add invocation"
        remove_label = "Remove invocation"
    else:
        class_name = character.get("class_name") or base_character.get("class", "")
        class_data = (data_context or {}).get("classes_by_name", {}).get(class_name, {})
        subclass_data = selected_subclass_data(class_data, base_character.get("subclass", ""))
        maneuver_rule = subclass_data.get("subclass_options", {}).get("maneuvers", {})
        records = optional_feature_records(
            maneuver_rule.get("options") or options,
            category="Battle Master maneuver",
        )
        kind = "maneuver"
        search_label = "Search maneuvers by name"
        add_label = "Add maneuver"
        remove_label = "Remove maneuver"

    catalog = build_optional_feature_catalog(
        records,
        selected_names=current_value,
        selection_limit=choice.get("choose", 0),
        kind=kind,
        existing_names=existing,
    )
    selected = render_medium_option_browser(
        catalog,
        current_value,
        selection_limit=choice.get("choose", 0),
        state_key=f"level_optional_feature_{choice.get('id')}",
        label=label,
        search_label=search_label,
        filters=(BrowserFilter("Filter by category", "category", "All categories"),),
        add_label=add_label,
        remove_label=remove_label,
    )
    selected = clamp_multiselect(selected, choice.get("choose", 0))
    if selected == current_value:
        return
    resolved = resolve_pending_choice(character, choice.get("id"), selected, choice)
    if resolved:
        st.rerun()
    elif selected:
        st.info(f"Choose exactly {choice.get('choose', 0)} option(s).")


def render_level_weapon_mastery_choice(character, choice, data_context, options, label):
    current_value = choice.get("value", []) if isinstance(choice.get("value", []), list) else []
    existing = (character.get("base_character") or {}).get("weapon_masteries", character.get("weapon_masteries", []))
    catalog = build_weapon_mastery_catalog(
        (data_context or {}).get("weapons", []),
        eligible_names=options,
        selected_names=current_value,
        selection_limit=choice.get("choose", 0),
        mastery_descriptions=(data_context or {}).get("weapon_masteries", []),
        existing_masteries=existing,
    )
    selected = render_medium_option_browser(
        catalog,
        current_value,
        selection_limit=choice.get("choose", 0),
        state_key=f"level_weapon_mastery_{choice.get('id')}",
        label=label,
        search_label="Search weapons by name",
        filters=(
            BrowserFilter("Filter by mastery property", "mastery", "All masteries"),
            BrowserFilter("Filter by weapon category", "category", "All categories"),
        ),
        add_label="Add mastery",
        remove_label="Remove mastery",
    )
    selected = clamp_multiselect(selected, choice.get("choose", 0))
    if selected == current_value:
        return
    resolved = resolve_pending_choice(character, choice.get("id"), selected, choice)
    if resolved:
        st.rerun()
    elif selected:
        st.info(f"Choose exactly {choice.get('choose', 0)} option(s).")


def render_level_compact_single_choice(character, choice, data_context, options, label):
    current_value = choice.get("value") if "value" in choice else None
    if isinstance(current_value, list):
        current_value = current_value[0] if current_value else None
    class_data = (data_context or {}).get("classes_by_name", {}).get(character.get("class_name", ""), {})
    subclass_data = selected_subclass_data(class_data, selected_subclass_from_choice(character))
    descriptions = feature_descriptions_for(data_context, class_data, subclass_data)
    metadata_lookup = {
        option: {"Choice": label}
        for option in options
    }
    compact_options = build_class_feature_choice_catalog(
        options,
        selected_name=current_value,
        kind="level_choice",
        source_label=subclass_data.get("source", "") or class_data.get("source", ""),
        description_lookup=descriptions,
        metadata_lookup=metadata_lookup,
        parent_description=descriptions.get(level_choice_feature_name(choice, label), ""),
    )
    selected = compact_value_choice(
        compact_options,
        current_value,
        state_key=f"level_choice_{choice.get('id')}",
        label=label,
        placeholder="Choose an option",
        control="segmented" if len(options) <= 5 else "selectbox",
    )
    if not selected:
        return
    if selected == current_value:
        return
    value = [selected] if choice.get("type") == "class_option_selection" else selected
    if resolve_pending_choice(character, choice.get("id"), value, choice):
        st.rerun()
    elif value:
        st.info(f"Choose exactly {choice.get('choose', 1)} option(s).")


def selected_subclass_from_choice(character):
    for choice in character.get("pending_choices", []) or []:
        if choice.get("type") == "subclass_choice" and choice.get("status") == "resolved":
            return choice.get("value", "")
    return character.get("subclass", "")


def level_choice_feature_name(choice, fallback):
    key_names = {
        "fighting_style": "Fighting Style",
        "defensive_tactics": "Defensive Tactics",
        "hunters_prey": "Hunter's Prey",
        "structured_spell_choice": "Circle of the Land Spells",
        "blessed_strikes": "Blessed Strikes",
        "elemental_affinity": "Elemental Affinity",
    }
    return key_names.get(choice.get("class_option_key", ""), fallback.replace("Choose ", ""))


def render_level_choice_controls(character, choices, choice_context=None):
    spells = choice_context_spells(choice_context)
    rendered_spell_group = False
    spell_choices = [
        choice
        for choice in choices
        if is_level_spell_picker_choice(choice)
    ]
    spell_choice_ids = {choice.get("id") for choice in spell_choices}
    for choice in choices:
        if choice.get("id") in spell_choice_ids:
            if not rendered_spell_group:
                render_level_spell_selection_choices(character, spell_choices, spells or [])
                rendered_spell_group = True
            continue
        render_level_choice_control(character, choice, choice_context)


def render_level_subclass_choice(character, choice, data_context):
    class_name = character.get("class_name") or character.get("class")
    class_data = (data_context or {}).get("classes_by_name", {}).get(class_name, {})
    label = choice.get("name") or "Choose subclass"
    options = choice_option_labels(choice)
    if not class_data:
        selected = st.selectbox(
            label,
            options,
            index=select_index(options, choice.get("value")) if choice.get("value") in options else None,
            placeholder="Choose a subclass",
            key=f"level_choice_{choice.get('id')}",
        )
        if selected is not None and resolve_pending_choice(character, choice.get("id"), selected, choice):
            st.caption(f"Selected: {selected}")
        return

    current_value = choice.get("value") if choice.get("status") == "resolved" else None
    catalog = build_subclass_catalog(
        class_data,
        int(character.get("target_level") or character.get("level") or 0),
        current_value,
        option_names=options,
    )
    selected_id = subclass_stable_id(class_data, current_value)
    updated_id = render_subclass_choice(
        catalog,
        selected_id,
        state_key=f"level_subclass_{choice.get('id')}",
        label=label,
    )
    if updated_id == selected_id:
        return
    selected_option = next((option for option in catalog if option.stable_id == updated_id), None)
    if selected_option and resolve_pending_choice(character, choice.get("id"), option_value(selected_option), choice):
        st.rerun()


def render_level_spell_selection_choice(character, choice, spells, options, label):
    render_level_spell_selection_choices(character, [choice], spells, label=label)


def render_level_spell_selection_choices(character, choices, spells, label=None):
    choices = [
        choice
        for choice in choices or []
        if is_level_spell_picker_choice(choice)
    ]
    if not choices:
        return
    spell_lookup = spell_metadata_by_name(spells or [])
    groups = []
    selected_groups = {}
    choices_by_group = {}
    for choice in choices:
        options = sort_spell_options_by_level(choice_option_labels(choice), spell_lookup)
        if not options:
            st.warning(f"{choice.get('name') or 'Required choice'} is required, but no options are available yet.")
            continue
        group_key = choice.get("id") or choice.get("spell_field", "spell")
        group_label = level_spell_choice_group_label(choice)
        action_label = level_spell_choice_action_label(choice)
        selected = [
            item
            for item in choice.get("value", [])
            if item in options
        ]
        groups.append(SpellSelectionGroupSpec(
            key=group_key,
            label=group_label,
            option_names=tuple(options),
            selected_names=tuple(selected),
            selection_limit=choice.get("choose", 0),
            add_label=f"Add {action_label}",
            remove_label=f"Remove {action_label}",
        ))
        selected_groups[group_key] = selected
        choices_by_group[group_key] = choice
    if not groups:
        return

    catalog = build_grouped_spell_option_catalog(spells, tuple(groups), kind="spell")
    picker_label = label or combined_level_spell_choice_label(choices)
    state_id = "_".join(choice.get("id", "") for choice in choices if choice.get("id"))
    updated_groups = render_unified_spell_picker(
        catalog,
        selected_groups,
        state_key=f"level_spell_choices_{state_id}",
        label=picker_label,
    )
    changed = False
    for group_key, choice in choices_by_group.items():
        selected = selected_groups.get(group_key, [])
        updated = updated_groups.get(group_key, selected)
        if updated == selected:
            continue
        resolved = resolve_pending_choice(character, choice.get("id"), updated, choice)
        if not resolved and updated:
            st.info(f"Choose exactly {choice.get('choose', 0)} option(s).")
        changed = True
    if changed:
        st.rerun()

    for group_key, choice in choices_by_group.items():
        selected = selected_groups.get(group_key, [])
        if choice.get("status") == "resolved" and selected:
            st.caption(f"{level_spell_choice_group_label(choice)} selected: " + ", ".join(selected))


def level_spell_choice_group_label(choice):
    if choice.get("type") == "feat_spell_selection":
        return "Feat spells"
    if choice.get("type") == "signature_spells_selection":
        return "Signature spells"
    if choice.get("type") == "spellbook_spells":
        return "Spellbook spells"
    if choice.get("type") == "class_option_selection" and is_spell_choice(choice):
        return choice.get("name", "Spell choice")
    field = choice.get("spell_field", "spell")
    field_labels = {
        "cantrips": "Cantrips",
        "known": "Known spells",
        "prepared": "Prepared spells",
        "spellbook": "Spellbook spells",
    }
    return field_labels.get(field, field.replace("_", " ").title())


def level_spell_choice_action_label(choice):
    if choice.get("type") == "feat_spell_selection":
        return "feat spell"
    if choice.get("type") == "signature_spells_selection":
        return "signature spell"
    if choice.get("type") == "spellbook_spells":
        return "spellbook spell"
    if choice.get("type") == "class_option_selection" and is_spell_choice(choice):
        return "spell"
    field = choice.get("spell_field", "spell")
    singular_labels = {
        "cantrips": "cantrip",
        "known": "known spell",
        "prepared": "prepared spell",
        "spellbook": "spellbook spell",
    }
    return singular_labels.get(field, "spell")


def combined_level_spell_choice_label(choices):
    if len(choices) == 1:
        return choices[0].get("name") or "Choose spell"
    labels = [level_spell_choice_group_label(choice).lower() for choice in choices]
    return "Choose level-up " + " and ".join(labels)


def is_level_spell_picker_choice(choice):
    return (
        choice.get("type") in {
            "spell_selection",
            "spellbook_spells",
            "feat_spell_selection",
            "signature_spells_selection",
        }
        or (choice.get("type") == "class_option_selection" and is_spell_choice(choice))
    )


def render_asi_or_feat_choice(character, choice, data_context=None):
    current_value = choice_current_value(choice)
    current_mode = "General feat" if current_value.get("mode") == "feat" else "Ability scores"
    selected_mode = st.segmented_control(
        choice.get("name", "Ability Score Improvement or general feat"),
        ["Ability scores", "General feat"],
        default=current_mode,
        key=f"asi_or_feat_mode_{choice.get('id')}",
    )
    if selected_mode == "General feat":
        render_general_feat_choice(character, choice, current_value, data_context)
    else:
        render_ability_score_increase_choice(character, choice, current_value)


def choice_current_value(choice):
    value = choice.get("value", {})
    return value if isinstance(value, dict) else {}


def render_ability_score_increase_choice(character, choice, current_value):
    current_increases = current_value.get("ability_increases", {}) if current_value.get("mode") == "asi" else {}
    current_style = "+2 to one ability" if 2 in current_increases.values() else "+1 to two abilities"
    style = st.segmented_control(
        "Increase type",
        ["+2 to one ability", "+1 to two abilities"],
        default=current_style,
        key=f"asi_style_{choice.get('id')}",
    )
    if style == "+2 to one ability":
        current_ability = next((ability for ability, amount in current_increases.items() if amount == 2), None)
        selected_ability = st.selectbox(
            "Ability",
            ABILITIES,
            index=select_index(ABILITIES, current_ability) if current_ability else None,
            placeholder="Choose an ability",
            key=f"asi_single_{choice.get('id')}",
        )
        value = {
            "mode": "asi",
            "ability_increases": {selected_ability: 2} if selected_ability else {},
        }
    else:
        current_abilities = [
            ability
            for ability, amount in current_increases.items()
            if amount == 1 and ability in ABILITIES
        ]
        selected_abilities = st.multiselect(
            "Abilities",
            ABILITIES,
            default=current_abilities[:2],
            max_selections=2,
            key=f"asi_split_{choice.get('id')}",
        )
        value = {
            "mode": "asi",
            "ability_increases": {ability: 1 for ability in selected_abilities},
        }
    if resolve_pending_choice(character, choice.get("id"), value, choice):
        st.caption("Selected: " + format_asi_value(value))
    elif value.get("ability_increases"):
        st.info("Choose +2 to one ability or +1 to two abilities without going above 20.")


def render_general_feat_choice(character, choice, current_value, data_context=None):
    feat_options = choice.get("feat_options", [])
    if not feat_options:
        st.warning("No eligible general feats are available for this character.")
        return

    current_feat_id = current_value.get("feat_id", "")
    feat_catalog = build_feat_catalog(choice.get("feat_candidates") or feat_options, selected_feat_id=current_feat_id)
    selected_feat_id = render_medium_single_option_browser(
        feat_catalog,
        current_feat_id,
        state_key=f"general_feat_{choice.get('id')}",
        label=choice.get("feat_label", "General feat"),
        search_label="Search feats by name",
        filters=(
            BrowserFilter("Filter by category", "category", "All categories"),
            BrowserFilter("Filter by choice support", "choice_support", "All support statuses"),
        ),
        choose_label="Choose feat",
        clear_label="Clear feat",
    )
    selected_feat = next(
        (
            feat
            for feat in feat_options
            if feat.get("id") == selected_feat_id
        ),
        {},
    )
    if not selected_feat:
        return

    active_current_value = current_value if selected_feat_id == current_feat_id else {}
    ability_choice = ""
    ability_increase = selected_feat.get("ability_increase", {})
    if ability_increase.get("mode") == "choose":
        ability_options = ability_increase.get("from", [])
        current_ability = active_current_value.get("feat_ability_choice", "")
        ability_choice = st.selectbox(
            "Ability increase",
            ability_options,
            index=select_index(ability_options, current_ability) if current_ability in ability_options else None,
            placeholder="Choose an ability",
            key=f"general_feat_ability_{choice.get('id')}",
        )
    elif ability_increase.get("mode") == "fixed":
        fixed_ability = next(iter(ability_increase.get("from", [])), "")
        amount = ability_increase.get("amount", 1)
        if fixed_ability:
            st.caption(f"Ability increase: {fixed_ability} +{amount}")

    current_feat_choices = active_current_value.get("feat_choices", {})
    feat_choices = render_feat_extra_choices(choice, selected_feat, current_feat_choices, data_context or {})
    value = {
        "mode": "feat",
        "feat_id": selected_feat.get("id", ""),
        "feat_name": selected_feat.get("name", ""),
        "feat_ability_choice": ability_choice or "",
        "feat_choices": feat_choices,
    }
    if resolve_pending_choice(character, choice.get("id"), value, choice):
        st.caption("Selected: " + selected_feat.get("name", ""))
    elif selected_feat:
        st.info("Choose the feat's required options before finalizing.")
    if feat_choices != current_feat_choices:
        st.rerun()


def render_spell_mastery_choice(character, choice, spells):
    current_value = choice.get("value", {}) if isinstance(choice.get("value", {}), dict) else {}
    spell_lookup = spell_metadata_by_name(spells)
    level_1_options = sort_spell_options_by_level(choice.get("level_1_options", []), spell_lookup)
    level_2_options = sort_spell_options_by_level(choice.get("level_2_options", []), spell_lookup)

    if not level_1_options or not level_2_options:
        st.warning("Spell Mastery needs one eligible level 1 and one eligible level 2 Wizard spell in your spellbook.")
        return

    current_level_1 = [current_value.get("level_1", "")] if current_value.get("level_1") in level_1_options else []
    current_level_2 = [current_value.get("level_2", "")] if current_value.get("level_2") in level_2_options else []
    selected_groups = render_spell_choice_browser(
        spells,
        (
            SpellSelectionGroupSpec(
                key="level_1",
                label="Level 1 Spell Mastery",
                option_names=tuple(level_1_options),
                selected_names=tuple(current_level_1),
                selection_limit=1,
                add_label="Add level 1 mastery spell",
                remove_label="Remove level 1 mastery spell",
            ),
            SpellSelectionGroupSpec(
                key="level_2",
                label="Level 2 Spell Mastery",
                option_names=tuple(level_2_options),
                selected_names=tuple(current_level_2),
                selection_limit=1,
                add_label="Add level 2 mastery spell",
                remove_label="Remove level 2 mastery spell",
            ),
        ),
        {
            "level_1": current_level_1,
            "level_2": current_level_2,
        },
        state_key=f"spell_mastery_{choice.get('id')}",
        label="Choose Spell Mastery spells",
    )
    level_1_selection = clamp_multiselect(selected_groups.get("level_1", current_level_1), 1)
    level_2_selection = clamp_multiselect(selected_groups.get("level_2", current_level_2), 1)
    level_1 = level_1_selection[0] if level_1_selection else ""
    level_2 = level_2_selection[0] if level_2_selection else ""
    value = {"level_1": level_1 or "", "level_2": level_2 or ""}
    if value != current_value:
        resolve_pending_choice(character, choice.get("id"), value, choice)
        st.rerun()
    if choice.get("status") == "resolved":
        st.caption(f"Selected: {level_1}, {level_2}")
    elif level_1 or level_2:
        st.info("Choose one eligible level 1 spell and one eligible level 2 spell.")


def render_feat_extra_choices(choice, selected_feat, current_choices, data_context=None):
    rendered_choices = {}
    spell_lookup = spell_metadata_by_name(choice.get("spells", []))
    for field in selected_feat.get("choice_schema", []):
        field_id = field.get("id", "")
        options = list(field.get("options", []))
        field_is_spell = field_id in {"spell", "spells"}
        if field_is_spell:
            options = sort_spell_options_by_level(options, spell_lookup)
        if selected_feat.get("name") == "Skill Expert" and field_id == "expertise":
            selected_skill = rendered_choices.get("skill_proficiency") or current_choices.get("skill_proficiency", "")
            if selected_skill and selected_skill not in options:
                options.append(selected_skill)
        if not options:
            st.warning(f"No valid {field.get('label', 'choice').lower()} options are available.")
            continue
        current_value = current_choices.get(field_id, "")
        if field_is_spell:
            current_selected = [
                item
                for item in (current_value if isinstance(current_value, list) else [current_value])
                if item in options
            ]
            limit = int(field.get("choose", 0) or (1 if field.get("type") != "multi" else 0))
            group_key = field_id
            selected_groups = render_spell_choice_browser(
                choice.get("spells", []),
                (
                    SpellSelectionGroupSpec(
                        key=group_key,
                        label=field.get("label", "Spells"),
                        option_names=tuple(options),
                        selected_names=tuple(current_selected),
                        selection_limit=limit,
                        add_label="Add spell",
                        remove_label="Remove spell",
                    ),
                ),
                {group_key: current_selected},
                state_key=f"general_feat_choice_{choice.get('id')}_{selected_feat.get('id')}_{field_id}",
                label=field.get("label", "Choose spell"),
            )
            selected_list = clamp_multiselect(selected_groups.get(group_key, current_selected), limit)
            selected_value = selected_list if field.get("type") == "multi" else (selected_list[0] if selected_list else "")
        elif field_id in {"skill", "skill_proficiency", "expertise"}:
            current_selected = current_value if isinstance(current_value, list) else ([current_value] if current_value else [])
            skill_catalog = build_skill_catalog(
                (data_context or {}).get("skills", []),
                options,
                [item for item in current_selected if item in options],
                kind="expertise" if field_id == "expertise" else "skill",
            )
            if field.get("type") == "multi":
                selected_value = compact_values_choice(
                    skill_catalog,
                    current_selected,
                    selection_limit=int(field.get("choose", 0) or 0),
                    state_key=f"general_feat_choice_{choice.get('id')}_{selected_feat.get('id')}_{field_id}",
                    label=field.get("label", "Choice"),
                )
            else:
                selected_value = compact_value_choice(
                    skill_catalog,
                    current_value,
                    state_key=f"general_feat_choice_{choice.get('id')}_{selected_feat.get('id')}_{field_id}",
                    label=field.get("label", "Choice"),
                    placeholder=f"Choose {field.get('label', 'an option').lower()}",
                )
        elif field.get("type") == "multi":
            selected_value = st.multiselect(
                field.get("label", "Choice"),
                options,
                default=[item for item in current_value if item in options] if isinstance(current_value, list) else [],
                max_selections=int(field.get("choose", 0) or 0),
                placeholder=f"Choose {field.get('label', 'options').lower()}",
                format_func=(lambda option: spell_option_label(option, spell_lookup)) if field_is_spell else str,
                key=f"general_feat_choice_{choice.get('id')}_{selected_feat.get('id')}_{field_id}",
            )
        else:
            selected_value = st.selectbox(
                field.get("label", "Choice"),
                options,
                index=select_index(options, current_value) if current_value in options else None,
                placeholder=f"Choose {field.get('label', 'an option').lower()}",
                format_func=(lambda option: spell_option_label(option, spell_lookup)) if field_is_spell else str,
                key=f"general_feat_choice_{choice.get('id')}_{selected_feat.get('id')}_{field_id}",
            )
        if selected_value:
            rendered_choices[field_id] = selected_value
    return rendered_choices


def format_asi_value(value):
    increases = value.get("ability_increases", {})
    return ", ".join(f"{ability} +{amount}" for ability, amount in increases.items())


def render_feature_details(features):
    if not features:
        st.write("None")
        return
    for feature in features:
        name = feature.get("name", "")
        description = feature.get("description", "")
        related_features = feature.get("related_features", [])
        if description:
            with st.expander(name):
                st.write(description)
                for related in related_features:
                    label = related.get("name", "")
                    if related.get("cost"):
                        label = f"{label} - Cost: {related['cost']}"
                    if related.get("description"):
                        st.write(f"**{label}:** {related['description']}")
                    elif label:
                        st.write(f"**{label}**")
        else:
            st.write(f"**{name}**")
            for related in related_features:
                label = related.get("name", "")
                if related.get("cost"):
                    label = f"{label} - Cost: {related['cost']}"
                if label:
                    st.write(f"- {label}")


def format_history_items(items):
    if not items:
        return ""
    formatted = []
    for item in items:
        if isinstance(item, dict):
            name = item.get("name") or item.get("type") or "Choice"
            value = format_level_choice_value(item)
            formatted.append(f"{name}: {value}" if value else name)
        else:
            formatted.append(str(item))
    return ", ".join(formatted)


def format_level_choice_value(choice):
    value = choice.get("value", "")
    if choice.get("type") == "asi_or_feat" and isinstance(value, dict):
        if value.get("mode") == "asi":
            return "ASI: " + format_asi_value(value)
        if value.get("mode") == "feat":
            return "Feat: " + value.get("feat_name", "")
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        return ", ".join(f"{key}: {item}" for key, item in value.items() if item)
    return value


def level_history_rows(history):
    rows = []
    for entry in history:
        rows.append({
            "Class": entry.get("class", ""),
            "From": entry.get("from_level", ""),
            "To": entry.get("to_level", ""),
            "HP increase": entry.get("hp_increase", ""),
            "Automatic gains": format_history_items(entry.get("automatic_features", [])),
            "Resolved choices": format_history_items(
                entry.get("resolved_choices", entry.get("pending_choices", []))
            ),
        })
    return rows


def magic_initiate_class(feat_name):
    if "(" not in feat_name:
        return ""
    return feat_name.split("(", 1)[1].split(")", 1)[0]


def all_origin_feats(data):
    return data.get("rules", {}).get("origin_feats", [])


def all_skill_names(data):
    return list(data.get("rules", {}).get("skills", {}).keys())


def tool_options():
    return [
        "Any artisan's tools",
        "Any gaming set",
        "Any musical instrument",
        "Any other tool",
    ]


def spell_details(spells, names):
    selected = [spell for spell in spells if spell["name"] in names]
    if selected:
        st.dataframe(
            [
                {
                    "Spell": spell["name"],
                    "Level": "Cantrip" if spell["level"] == 0 else spell["level"],
                    "School": spell["school"],
                    "Casting Time": spell["casting_time"],
                    "Range": spell["range"],
                    "Duration": spell["duration"],
                }
                for spell in selected
            ],
            hide_index=True,
            width="stretch",
        )
        render_spell_descriptions(
            [
                {
                    "name": spell["name"],
                    "description": spell.get("description", ""),
                }
                for spell in selected
            ]
        )


def render_spell_descriptions(spells):
    spells_with_descriptions = [
        spell
        for spell in spells
        if spell.get("name") and spell.get("description")
    ]
    if not spells_with_descriptions:
        return
    for spell in spells_with_descriptions:
        with st.expander(spell["name"]):
            st.write(spell["description"])


def render_sheet_spells(sheet):
    spells = sheet.get("spells", {})
    by_level = normalized_spell_groups(sheet)
    if not any(by_level.values()):
        st.write("None")
        return

    if by_level.get(0):
        st.write("**Cantrips:** " + ", ".join(by_level[0]))
    for level in range(1, 10):
        if by_level.get(level):
            st.write(f"**Level {level}:** " + ", ".join(by_level[level]))
    if by_level.get("unknown"):
        st.write("**Unknown level:** " + ", ".join(by_level["unknown"]))
    if spells.get("spellbook"):
        st.write("**Spellbook:** " + ", ".join(spells["spellbook"]))
    if spells.get("prepared"):
        prepared_limit = spells.get("prepared_limit", 0)
        label = f"Prepared ({len(spells['prepared'])}/{prepared_limit})" if prepared_limit else "Prepared"
        st.write(f"**{label}:** " + ", ".join(spells["prepared"]))
    if spells.get("spellcasting_sources"):
        st.write("**Spellcasting sources**")
        st.dataframe(
            [
                {
                    "Source": source.get("source_name", ""),
                    "Ability": source.get("ability", ""),
                    "Save DC": source.get("spell_save_dc", ""),
                    "Attack Bonus": format_modifier(source.get("spell_attack_bonus", 0)),
                }
                for source in spells.get("spellcasting_sources", [])
            ],
            hide_index=True,
            width="stretch",
        )

    granted = [
        spell
        for spell in spells.get("granted", [])
        if spell not in spells.get("cantrips", [])
    ]
    if granted:
        st.caption("Species, subclass, and feat spells are included in the level groups above.")
    render_spell_descriptions(sheet.get("spell_details", []))


def format_feat_choices(choices):
    parts = []
    for key, value in choices.items():
        label = key.replace("_", " ").title()
        if isinstance(value, list):
            value = ", ".join(str(item) for item in value if item)
        if value:
            parts.append(f"{label}: {value}")
    return "; ".join(parts) or "-"


def normalized_spell_groups(sheet):
    groups = {level: [] for level in range(0, 10)}
    groups["unknown"] = []
    raw_groups = sheet.get("spells", {}).get("by_level", {})
    if raw_groups:
        for level, spells in raw_groups.items():
            key = int(level) if str(level).isdigit() else "unknown"
            groups.setdefault(key, [])
            groups[key].extend(spell for spell in spells if spell not in groups[key])
        return groups

    details_by_name = {
        detail.get("name"): detail
        for detail in sheet.get("spell_details", [])
    }
    spells = sheet.get("spells", {})
    for spell in (
        list(spells.get("cantrips", []))
        + list(spells.get("spellbook", []))
        + list(spells.get("prepared", []))
        + list(spells.get("known", []))
        + list(spells.get("granted", []))
    ):
        if not spell:
            continue
        level = details_by_name.get(spell, {}).get("level")
        key = level if isinstance(level, int) else "unknown"
        if spell not in groups.setdefault(key, []):
            groups[key].append(spell)
    return groups


def render_score_cards(character):
    cols = st.columns(6)
    for index, ability in enumerate(ABILITIES):
        with cols[index]:
            st.metric(
                ability[:3].upper(),
                character["ability_scores"][ability],
                format_modifier(character["ability_modifiers"].get(ability, 0)),
            )


def render_bonus_table(title, bonuses, proficiencies=None, expertise=None):
    proficiencies = set(proficiencies or [])
    expertise = set(expertise or [])
    st.subheader(title)
    st.dataframe(
        [
            {
                "Name": name,
                "Bonus": format_modifier(bonus),
                "Proficient": "Yes" if name in proficiencies else "",
                "Expertise": "Yes" if name in expertise else "",
            }
            for name, bonus in bonuses.items()
        ],
        hide_index=True,
        width="stretch",
    )


def render_origin_feat_controls(character, data):
    feats = active_origin_feats(character)
    choices = character.setdefault("origin_feat_choices", {
        "skills": [],
        "tools": [],
        "cantrips": [],
        "spell": "",
        "spellcasting_ability": "",
    })

    if not feats:
        return

    st.subheader("Origin Feat Choices")
    st.write(", ".join(feats))

    if "Skilled" in feats:
        combined_options = [f"Skill: {skill}" for skill in all_skill_names(data)] + [f"Tool: {tool}" for tool in tool_options()]
        current = [f"Skill: {skill}" for skill in choices.get("skills", [])] + [f"Tool: {tool}" for tool in choices.get("tools", [])]
        skilled_catalog = build_prefixed_skill_tool_catalog(
            data.get("skills", []),
            all_skill_names(data),
            tool_options(),
            [item for item in current if item in combined_options],
        )
        selected = compact_values_choice(
            skilled_catalog,
            [item for item in current if item in combined_options],
            selection_limit=3,
            state_key="origin_feat_skilled",
            label="Skilled: choose any combination of 3 skills or tools",
        )
        selected = clamp_multiselect(selected, 3)
        choices["skills"] = [item.removeprefix("Skill: ") for item in selected if item.startswith("Skill: ")]
        choices["tools"] = [item.removeprefix("Tool: ") for item in selected if item.startswith("Tool: ")]

    if "Crafter" in feats:
        artisan_tools = [
            "Carpenter's Tools",
            "Leatherworker's Tools",
            "Mason's Tools",
            "Potter's Tools",
            "Smith's Tools",
            "Tinker's Tools",
            "Weaver's Tools",
            "Woodcarver's Tools",
        ]
        current_crafter_tools = [tool for tool in choices.get("tools", []) if tool in artisan_tools]
        crafter_catalog = build_tool_catalog(
            artisan_tools,
            current_crafter_tools,
            category="Artisan's Tool",
            source_label="XPHB",
        )
        selected_crafter_tools = compact_values_choice(
            crafter_catalog,
            current_crafter_tools,
            selection_limit=3,
            state_key="origin_feat_crafter_tools",
            label="Crafter: choose 3 artisan tools",
        )
        choices["tools"] = merge_unique(
            [tool for tool in choices.get("tools", []) if tool not in artisan_tools],
            clamp_multiselect(selected_crafter_tools, 3),
        )

    if "Musician" in feats:
        instruments = ["Bagpipes", "Drum", "Dulcimer", "Flute", "Horn", "Lute", "Lyre", "Pan Flute", "Shawm", "Viol"]
        current_instruments = [tool for tool in choices.get("tools", []) if tool in instruments]
        musician_catalog = build_tool_catalog(
            instruments,
            current_instruments,
            category="Musical Instrument",
            source_label="XPHB",
        )
        selected_instruments = compact_values_choice(
            musician_catalog,
            current_instruments,
            selection_limit=3,
            state_key="origin_feat_musician_instruments",
            label="Musician: choose 3 musical instruments",
        )
        choices["tools"] = merge_unique(
            [tool for tool in choices.get("tools", []) if tool not in instruments],
            clamp_multiselect(selected_instruments, 3),
        )

    magic_feats = [feat for feat in feats if feat.startswith("Magic Initiate")]
    if magic_feats:
        feat = magic_feats[0]
        spell_class = magic_initiate_class(feat)
        cantrips = leveled_spell_options_for_display(spell_options(data["spells"], spell_class, 0), data["spells"])
        level_one_spells = leveled_spell_options_for_display(spell_options(data["spells"], spell_class, 1), data["spells"])
        current_cantrips = [spell for spell in choices.get("cantrips", []) if spell in cantrips]
        current_spell = [choices.get("spell", "")] if choices.get("spell") in level_one_spells else []
        spell_groups = [
            SpellSelectionGroupSpec(
                key="cantrips",
                label="Cantrips",
                option_names=tuple(cantrips),
                selected_names=tuple(current_cantrips),
                selection_limit=2,
                add_label="Add cantrip",
                remove_label="Remove cantrip",
            )
        ]
        selected_groups = {"cantrips": current_cantrips}
        if level_one_spells:
            spell_groups.append(SpellSelectionGroupSpec(
                key="spell",
                label="Level 1 spell",
                option_names=tuple(level_one_spells),
                selected_names=tuple(current_spell),
                selection_limit=1,
                add_label="Add Level 1 spell",
                remove_label="Remove Level 1 spell",
            ))
            selected_groups["spell"] = current_spell
        updated_groups = render_spell_choice_browser(
            data["spells"],
            tuple(spell_groups),
            selected_groups,
            state_key=f"origin_{feat.lower().replace(' ', '_')}_spells",
            label=f"{feat}: choose 2 cantrips and 1 Level 1 spell",
        )
        updated_cantrips = clamp_multiselect(updated_groups.get("cantrips", current_cantrips), 2)
        updated_spell_list = clamp_multiselect(updated_groups.get("spell", current_spell), 1)
        updated_spell = updated_spell_list[0] if updated_spell_list else ""
        if updated_cantrips != choices.get("cantrips", []) or updated_spell != choices.get("spell", ""):
            choices["cantrips"] = updated_cantrips
            choices["spell"] = updated_spell
            st.rerun()
        choices["cantrips"] = updated_cantrips
        choices["spell"] = updated_spell
        abilities = ["Intelligence", "Wisdom", "Charisma"]
        choices["spellcasting_ability"] = st.selectbox(
            f"{feat}: spellcasting ability",
            abilities,
            index=optional_select_index(abilities, choices.get("spellcasting_ability")),
            placeholder="Choose an ability",
        )


def render_background_summary(background_data):
    if not background_data:
        return
    with st.container(border=True):
        st.markdown(f"**{background_data.get('name', 'Background')}**")
        ability_options = background_data.get("ability_options", {})
        if ability_options.get("abilities"):
            st.write("**Abilities:** " + ", ".join(ability_options.get("abilities", [])))
        if background_data.get("skill_proficiencies"):
            st.write("**Skills:** " + ", ".join(background_data.get("skill_proficiencies", [])))
        tools = merge_unique(background_data.get("tool_proficiencies", []), background_data.get("tool_choices", {}).get("from", []))
        if tools:
            st.write("**Tools:** " + ", ".join(tools))
        if background_data.get("origin_feats"):
            st.write("**Origin feat:** " + ", ".join(background_data.get("origin_feats", [])))
        if background_data.get("equipment_packages"):
            st.caption(f"{len(background_data.get('equipment_packages', []))} equipment package option(s)")


def render_class_summary(class_data):
    if not class_data:
        return
    with st.container(border=True):
        st.markdown(f"**{class_data.get('name', 'Class')}**")
        if class_data.get("hit_die"):
            st.write(f"**Hit Die:** d{class_data.get('hit_die')}")
        if class_data.get("primary_ability"):
            st.write("**Primary abilities:** " + ", ".join(class_data.get("primary_ability", [])))
        if class_data.get("saving_throw_proficiencies"):
            st.write("**Saving throws:** " + ", ".join(class_data.get("saving_throw_proficiencies", [])))
        armor = class_data.get("armor_proficiencies", [])
        weapons = class_data.get("weapon_proficiencies", [])
        if armor:
            st.write("**Armor:** " + ", ".join(armor))
        if weapons:
            st.write("**Weapons:** " + ", ".join(weapons))
        if class_data.get("level_1_features"):
            st.write("**Level 1 features:** " + ", ".join(class_data.get("level_1_features", [])))
        st.caption("Spellcasting: " + ("Yes" if class_data.get("spellcasting") else "No"))


def main():
    initialize_session()
    data_sources = available_data_sources()
    default_source = FIVETOOLS_SOURCE if FIVETOOLS_SOURCE in data_sources else SAMPLE_SOURCE
    source_name = st.sidebar.radio(
        "Data source",
        data_sources,
        index=select_index(data_sources, st.session_state.get("data_source", default_source)),
    )
    if source_name != st.session_state.get("data_source"):
        st.session_state.data_source = source_name
        clear_ability_score_widgets()
        st.session_state.character = new_character()
        st.session_state.level_up_draft = None
        st.rerun()

    data = load_app_data(source_name)
    character = st.session_state.character

    st.title("D&D 5e 2024 Character Builder")
    st.caption(f"Local Streamlit MVP using {source_name}.")
    if source_name == FIVETOOLS_SOURCE:
        metadata = data.get("metadata", {})
        st.sidebar.caption(
            "Imported sources: "
            + ", ".join(metadata.get("sources", []))
        )

    class_data = data["classes_by_name"].get(character.get("class"), {})
    recalculate_character(character, data)

    tabs = st.tabs([
        "Basic Info",
        "Species",
        "Background",
        "Class",
        "Ability Scores",
        "Proficiencies",
        "Class Options",
        "Spells",
        "Equipment",
        "Level Up",
        "Character Sheet",
        "Save / Load",
    ])

    with tabs[0]:
        left, right = st.columns([2, 1])
        with left:
            character["name"] = st.text_input("Character name", value=character.get("name", ""))
            character["notes"] = st.text_area("Notes", value=character.get("notes", ""), height=120)
        with right:
            recalculate_character(character, data)
            st.metric("Level", character["level"])
            st.metric("Proficiency Bonus", format_modifier(character["proficiency_bonus"]))

    with tabs[1]:
        species_names = [item["name"] for item in data["species"]]
        previous_species = character.get("species")
        selected_species = st.selectbox(
            "Species",
            species_names,
            index=optional_select_index(species_names, character.get("species")),
            placeholder="Choose a species",
        )
        if selected_species is None:
            st.info("Choose a species to see species traits and options.")
        elif selected_species != previous_species:
            change_species(character, selected_species)
        else:
            character["species"] = selected_species
        if selected_species:
            species_data = data["species_by_name"][selected_species]
            st.write(f"**Size:** {species_data['size']}")
            st.write(f"**Speed:** {species_data['speed']} feet")
            st.write("**Languages:** " + ", ".join(species_data.get("languages", [])))
            st.write("**Traits:** " + ", ".join(species_data.get("traits", [])))

            species_choice = species_data.get("choice_options")
            if species_choice:
                current_choice = character.get("species_options", {}).get(species_choice["key"])
                species_catalog = build_species_choice_catalog(
                    species_data,
                    species_choice,
                    current_choice,
                )
                selected_choice = compact_value_choice(
                    species_catalog,
                    current_choice,
                    state_key=f"species_choice_{species_choice.get('key', '')}",
                    label=species_choice["name"],
                    placeholder="Choose an option",
                    control="segmented" if len(species_choice.get("options", [])) <= 5 else "selectbox",
                )
                if selected_choice:
                    character.setdefault("species_options", {})[species_choice["key"]] = selected_choice

            if "Versatile" in species_data.get("traits", []):
                origin_feats = all_origin_feats(data)
                current_feat = next(iter(character.get("species_options", {}).get("origin_feats", [])), None)
                selected_feat = st.selectbox(
                    "Versatile: choose an Origin feat",
                    origin_feats,
                    index=optional_select_index(origin_feats, current_feat),
                    placeholder="Choose an Origin feat",
                )
                if selected_feat:
                    change_origin_feat(character, selected_feat)

            skill_choice = species_data.get("skill_choices", {})
            if skill_choice.get("choose", 0):
                current_species_skills = [
                    skill
                    for skill in character.get("species_options", {}).get("skill_proficiencies", [])
                    if skill in skill_choice.get("from", [])
                ]
                species_skill_catalog = build_skill_catalog(
                    data.get("skills", []),
                    skill_choice.get("from", []),
                    current_species_skills,
                )
                selected_species_skills = compact_values_choice(
                    species_skill_catalog,
                    current_species_skills,
                    selection_limit=skill_choice["choose"],
                    state_key=f"species_skills_{selected_species}",
                    label=f"Choose {skill_choice['choose']} species skill",
                )
                character.setdefault("species_options", {})["skill_proficiencies"] = clamp_multiselect(
                    selected_species_skills,
                    skill_choice["choose"],
                )

            lineage_options = species_data.get("lineage_options", [])
            if lineage_options:
                current_lineage = character.get("species_options", {}).get("lineage")
                lineage_catalog = build_lineage_catalog(species_data, current_lineage)
                selected_lineage = compact_value_choice(
                    lineage_catalog,
                    current_lineage,
                    state_key=f"species_lineage_{selected_species}",
                    label="Lineage",
                    placeholder="Choose a lineage",
                    control="segmented" if len(lineage_options) <= 5 else "selectbox",
                )
                if selected_lineage is None:
                    st.info("Choose a lineage to apply lineage benefits.")
                else:
                    lineage_data = next(item for item in lineage_options if item["name"] == selected_lineage)
                    character.setdefault("species_options", {})["lineage"] = selected_lineage
                    character["species_options"]["lineage_spells"] = lineage_data.get("level_1_spells", [])
                    if lineage_data.get("spellcasting_abilities"):
                        current_ability = character["species_options"].get("lineage_spellcasting_ability")
                        selected_ability = st.selectbox(
                            "Lineage spellcasting ability",
                            lineage_data["spellcasting_abilities"],
                            index=optional_select_index(lineage_data["spellcasting_abilities"], current_ability),
                            placeholder="Choose an ability",
                        )
                        if selected_ability:
                            character["species_options"]["lineage_spellcasting_ability"] = selected_ability

    with tabs[2]:
        background_names = [item["name"] for item in data["backgrounds"]]
        previous_background = character.get("background")
        selected_background = st.selectbox(
            "Background",
            background_names,
            index=optional_select_index(background_names, character.get("background")),
            placeholder="Choose a background",
        )
        if selected_background is None:
            st.info("Choose a background to see background benefits and ability bonuses.")
            background_data = {}
        elif selected_background != previous_background:
            change_background(character, selected_background)
        else:
            character["background"] = selected_background
        if selected_background:
            background_data = data["backgrounds_by_name"][selected_background]
        else:
            background_data = {}
        render_background_summary(background_data)

        ability_options = background_data.get("ability_options", {})
        if ability_options.get("mode") == "choose_weighted":
            abilities = ability_options.get("abilities", [])
            primary_bonus = ability_options.get("primary_bonus", 2)
            secondary_bonus = ability_options.get("secondary_bonus", 1)
            col_a, col_b = st.columns(2)
            with col_a:
                selected_primary = st.selectbox(
                    f"+{primary_bonus} ability",
                    abilities,
                    index=optional_select_index(abilities, character.get("background_options", {}).get("primary_ability")),
                    placeholder="Choose an ability",
                )
                if selected_primary:
                    character.setdefault("background_options", {})["primary_ability"] = selected_primary
            secondary_options = [
                ability
                for ability in abilities
                if ability != character.get("background_options", {}).get("primary_ability")
            ]
            with col_b:
                selected_secondary = st.selectbox(
                    f"+{secondary_bonus} ability",
                    secondary_options,
                    index=optional_select_index(secondary_options, character.get("background_options", {}).get("secondary_ability")),
                    placeholder="Choose an ability",
                )
                if selected_secondary:
                    character["background_options"]["secondary_ability"] = selected_secondary

        tool_choice = background_data.get("tool_choices", {})
        if tool_choice.get("choose", 0):
            current_tools = [
                tool
                for tool in character.get("background_options", {}).get("tool_proficiencies", [])
                if tool in tool_choice.get("from", [])
            ]
            tool_catalog = build_tool_catalog(
                tool_choice.get("from", []),
                current_tools,
                category="Tool",
                source_label=background_data.get("source", ""),
            )
            selected_tools = compact_values_choice(
                tool_catalog,
                current_tools,
                selection_limit=tool_choice["choose"],
                state_key=f"background_tools_{selected_background}",
                label=f"Choose {tool_choice['choose']} tool proficiency",
            )
            character.setdefault("background_options", {})["tool_proficiencies"] = clamp_multiselect(
                selected_tools,
                tool_choice["choose"],
            )

        recalculate_character(character, data)
        render_origin_feat_controls(character, data)

    with tabs[3]:
        class_names = [item["name"] for item in data["classes"]]
        previous_class = character.get("class")
        selected_class = st.selectbox(
            "Class",
            class_names,
            index=optional_select_index(class_names, character.get("class")),
            placeholder="Choose a class",
        )
        if selected_class is None:
            st.info("Choose a class to see class features and options.")
            class_data = {}
        elif selected_class != previous_class:
            change_character_class(character, selected_class)
        else:
            character["class"] = selected_class
        if selected_class:
            class_data = data["classes_by_name"][selected_class]
            render_class_summary(class_data)
            feature_rows = [
                {
                    "Level": level,
                    "Features": ", ".join(class_features_at_level(class_data, level)) or "None",
                }
                for level in range(1, character.get("level", 1) + 1)
            ]
            st.write(f"**Class features through level {character.get('level', 1)}:**")
            st.dataframe(feature_rows, hide_index=True, width="stretch")

    with tabs[4]:
        st.write("Choose base scores before background bonuses.")
        current_method = character.get("ability_score_method", "Manual entry")
        character["ability_score_method"] = score_method_control(
            "Score method",
            ABILITY_SCORE_METHODS,
            current_method,
        )

        if character["ability_score_method"] == "Standard array":
            st.caption("Standard array: " + ", ".join(str(score) for score in STANDARD_ARRAY))
            if st.button("Reset standard array assignment", icon=":material/check:"):
                reset_score_assignments(character, STANDARD_ARRAY)
            render_score_assignment_controls(character, STANDARD_ARRAY)
        elif character["ability_score_method"] == "Roll 4d6":
            rolled_scores = character.get("rolled_ability_scores", [])
            if rolled_scores:
                st.caption("Current roll: " + ", ".join(str(score) for score in rolled_scores))
            if st.button("Roll and apply scores", icon=":material/casino:"):
                rolled_scores = roll_ability_scores()
                character["rolled_ability_scores"] = rolled_scores
                reset_score_assignments(character, rolled_scores)
                st.success("Rolled: " + ", ".join(str(score) for score in rolled_scores))
            if rolled_scores:
                render_score_assignment_controls(character, rolled_scores)
            else:
                st.info("Roll scores to generate a score pool.")
        else:
            ensure_ability_score_widgets(character)
            cols = st.columns(3)
            for index, ability in enumerate(ABILITIES):
                with cols[index % 3]:
                    character.setdefault("base_ability_scores", {}).setdefault(ability, character["ability_scores"].get(ability, 10))
                    character["base_ability_scores"][ability] = int(st.number_input(
                        ability,
                        min_value=1,
                        max_value=30,
                        step=1,
                        key=ability_score_widget_key(ability),
                    ))
        recalculate_character(character, data)
        render_score_cards(character)
        if any(character.get("ability_score_bonuses", {}).values()):
            st.write("**Background bonuses:**")
            st.dataframe(
                [
                    {
                        "Ability": ability,
                        "Base": character["base_ability_scores"][ability],
                        "Bonus": format_modifier(character["ability_score_bonuses"][ability]),
                        "Final": character["ability_scores"][ability],
                    }
                    for ability in ABILITIES
                ],
                hide_index=True,
                width="stretch",
            )

    with tabs[5]:
        background_data = data["backgrounds_by_name"].get(character.get("background"), {})
        class_data = data["classes_by_name"].get(character.get("class"), {})
        background_skills = background_data.get("skill_proficiencies", [])
        st.write("**Background skills:** " + (", ".join(background_skills) or "None"))

        skill_rule = class_data.get("skill_choices", {})
        class_options = available_class_skill_options(class_data, background_skills)
        class_skill_limit = skill_rule.get("choose", 0)
        class_skill_catalog = build_skill_catalog(
            data.get("skills", []),
            class_options,
            [
                skill
                for skill in character.get("class_options", {}).get("class_skills", [])
                if skill in class_options
            ],
        )
        selected_class_skills = compact_values_choice(
            class_skill_catalog,
            character.get("class_options", {}).get("class_skills", []),
            selection_limit=class_skill_limit,
            state_key=f"class_skills_{character.get('class', '')}",
            label=f"Choose {class_skill_limit} class skills",
        )
        selected_class_skills = clamp_multiselect(selected_class_skills, class_skill_limit)
        character.setdefault("class_options", {})["class_skills"] = selected_class_skills
        recalculate_character(character, data)

        if len(selected_class_skills) != class_skill_limit:
            st.info(f"{character.get('class') or 'This class'} needs exactly {class_skill_limit} class skill choices.")
        if background_skills:
            st.caption("Skills already granted by your background are excluded from class skill options.")

        render_bonus_table(
            "Skill Bonuses",
            character["skill_bonuses"],
            character["skill_proficiencies"],
            character.get("expertise", []),
        )
        render_bonus_table(
            "Saving Throws",
            character["saving_throw_bonuses"],
            character["saving_throw_proficiencies"],
        )

    with tabs[6]:
        class_data = data["classes_by_name"].get(character.get("class"), {})
        options = class_data.get("class_options", {})
        rendered_subclass_options = render_subclass_option_controls(character, class_data, data)
        fighting_styles = fighting_style_options(data, character.get("class", "")) if "fighting_style" in options else []
        if fighting_styles:
            current = character["class_options"].get("fighting_style")
            fighting_style_metadata = {
                style: {
                    "Follow-up choice": (
                        "Choose 2 Cleric cantrips" if style == "Blessed Warrior"
                        else "Choose 2 Druid cantrips" if style == "Druidic Warrior"
                        else "None"
                    )
                }
                for style in fighting_styles
            }
            fighting_style_catalog = build_class_feature_choice_catalog(
                fighting_styles,
                selected_name=current,
                kind="fighting_style",
                source_label="XPHB",
                description_lookup=feature_descriptions_for(data, class_data),
                metadata_lookup=fighting_style_metadata,
            )
            selected_style = compact_value_choice(
                fighting_style_catalog,
                current,
                state_key=f"class_fighting_style_{character.get('class', '')}",
                label="Fighting Style",
                placeholder="Choose a Fighting Style",
            )
            if selected_style:
                character["class_options"]["fighting_style"] = selected_style
            if character["class_options"].get("fighting_style") == "Blessed Warrior":
                cleric_cantrips = leveled_spell_options_for_display(cantrip_options(data, "Cleric"), data["spells"])
                current = [
                    spell
                    for spell in character["class_options"].get("blessed_warrior_cantrips", [])
                    if spell in cleric_cantrips
                ]
                selected_groups = render_spell_choice_browser(
                    data["spells"],
                    (
                        SpellSelectionGroupSpec(
                            key="blessed_warrior_cantrips",
                            label="Blessed Warrior cantrips",
                            option_names=tuple(cleric_cantrips),
                            selected_names=tuple(current),
                            selection_limit=2,
                            add_label="Add cantrip",
                            remove_label="Remove cantrip",
                        ),
                    ),
                    {"blessed_warrior_cantrips": current},
                    state_key="blessed_warrior_cantrips",
                    label="Blessed Warrior: choose 2 Cleric cantrips",
                )
                selected = clamp_multiselect(selected_groups.get("blessed_warrior_cantrips", current), 2)
                if selected != character["class_options"].get("blessed_warrior_cantrips", []):
                    character["class_options"]["blessed_warrior_cantrips"] = selected
                    st.rerun()
                character["class_options"]["blessed_warrior_cantrips"] = selected
            else:
                character["class_options"]["blessed_warrior_cantrips"] = []
            if character["class_options"].get("fighting_style") == "Druidic Warrior":
                druid_cantrips = leveled_spell_options_for_display(cantrip_options(data, "Druid"), data["spells"])
                current = [
                    spell
                    for spell in character["class_options"].get("druidic_warrior_cantrips", [])
                    if spell in druid_cantrips
                ]
                selected_groups = render_spell_choice_browser(
                    data["spells"],
                    (
                        SpellSelectionGroupSpec(
                            key="druidic_warrior_cantrips",
                            label="Druidic Warrior cantrips",
                            option_names=tuple(druid_cantrips),
                            selected_names=tuple(current),
                            selection_limit=2,
                            add_label="Add cantrip",
                            remove_label="Remove cantrip",
                        ),
                    ),
                    {"druidic_warrior_cantrips": current},
                    state_key="druidic_warrior_cantrips",
                    label="Druidic Warrior: choose 2 Druid cantrips",
                )
                selected = clamp_multiselect(selected_groups.get("druidic_warrior_cantrips", current), 2)
                if selected != character["class_options"].get("druidic_warrior_cantrips", []):
                    character["class_options"]["druidic_warrior_cantrips"] = selected
                    st.rerun()
                character["class_options"]["druidic_warrior_cantrips"] = selected
            else:
                character["class_options"]["druidic_warrior_cantrips"] = []
        if "divine_order" in options:
            current = character["class_options"].get("divine_order")
            divine_metadata = {
                "Protector": {"Consequence": "Martial weapon proficiency and Heavy Armor training"},
                "Thaumaturge": {"Follow-up choice": "Choose one extra Cleric cantrip"},
            }
            divine_catalog = build_class_feature_choice_catalog(
                options["divine_order"],
                selected_name=current,
                kind="class_order",
                source_label=class_data.get("source", ""),
                description_lookup=feature_descriptions_for(data, class_data),
                related_features=related_features_for(class_data, "Divine Order"),
                metadata_lookup=divine_metadata,
                parent_description=class_data.get("feature_descriptions", {}).get("Divine Order", ""),
            )
            selected_order = compact_value_choice(
                divine_catalog,
                current,
                state_key="class_divine_order",
                label="Divine Order",
                placeholder="Choose Divine Order",
                control="segmented",
            )
            if selected_order:
                character["class_options"]["divine_order"] = selected_order
            if character["class_options"].get("divine_order") == "Thaumaturge":
                cleric_cantrips = leveled_spell_options_for_display(spell_options(data["spells"], "Cleric", 0), data["spells"])
                current = [
                    spell
                    for spell in character["class_options"].get("extra_cantrips", [])
                    if spell in cleric_cantrips
                ][:1]
                selected_groups = render_spell_choice_browser(
                    data["spells"],
                    (
                        SpellSelectionGroupSpec(
                            key="extra_cantrips",
                            label="Extra cantrip",
                            option_names=tuple(cleric_cantrips),
                            selected_names=tuple(current),
                            selection_limit=1,
                            add_label="Add cantrip",
                            remove_label="Remove cantrip",
                        ),
                    ),
                    {"extra_cantrips": current},
                    state_key="thaumaturge_extra_cantrip",
                    label="Thaumaturge: choose one extra Cleric cantrip",
                )
                selected = clamp_multiselect(selected_groups.get("extra_cantrips", current), 1)
                if selected != character["class_options"].get("extra_cantrips", []):
                    character["class_options"]["extra_cantrips"] = selected
                    st.rerun()
                character["class_options"]["extra_cantrips"] = selected
            elif character["class_options"].get("extra_cantrips"):
                character["class_options"]["extra_cantrips"] = []
        if "primal_order" in options:
            current = character["class_options"].get("primal_order")
            primal_metadata = {
                "Magician": {"Follow-up choice": "Choose one extra Druid cantrip"},
                "Warden": {"Consequence": "Martial weapon proficiency and Medium Armor training"},
            }
            primal_catalog = build_class_feature_choice_catalog(
                options["primal_order"],
                selected_name=current,
                kind="class_order",
                source_label=class_data.get("source", ""),
                description_lookup=feature_descriptions_for(data, class_data),
                related_features=related_features_for(class_data, "Primal Order"),
                metadata_lookup=primal_metadata,
                parent_description=class_data.get("feature_descriptions", {}).get("Primal Order", ""),
            )
            selected_order = compact_value_choice(
                primal_catalog,
                current,
                state_key="class_primal_order",
                label="Primal Order",
                placeholder="Choose Primal Order",
                control="segmented",
            )
            if selected_order:
                character["class_options"]["primal_order"] = selected_order
            if character["class_options"].get("primal_order") == "Magician":
                druid_cantrips = leveled_spell_options_for_display(spell_options(data["spells"], "Druid", 0), data["spells"])
                current = [
                    spell
                    for spell in character["class_options"].get("extra_cantrips", [])
                    if spell in druid_cantrips
                ][:1]
                selected_groups = render_spell_choice_browser(
                    data["spells"],
                    (
                        SpellSelectionGroupSpec(
                            key="extra_cantrips",
                            label="Extra cantrip",
                            option_names=tuple(druid_cantrips),
                            selected_names=tuple(current),
                            selection_limit=1,
                            add_label="Add cantrip",
                            remove_label="Remove cantrip",
                        ),
                    ),
                    {"extra_cantrips": current},
                    state_key="magician_extra_cantrip",
                    label="Magician: choose one extra Druid cantrip",
                )
                selected = clamp_multiselect(selected_groups.get("extra_cantrips", current), 1)
                if selected != character["class_options"].get("extra_cantrips", []):
                    character["class_options"]["extra_cantrips"] = selected
                    st.rerun()
                character["class_options"]["extra_cantrips"] = selected
            elif character["class_options"].get("extra_cantrips"):
                character["class_options"]["extra_cantrips"] = []
        if "expertise" in options:
            expertise_rule = options["expertise"]
            expertise_options = character.get("skill_proficiencies", [])
            current_expertise = [skill for skill in character.get("expertise", []) if skill in expertise_options]
            expertise_catalog = build_skill_catalog(
                data.get("skills", []),
                expertise_options,
                current_expertise,
                kind="expertise",
            )
            selected_expertise = compact_values_choice(
                expertise_catalog,
                current_expertise,
                selection_limit=expertise_rule.get("choose", 0),
                state_key=f"class_expertise_{character.get('class', '')}",
                label=f"Choose {expertise_rule.get('choose', 0)} expertise skills",
            )
            character["expertise"] = clamp_multiselect(selected_expertise, expertise_rule.get("choose", 0))
            if len(character["expertise"]) != expertise_rule.get("choose", 0):
                st.info("Rogue expertise applies double proficiency to two proficient skills.")
        if character.get("class") == "Rogue":
            current = character["class_options"].get("rogue_thieves_cant_language")
            known_languages = set(character.get("languages", [])) - {current}
            language_options = [language for language in LANGUAGE_OPTIONS if language not in known_languages]
            selected_language = st.selectbox(
                "Thieves' Cant: choose one additional language",
                language_options,
                index=optional_select_index(language_options, current),
                placeholder="Choose a language",
            )
            if selected_language:
                character["class_options"]["rogue_thieves_cant_language"] = selected_language
        if "eldritch_invocations" in options:
            invocation_rule = options["eldritch_invocations"]
            invocation_count = get_class_resources(class_data, character.get("level", 1)).get(
                "eldritch_invocations",
                invocation_rule.get("choose", 0),
            )
            invocation_options = eligible_invocation_names(character, invocation_rule, character.get("level", 1))
            current_invocations = [
                invocation
                for invocation in character.get("class_options", {}).get("eldritch_invocations", [])
                if invocation
            ]
            invocation_catalog = build_optional_feature_catalog(
                invocation_records(character, invocation_rule, character.get("level", 1)),
                selected_names=current_invocations,
                selection_limit=invocation_count,
                kind="eldritch_invocation",
            )
            selected_invocations = render_medium_option_browser(
                invocation_catalog,
                current_invocations,
                selection_limit=invocation_count,
                state_key=f"eldritch_invocations_{character.get('level', 1)}",
                label=f"Choose {invocation_count} Eldritch Invocation",
                search_label="Search invocations by name",
                filters=(BrowserFilter("Filter by category", "category", "All categories"),),
                add_label="Add invocation",
                remove_label="Remove invocation",
            )
            selected_invocations = clamp_multiselect(selected_invocations, invocation_count)
            if selected_invocations != character["class_options"].get("eldritch_invocations", []):
                character["class_options"]["eldritch_invocations"] = selected_invocations
                st.rerun()
        mastery_count = get_class_resources(class_data, character.get("level", 1)).get("weapon_mastery_count", 0)
        if mastery_count:
            weapon_names = eligible_weapon_mastery_names(character, data.get("weapons", []))
            current_masteries = character.get("weapon_masteries", [])
            mastery_catalog = build_weapon_mastery_catalog(
                data.get("weapons", []),
                eligible_names=weapon_names,
                selected_names=current_masteries,
                selection_limit=mastery_count,
                mastery_descriptions=data.get("weapon_masteries", []),
            )
            selected_masteries = render_medium_option_browser(
                mastery_catalog,
                current_masteries,
                selection_limit=mastery_count,
                state_key=f"class_weapon_mastery_{character.get('class', '')}_{character.get('level', 1)}",
                label=f"Choose {mastery_count} Weapon Mastery weapons",
                search_label="Search weapons by name",
                filters=(
                    BrowserFilter("Filter by mastery property", "mastery", "All masteries"),
                    BrowserFilter("Filter by weapon category", "category", "All categories"),
                ),
                add_label="Add mastery",
                remove_label="Remove mastery",
            )
            selected_masteries = clamp_multiselect(selected_masteries, mastery_count)
            if selected_masteries != current_masteries:
                character["weapon_masteries"] = selected_masteries
                st.rerun()
        rendered_configurations = render_feature_configuration_controls(character, data)
        if not rendered_subclass_options and not rendered_configurations and not options and not mastery_count:
            st.info("No extra class choices for this character right now.")

    with tabs[7]:
        class_data = data["classes_by_name"].get(character.get("class"), {})
        spellcasting = effective_spellcasting(class_data, character.get("subclass", ""), character.get("level", 1))
        subclass_data = selected_subclass_data(class_data, character.get("subclass", ""))
        active_subclass_grants = get_active_subclass_grants(subclass_data, character.get("level", 1))
        granted_spells = merge_unique(
            spell_grants(character),
            spellcasting.get("granted_cantrips", []) if spellcasting else [],
            active_subclass_grants.get("granted_cantrips", []),
            active_subclass_grants.get("always_known_spells", []),
            active_subclass_grants.get("always_prepared_spells", []),
            selected_structured_subclass_spells(character, subclass_data),
        )
        if not spellcasting:
            st.info("No spell choices required for this class.")
        else:
            cantrip_limit = spellcasting.get("cantrips_known", 0)
            cantrip_names = leveled_spell_options_for_display(
                subclass_spell_options(data["spells"], spellcasting, 0),
                data["spells"],
            )
            available_spell_levels = get_available_spell_levels(class_data, character.get("level", 1)) or [1]
            leveled_spell_names = leveled_spell_options_for_display(
                leveled_spell_options(data["spells"], spellcasting, available_spell_levels, class_data, character.get("level", 1)),
                data["spells"],
            )
            character.setdefault("spells", {}).setdefault("spellbook", [])
            if uses_spellbook_prepared_control(spellcasting) and character["spells"].get("known"):
                character["spells"]["spellbook"] = merge_unique(
                    character["spells"].get("spellbook", []),
                    character["spells"].get("known", []),
                )
                character["spells"]["known"] = []
            if "known_spells" in spellcasting:
                known_limit = spellcasting["known_spells"]
                spell_picker_options = build_grouped_spell_option_catalog(
                    data["spells"],
                    (
                        SpellSelectionGroupSpec(
                            key="cantrips",
                            label="Cantrips",
                            option_names=tuple(cantrip_names),
                            selected_names=tuple(character["spells"].get("cantrips", [])),
                            selection_limit=cantrip_limit,
                            add_label="Add cantrip",
                            remove_label="Remove cantrip",
                        ),
                        SpellSelectionGroupSpec(
                            key="known",
                            label="Known spells",
                            option_names=tuple(leveled_spell_names),
                            selected_names=tuple(character["spells"].get("known", [])),
                            selection_limit=known_limit,
                            add_label="Add known spell",
                            remove_label="Remove known spell",
                        ),
                    ),
                    kind="spell",
                )
                spell_picker_selections = render_unified_spell_picker(
                    spell_picker_options,
                    {
                        "cantrips": character["spells"].get("cantrips", []),
                        "known": character["spells"].get("known", []),
                    },
                    state_key="initial_spell_picker",
                    label=f"Choose {cantrip_limit} cantrips and {known_limit} known spells",
                )
                if (
                    spell_picker_selections.get("cantrips", []) != character["spells"].get("cantrips", [])
                    or spell_picker_selections.get("known", []) != character["spells"].get("known", [])
                ):
                    character["spells"]["cantrips"] = spell_picker_selections.get("cantrips", [])
                    character["spells"]["known"] = spell_picker_selections.get("known", [])
                    character["spells"]["prepared"] = []
                    st.rerun()
                character["spells"]["cantrips"] = spell_picker_selections.get("cantrips", [])
                character["spells"]["known"] = spell_picker_selections.get("known", [])
                character["spells"]["prepared"] = []
            elif uses_spellbook_prepared_control(spellcasting):
                spellbook_limit = spellcasting["spellbook_spells"]
                spell_picker_options = build_grouped_spell_option_catalog(
                    data["spells"],
                    (
                        SpellSelectionGroupSpec(
                            key="cantrips",
                            label="Cantrips",
                            option_names=tuple(cantrip_names),
                            selected_names=tuple(character["spells"].get("cantrips", [])),
                            selection_limit=cantrip_limit,
                            add_label="Add cantrip",
                            remove_label="Remove cantrip",
                        ),
                        SpellSelectionGroupSpec(
                            key="spellbook",
                            label="Spellbook spells",
                            option_names=tuple(leveled_spell_names),
                            selected_names=tuple(character["spells"].get("spellbook", [])),
                            selection_limit=spellbook_limit,
                            add_label="Add spellbook spell",
                            remove_label="Remove spellbook spell",
                        ),
                    ),
                    kind="spell",
                )
                spell_picker_selections = render_unified_spell_picker(
                    spell_picker_options,
                    {
                        "cantrips": character["spells"].get("cantrips", []),
                        "spellbook": character["spells"].get("spellbook", []),
                    },
                    state_key="initial_spellbook_spell_picker",
                    label=f"Choose {cantrip_limit} cantrips and {spellbook_limit} Wizard spellbook spells",
                )
                if (
                    spell_picker_selections.get("cantrips", []) != character["spells"].get("cantrips", [])
                    or spell_picker_selections.get("spellbook", []) != character["spells"].get("spellbook", [])
                ):
                    character["spells"]["cantrips"] = spell_picker_selections.get("cantrips", [])
                    character["spells"]["spellbook"] = spell_picker_selections.get("spellbook", [])
                    character["spells"]["known"] = []
                    st.rerun()
                character["spells"]["cantrips"] = spell_picker_selections.get("cantrips", [])
                character["spells"]["spellbook"] = spell_picker_selections.get("spellbook", [])
                character["spells"]["known"] = []
            elif uses_generic_prepared_control(spellcasting):
                prepared_limit = spellcasting["prepared_spells"]
                spell_picker_options = build_grouped_spell_option_catalog(
                    data["spells"],
                    (
                        SpellSelectionGroupSpec(
                            key="cantrips",
                            label="Cantrips",
                            option_names=tuple(cantrip_names),
                            selected_names=tuple(character["spells"].get("cantrips", [])),
                            selection_limit=cantrip_limit,
                            add_label="Add cantrip",
                            remove_label="Remove cantrip",
                        ),
                        SpellSelectionGroupSpec(
                            key="prepared",
                            label="Prepared spells",
                            option_names=tuple(leveled_spell_names),
                            selected_names=tuple(character["spells"].get("prepared", [])),
                            selection_limit=prepared_limit,
                            add_label="Add prepared spell",
                            remove_label="Remove prepared spell",
                        ),
                    ),
                    kind="spell",
                )
                spell_picker_selections = render_unified_spell_picker(
                    spell_picker_options,
                    {
                        "cantrips": character["spells"].get("cantrips", []),
                        "prepared": character["spells"].get("prepared", []),
                    },
                    state_key="initial_prepared_spell_picker",
                    label=f"Choose {cantrip_limit} cantrips and {prepared_limit} prepared spells",
                )
                if (
                    spell_picker_selections.get("cantrips", []) != character["spells"].get("cantrips", [])
                    or spell_picker_selections.get("prepared", []) != character["spells"].get("prepared", [])
                ):
                    character["spells"]["cantrips"] = spell_picker_selections.get("cantrips", [])
                    character["spells"]["prepared"] = spell_picker_selections.get("prepared", [])
                    character["spells"]["known"] = []
                    st.rerun()
                character["spells"]["cantrips"] = spell_picker_selections.get("cantrips", [])
                character["spells"]["prepared"] = spell_picker_selections.get("prepared", [])
                character["spells"]["known"] = []
            else:
                cantrip_options_catalog = build_spell_option_catalog(
                    data["spells"],
                    cantrip_names,
                    character["spells"].get("cantrips", []),
                    kind="cantrip",
                    selection_limit=cantrip_limit,
                )
                browser_cantrips = render_spell_option_browser(
                    cantrip_options_catalog,
                    character["spells"].get("cantrips", []),
                    selection_limit=cantrip_limit,
                    state_key="initial_cantrip_browser",
                    label=f"Choose {cantrip_limit} cantrips",
                )
                if browser_cantrips != character["spells"].get("cantrips", []):
                    character["spells"]["cantrips"] = browser_cantrips
                    st.rerun()
                character["spells"]["cantrips"] = browser_cantrips
            if uses_spellbook_prepared_control(spellcasting):
                character["spells"]["known"] = []
                prepared_limit = spellcasting.get("prepared_spells", 0)
                spellbook_options = selected_spell_options_for_display(
                    character["spells"].get("spellbook", []),
                    data["spells"],
                )
                current_prepared = [
                    spell
                    for spell in character["spells"].get("prepared", [])
                    if spell in spellbook_options
                ]
                selected_groups = render_spell_choice_browser(
                    data["spells"],
                    (
                        SpellSelectionGroupSpec(
                            key="prepared",
                            label="Prepared spells",
                            option_names=tuple(spellbook_options),
                            selected_names=tuple(current_prepared),
                            selection_limit=prepared_limit,
                            add_label="Add prepared spell",
                            remove_label="Remove prepared spell",
                        ),
                    ),
                    {"prepared": current_prepared},
                    state_key="wizard_prepared_spells",
                    label=f"Choose up to {prepared_limit} prepared Wizard spells",
                )
                selected_prepared = clamp_multiselect(selected_groups.get("prepared", current_prepared), prepared_limit)
                if selected_prepared != character["spells"].get("prepared", []):
                    character["spells"]["prepared"] = selected_prepared
                    st.rerun()
                character["spells"]["prepared"] = selected_prepared
            elif "known_spells" in spellcasting or uses_generic_prepared_control(spellcasting):
                pass

            st.write(f"**Spellcasting ability:** {spellcasting['ability']}")
            spell_details(
                data["spells"],
                character["spells"].get("cantrips", [])
                + character["spells"].get("spellbook", [])
                + character["spells"].get("known", [])
                + character["spells"].get("prepared", []),
            )
        if granted_spells:
            st.subheader("Granted spells")
            st.write(", ".join(granted_spells))
            spell_details(data["spells"], granted_spells)

    with tabs[8]:
        class_data = data["classes_by_name"].get(character.get("class"), {})
        background_data = data["backgrounds_by_name"].get(character.get("background"), {})
        sync_equipment_state(character, class_data, background_data)
        class_packages = class_data.get("equipment_packages", [])
        background_packages = background_data.get("equipment_packages", [])
        class_package_names = [package["name"] for package in class_packages]
        background_package_names = [package["name"] for package in background_packages]

        if class_package_names:
            current_class_package = character.get("class_options", {}).get("equipment_package")
            class_package_catalog = build_equipment_package_catalog(
                class_packages,
                current_class_package,
                source_label=character.get("class", "Class"),
            )
            selected_class_package = compact_value_choice(
                class_package_catalog,
                current_class_package,
                state_key=f"class_equipment_package_{character.get('class', '')}",
                label="Class equipment package",
                placeholder="Choose a class package",
            )
            if selected_class_package:
                character.setdefault("class_options", {})["equipment_package"] = selected_class_package
                sync_equipment_state(character, class_data, background_data)
        else:
            selected_class_package = None

        if background_package_names:
            current_background_package = character.get("background_options", {}).get("equipment_package")
            background_package_catalog = build_equipment_package_catalog(
                background_packages,
                current_background_package,
                source_label=character.get("background", "Background"),
            )
            selected_background_package = compact_value_choice(
                background_package_catalog,
                current_background_package,
                state_key=f"background_equipment_package_{character.get('background', '')}",
                label="Background equipment package",
                placeholder="Choose a background package",
            )
            if selected_background_package:
                character.setdefault("background_options", {})["equipment_package"] = selected_background_package
                sync_equipment_state(character, class_data, background_data)
        else:
            selected_background_package = None

        include_defaults = st.checkbox(
            "Include default class and background equipment",
            value=character.get("include_default_equipment", True),
            key="include_default_equipment",
        )
        if include_defaults != character.get("include_default_equipment", True):
            character["include_default_equipment"] = include_defaults
            sync_equipment_state(character, class_data, background_data)
            st.rerun()
        character["include_default_equipment"] = include_defaults

        package_equipment = selected_default_equipment(character, class_data, background_data)
        if package_equipment:
            with st.expander("Default equipment included", expanded=False):
                st.write(", ".join(package_equipment))
        else:
            st.caption("No default package equipment is currently included.")

        equipment_catalog = build_equipment_catalog(
            data["equipment"],
            character.get("custom_equipment", []),
            package_equipment,
        )
        custom_equipment = render_equipment_browser(
            equipment_catalog,
            character.get("custom_equipment", []),
            state_key="custom_equipment",
        )
        if custom_equipment != character.get("custom_equipment", []):
            character["custom_equipment"] = custom_equipment
            sync_equipment_state(character, class_data, background_data)
            st.rerun()
        character["equipment"] = derive_equipment(character, class_data, background_data)
        recalculate_character(character, data)

    with tabs[9]:
        recalculate_character(character, data)
        current_level = character.get("level", 1)
        st.metric("Current level", current_level)
        next_level = current_level + 1
        target_options = [next_level] if next_level in SUPPORTED_LEVELS else []
        if not target_options:
            st.info(f"This MVP currently supports levels {min(SUPPORTED_LEVELS)} to {max(SUPPORTED_LEVELS)}.")
        else:
            target_level = st.selectbox("Target level", target_options)
            draft = st.session_state.get("level_up_draft")
            if draft and (
                draft.get("current_level") != current_level
                or draft.get("class_name") != character.get("class", "")
            ):
                st.warning("The active level-up draft no longer matches this character. Start a new draft.")
                if st.button("Discard stale draft"):
                    st.session_state.level_up_draft = None
                    st.rerun()
                draft = None

            if not draft:
                if st.button("Start level up", type="primary", icon=":material/play_arrow:"):
                    st.session_state.level_up_draft = create_level_up_draft(character, target_level, data)
                    st.rerun()
                st.info("Start a level-up draft to preview changes and make required choices.")
            else:
                refresh_level_up_draft_choices(character, draft, data)
                if draft.get("blocked_reason"):
                    st.warning(draft["blocked_reason"])
                summary_cols = st.columns(4)
                summary_cols[0].metric("Target level", draft["target_level"])
                summary_cols[1].metric("HP increase", draft["hp_increase"])
                summary_cols[2].metric("Proficiency before", format_modifier(draft["proficiency_bonus_before"]))
                summary_cols[3].metric("Proficiency after", format_modifier(draft["proficiency_bonus_after"]))

                automatic_features = draft.get("automatic_features", [])
                st.subheader("Automatic gains")
                if automatic_features:
                    st.dataframe(
                        [
                            {
                                "Level": feature["level"],
                                "Source": feature["source"],
                                "Feature": feature["name"],
                            }
                            for feature in automatic_features
                        ],
                        hide_index=True,
                        width="stretch",
                    )
                else:
                    st.write("None")

                pending_choices = draft.get("pending_choices", [])
                st.subheader("Required choices")
                if pending_choices:
                    before_choice_ids = {choice.get("id") for choice in pending_choices}
                    render_level_choice_controls(draft, pending_choices, data)
                    refresh_level_up_draft_choices(character, draft, data)
                    after_choice_ids = {
                        choice.get("id")
                        for choice in draft.get("pending_choices", [])
                    }
                    if after_choice_ids != before_choice_ids:
                        st.rerun()
                else:
                    st.write("None")

                validation = validate_level_up_plan(character, draft, data) if draft.get("can_finalize") else {"ok": False}
                if pending_choices and not draft["can_finalize"]:
                    st.info("Resolve the required choice before finalizing this level.")
                if validation.get("message") and draft.get("can_finalize") and not validation.get("ok"):
                    st.warning(validation["message"])

                action_cols = st.columns(2)
                with action_cols[0]:
                    if st.button(
                        "Finalize level up",
                        type="primary",
                        icon=":material/arrow_upward:",
                        disabled=not draft["can_finalize"] or not validation.get("ok", False),
                    ):
                        result = commit_level_up_draft(character, draft, data)
                        if result["ok"]:
                            st.session_state.level_up_draft = None
                            recalculate_character(character, data)
                            st.success(f"{character.get('name') or 'Character'} is now level {character['level']}.")
                            st.rerun()
                        else:
                            st.error(result["message"])
                with action_cols[1]:
                    if st.button("Cancel level up", icon=":material/cancel:"):
                        st.session_state.level_up_draft = None
                        st.info("Level-up draft canceled.")
                        st.rerun()

        if character.get("level_history"):
            st.subheader("Level history")
            st.dataframe(level_history_rows(character["level_history"]), hide_index=True, width="stretch")
        if character.get("pending_choices"):
            st.subheader("Pending choices")
            st.dataframe(character["pending_choices"], hide_index=True, width="stretch")

    with tabs[10]:
        recalculate_character(character, data)
        validation = build_validation_report(
            character,
            data["classes_by_name"].get(character.get("class"), {}),
            data["species_by_name"].get(character.get("species"), {}),
            data["backgrounds_by_name"].get(character.get("background"), {}),
            data["spells"],
            data["weapons"],
        )
        sheet = build_character_sheet(character, data)
        if validation["missing"]:
            st.warning("Still needed: " + "; ".join(validation["missing"]))
        elif validation["unsupported"]:
            st.warning("Unsupported: " + "; ".join(validation["unsupported"]))
        else:
            st.success("Character is ready to save.")
        if validation["warnings"]:
            st.info("Notes: " + "; ".join(validation["warnings"]))

        render_score_cards(character)
        top = st.columns(5)
        top[0].metric("HP", sheet["core_stats"]["hit_points"]["max"])
        top[1].metric("AC", sheet["core_stats"]["armor_class"])
        top[2].metric("Initiative", sheet["core_stats"]["initiative_display"])
        top[3].metric("Speed", f"{sheet['identity']['speed']} ft")
        top[4].metric("Hit Die", sheet["core_stats"]["hit_die"] or "-")
        ac_details = sheet["core_stats"].get("armor_class_details", {})
        if ac_details.get("source_name"):
            shield_note = " with shield" if ac_details.get("shield_applied") else ""
            st.caption(f"AC source: {ac_details['source_name']}{shield_note}")

        st.subheader("Identity")
        st.write(
            f"**{sheet['identity']['name'] or 'Unnamed'}**, Level {sheet['identity']['level']} "
            f"{sheet['identity']['species'] or 'Unknown Species'} "
            f"{sheet['identity']['class'] or 'Unknown Class'}"
        )
        st.write(f"**Background:** {sheet['identity']['background'] or 'None'}")
        st.write(f"**Size:** {sheet['identity']['size'] or 'Unknown'}")

        left, right = st.columns(2)
        with left:
            render_bonus_table(
                "Saving Throws",
                character["saving_throw_bonuses"],
                character["saving_throw_proficiencies"],
            )
        with right:
            render_bonus_table(
                "Skills",
                character["skill_bonuses"],
                character["skill_proficiencies"],
                character.get("expertise", []),
            )

        st.subheader("Proficiencies")
        st.write("**Armor:** " + (", ".join(sheet["proficiencies"]["armor"]) or "None"))
        st.write("**Weapons:** " + (", ".join(sheet["proficiencies"]["weapons"]) or "None"))
        st.write("**Tools:** " + (", ".join(sheet["proficiencies"]["tools"]) or "None"))
        st.write("**Languages:** " + (", ".join(sheet["proficiencies"]["languages"]) or "None"))

        st.subheader("Features")
        render_feature_details(sheet.get("feature_details", []))
        if sheet.get("general_feat_details"):
            st.subheader("General feat choices")
            st.dataframe(
                [
                    {
                        "Feat": detail.get("name", ""),
                        "Choices": format_feat_choices(detail.get("choices", {})),
                        "Source": detail.get("source", {}).get("type", ""),
                    }
                    for detail in sheet.get("general_feat_details", [])
                ],
                hide_index=True,
                width="stretch",
            )

        st.subheader("Resources")
        if sheet["resources"]:
            st.json(sheet["resources"])
        else:
            st.write("None")

        if sheet["weapon_masteries"]:
            st.subheader("Weapon Mastery")
            st.write(", ".join(sheet["weapon_masteries"]))

        st.subheader("Spells")
        render_sheet_spells(sheet)

        st.subheader("Equipment")
        st.write(", ".join(sheet["equipment"]) or "None")

        with st.expander("Raw character JSON"):
            st.json(character)
        with st.expander("Normalized sheet JSON"):
            st.json(sheet)
        with st.expander("Validation report"):
            st.json(validation)

    with tabs[11]:
        recalculate_character(character, data)
        save_col, export_col, load_col = st.columns(3)
        with save_col:
            st.subheader("Save")
            if st.button("Save Character", type="primary"):
                path = save_character(character)
                st.success(f"Saved to {path}")
        with export_col:
            st.subheader("Export")
            render_pdf_export_options(character, data)
            validation = build_validation_report(
                character,
                data["classes_by_name"].get(character.get("class"), {}),
                data["species_by_name"].get(character.get("species"), {}),
                data["backgrounds_by_name"].get(character.get("background"), {}),
                data["spells"],
                data["weapons"],
            )
            if validation["complete"]:
                if st.button("Create Editable PDF"):
                    path = export_character_pdf(build_character_sheet(character, data))
                    st.success(f"Created {path}")
                    with path.open("rb") as file:
                        st.download_button(
                            "Download PDF",
                            file,
                            file_name=path.name,
                            mime="application/pdf",
                        )
            else:
                st.info("Complete required choices before PDF export.")
        with load_col:
            st.subheader("Load")
            saved_files = list_saved_characters()
            if not saved_files:
                st.info("No saved characters yet.")
            else:
                labels = [path.stem for path in saved_files]
                selected = st.selectbox("Saved characters", labels)
                selected_path = saved_files[labels.index(selected)]
                if st.button("Load Character"):
                    clear_ability_score_widgets()
                    st.session_state.character = load_character(selected_path)
                    st.session_state.level_up_draft = None
                    st.rerun()


if __name__ == "__main__":
    main()
