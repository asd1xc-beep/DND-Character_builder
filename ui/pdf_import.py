import hashlib
from copy import deepcopy
from dataclasses import replace

import streamlit as st

from models.character import ABILITIES
from presentation.compact_catalog import (
    build_class_feature_choice_catalog,
    build_lineage_catalog,
    build_species_choice_catalog,
    build_subclass_catalog,
    subclass_stable_id,
)
from presentation.equipment_catalog import build_equipment_catalog
from presentation.feat_catalog import build_feat_catalog
from presentation.option_catalog import SpellSelectionGroupSpec
from presentation.pdf_import_models import build_import_review_sections
from presentation.weapon_mastery_catalog import build_weapon_mastery_catalog
from rules.import_reconciliation import (
    build_reconciliation_draft,
    current_validation,
    first_subclass_choice_level,
    initial_reconciliation_selections,
)
from rules.class_choice_rules import (
    battle_master_maneuver_total,
    required_class_choice_definitions,
)
from rules.feat_rules import feat_choice_schema
from rules.leveling import (
    effective_spellcasting,
    get_available_spell_levels,
    get_class_resources,
    selected_subclass_options,
)
from rules.weapon_mastery import eligible_weapon_mastery_names
from rules.wizard_savant import (
    savant_spell_choice_keys_up_to_level,
    savant_spell_choice_rule,
)
from services.character_engine import active_origin_feats, recalculate_character
from services.equipment_state import selected_default_equipment
from services.pdf_import import MAX_PDF_BYTES, parse_pdf_import
from services.pdf_passthrough import normalize_pdf_passthrough_fields
from services.pdf_roundtrip import utc_timestamp
from services.save_load import migrate_character
from ui.equipment_browser import render_equipment_browser
from ui.medium_option_browser import (
    render_medium_option_browser,
    render_medium_single_option_browser,
)
from ui.spell_choice_browser import render_spell_choice_browser
from ui.subclass_choice import render_subclass_choice


PDF_IMPORT_DRAFT_KEY = "pdf_import_draft"
PDF_IMPORT_WIDGET_PREFIX = "pdf_import_"
GENERIC_TOOL_OPTIONS = [
    "Any artisan's tools",
    "Any gaming set",
    "Any musical instrument",
    "Any other tool",
]
ARTISAN_TOOL_OPTIONS = [
    "Carpenter's Tools",
    "Leatherworker's Tools",
    "Mason's Tools",
    "Potter's Tools",
    "Smith's Tools",
    "Tinker's Tools",
    "Weaver's Tools",
    "Woodcarver's Tools",
]
MUSICAL_INSTRUMENT_OPTIONS = [
    "Bagpipes",
    "Drum",
    "Dulcimer",
    "Flute",
    "Horn",
    "Lute",
    "Lyre",
    "Pan Flute",
    "Shawm",
    "Viol",
]


def render_pdf_import(data):
    st.divider()
    st.subheader("Import editable PDF")
    st.caption(
        "Builder PDFs recover their embedded JSON exactly. Compatible editable "
        "sheets open a detached review before any character state can change."
    )
    nonce = st.session_state.setdefault("pdf_import_uploader_nonce", 0)
    uploaded = st.file_uploader(
        "Choose an editable character PDF",
        type=["pdf"],
        key=f"pdf_import_upload_{nonce}",
        max_upload_size=MAX_PDF_BYTES // (1024 * 1024),
        width="stretch",
    )
    if uploaded is None:
        _render_cancel_if_needed()
        return None

    pdf_bytes = uploaded.getvalue()
    digest = hashlib.sha256(pdf_bytes).hexdigest()
    draft_state = st.session_state.get(PDF_IMPORT_DRAFT_KEY)
    if not draft_state or draft_state.get("digest") != digest:
        parsed = parse_pdf_import(pdf_bytes, data=data)
        draft_state = {
            "digest": digest,
            "result": parsed,
            "selections": initial_reconciliation_selections(parsed, data),
        }
        st.session_state[PDF_IMPORT_DRAFT_KEY] = draft_state

    import_result = draft_state["result"]
    if import_result.status in {"error", "unsupported"}:
        render_detection_failure(import_result)
        _render_cancel_if_needed()
        return None

    if import_result.source_kind == "embedded_state":
        reconciliation = build_reconciliation_draft(
            import_result,
            draft_state["selections"],
            data,
        )
        render_embedded_review(import_result, reconciliation)
    else:
        selections = render_compatible_controls(
            draft_state["selections"],
            data,
        )
        draft_state["selections"] = selections
        reconciliation = build_reconciliation_draft(import_result, selections, data)
        render_reconciliation_summary(reconciliation)

    render_adoption_actions(reconciliation, import_result, data)
    return reconciliation


def render_detection_failure(import_result):
    st.error("This PDF cannot be imported.")
    for issue in import_result.issues:
        st.write(f"**{issue.label}**")
        if issue.remedy:
            st.caption(issue.remedy)


def render_embedded_review(import_result, reconciliation):
    character = reconciliation.candidate_character
    st.success("Exact builder character found")
    with st.container(border=True):
        st.write(f"**{character.get('name') or 'Unnamed character'}**")
        class_line = " ".join(
            value
            for value in (
                character.get("class", ""),
                character.get("subclass", ""),
                str(character.get("level", "")),
            )
            if value
        )
        st.write(class_line or "Class not recorded")
        st.caption(
            f"{character.get('species') or 'No species'} | "
            f"{character.get('background') or 'No background'} | "
            f"Schema {import_result.payload_info.get('character_schema_version', '-')}"
        )
        st.write(
            f"Maximum HP: {character.get('hit_points', {}).get('maximum', '-')} | "
            f"Spells: {sum(len(values) for values in character.get('spells', {}).values())} | "
            f"Equipment: {len(character.get('equipment', []))}"
        )
    render_reconciliation_summary(reconciliation)


def render_compatible_controls(selections, data):
    selected = deepcopy(selections)
    st.warning("Compatible PDF - review required")

    with st.expander("1. Identity and level", expanded=True):
        selected["name"] = st.text_input(
            "Character name",
            value=selected.get("name", ""),
            key="pdf_import_name",
        )
        columns = st.columns(2)
        with columns[0]:
            selected["class_name"] = _catalog_select(
                "Class",
                [record.get("name", "") for record in data.get("classes", [])],
                selected.get("class_name", ""),
                "pdf_import_class",
            )
            selected["species"] = _catalog_select(
                "Species",
                [record.get("name", "") for record in data.get("species", [])],
                selected.get("species", ""),
                "pdf_import_species",
            )
        with columns[1]:
            selected["level"] = st.number_input(
                "Level",
                min_value=1,
                max_value=20,
                value=int(selected.get("level", 1) or 1),
                step=1,
                key="pdf_import_level",
            )
            selected["background"] = _catalog_select(
                "Background",
                [record.get("name", "") for record in data.get("backgrounds", [])],
                selected.get("background", ""),
                "pdf_import_background",
            )

    with st.expander("2. Ability-score baseline and background bonuses", expanded=True):
        _render_ability_controls(selected, data)

    with st.expander("3. Subclass and class choices", expanded=True):
        _render_class_controls(selected, data)

    with st.expander("4. Skills, expertise, feats, and masteries", expanded=False):
        _render_proficiency_controls(selected, data)

    with st.expander("5. Spells and spell sources", expanded=False):
        _render_spell_controls(selected, data)

    with st.expander("6. Equipment", expanded=False):
        _render_equipment_controls(selected, data)

    with st.expander("7. Hit-point baseline", expanded=True):
        observed = selected.get("observed_maximum_hp")
        st.write(f"**Observed maximum HP:** {observed if observed is not None else 'Missing'}")
        selected["preserve_observed_maximum_hp"] = st.toggle(
            "Preserve observed maximum HP",
            value=bool(selected.get("preserve_observed_maximum_hp", True)),
            key="pdf_import_preserve_hp",
            help=(
                "The builder stores the difference as an explicit import adjustment. "
                "Turn this off to use calculated HP instead."
            ),
        )

    return selected


def _render_ability_controls(selected, data):
    background = data.get("backgrounds_by_name", {}).get(selected.get("background"), {})
    allowed = list(background.get("ability_options", {}).get("abilities", []))
    selected["background_primary_ability"] = _catalog_select(
        "Background +2 ability",
        allowed,
        selected.get("background_primary_ability", ""),
        "pdf_import_background_primary",
    )
    secondary_options = [
        ability for ability in allowed
        if ability != selected.get("background_primary_ability")
    ]
    selected["background_secondary_ability"] = _catalog_select(
        "Background +1 ability",
        secondary_options,
        selected.get("background_secondary_ability", ""),
        "pdf_import_background_secondary",
    )
    columns = st.columns(3)
    scores = dict(selected.get("ability_scores", {}))
    for index, ability in enumerate(ABILITIES):
        with columns[index % 3]:
            scores[ability] = st.number_input(
                ability,
                min_value=1,
                max_value=30,
                value=int(scores.get(ability, 10) or 10),
                step=1,
                key=f"pdf_import_ability_{ability.casefold()}",
            )
    selected["ability_scores"] = scores
    selected["ability_scores_confirmed"] = st.checkbox(
        "I confirm these final scores and the reconstructed baseline.",
        value=bool(selected.get("ability_scores_confirmed")),
        key="pdf_import_abilities_confirmed",
    )


def _render_class_controls(selected, data):
    class_data = data.get("classes_by_name", {}).get(selected.get("class_name"), {})
    subclass_level = first_subclass_choice_level(class_data)
    if subclass_level and int(selected.get("level", 1)) >= subclass_level:
        options = build_subclass_catalog(
            class_data,
            int(selected.get("level", 1)),
            selected.get("subclass", ""),
        )
        selected_id = subclass_stable_id(class_data, selected.get("subclass"))
        updated_id = render_subclass_choice(
            options,
            selected_id,
            state_key="pdf_import_subclass_browser",
            label="Current subclass",
        )
        selected["subclass"] = next(
            (
                str(dict(option.payload).get("value", option.name))
                for option in options
                if option.stable_id == updated_id
            ),
            "",
        )
    else:
        st.caption("This class does not require a subclass at the imported level.")

    class_options = dict(selected.get("class_options", {}))
    for key, values in (class_data.get("class_options", {}) or {}).items():
        if not isinstance(values, list) or not values:
            continue
        class_options[key] = _catalog_select(
            key.replace("_", " ").title(),
            [str(value) for value in values],
            class_options.get(key, ""),
            f"pdf_import_class_option_{key}",
        )
    selected["class_options"] = class_options
    preview = _preview_candidate(selected, data)
    for definition in required_class_choice_definitions(
        preview,
        class_data,
        int(selected.get("level", 1)),
        data,
    ):
        key = definition.get("key", "")
        values = [str(value) for value in definition.get("options", []) if value]
        if not key or not values or key in (class_data.get("class_options", {}) or {}):
            continue
        options = build_class_feature_choice_catalog(
            values,
            selected_name=(
                class_options.get(key, "")
                if definition.get("type") == "class_option_single"
                else None
            ),
            kind=f"pdf_import_{key}",
            source_label=selected.get("class_name", ""),
        )
        if definition.get("type") == "class_option_single":
            class_options[key] = render_medium_single_option_browser(
                options,
                class_options.get(key, ""),
                state_key=f"pdf_import_class_choice_{key}",
                label=definition.get("name", key.replace("_", " ").title()),
                search_label="Search choices",
            ) or ""
        else:
            selected_values = list(class_options.get(key, []) or [])
            class_options[key] = render_medium_option_browser(
                options,
                selected_values,
                selection_limit=int(definition.get("choose", 0) or 0),
                state_key=f"pdf_import_class_choice_{key}",
                label=definition.get("name", key.replace("_", " ").title()),
                search_label="Search choices",
            )
    _render_subclass_follow_up_controls(selected, class_data, class_options, data)
    selected["class_options"] = class_options


def _render_subclass_follow_up_controls(selected, class_data, class_options, data):
    subclass_options = selected_subclass_options(
        class_data,
        selected.get("subclass", ""),
    )
    if not subclass_options:
        return
    level = int(selected.get("level", 1))
    rules = []
    for key in (
        "maneuvers",
        "student_of_war_skill",
        "student_of_war_tool",
        "lore_skills",
        "hunters_prey",
        "primal_companion",
    ):
        rule = subclass_options.get(key)
        if not isinstance(rule, dict):
            continue
        values = rule.get("from", [])
        if values == "class_skill_options":
            values = class_data.get("skill_choices", {}).get("from", [])
        choose = int(rule.get("choose", 1) or 1)
        if key == "maneuvers" and class_data.get("name") == "Fighter":
            choose = battle_master_maneuver_total(level)
        rules.append((key, rule.get("label", key.replace("_", " ").title()), values, choose))

    for key, label, values, choose in rules:
        names = [str(value) for value in values or [] if value]
        if not names:
            continue
        options = build_class_feature_choice_catalog(
            names,
            kind=f"pdf_import_subclass_{key}",
            source_label=selected.get("subclass", ""),
        )
        if choose == 1 and key in {
            "student_of_war_skill",
            "student_of_war_tool",
            "hunters_prey",
            "primal_companion",
        }:
            class_options[key] = render_medium_single_option_browser(
                options,
                class_options.get(key, ""),
                state_key=f"pdf_import_subclass_choice_{key}",
                label=label,
                search_label="Search choices",
            ) or ""
        else:
            class_options[key] = render_medium_option_browser(
                options,
                list(class_options.get(key, []) or []),
                selection_limit=choose,
                state_key=f"pdf_import_subclass_choice_{key}",
                label=label,
                search_label="Search choices",
            )

    structured_rule = subclass_options.get("structured_spell_choice", {})
    if structured_rule:
        structured_options = structured_rule.get("options", [])
        option_names = [
            str(option.get("name") or "")
            for option in structured_options
            if option.get("name")
        ]
        current = class_options.get("structured_spell_choice", {})
        current_name = current.get("name", "") if isinstance(current, dict) else ""
        catalog = build_class_feature_choice_catalog(
            option_names,
            selected_name=current_name,
            kind="pdf_import_structured_spell_choice",
            source_label=selected.get("subclass", ""),
        )
        chosen_name = render_medium_single_option_browser(
            catalog,
            current_name,
            state_key="pdf_import_structured_spell_choice",
            label=structured_rule.get("name", "Subclass spell group"),
            search_label="Search spell groups",
        )
        class_options["structured_spell_choice"] = deepcopy(next(
            (
                option for option in structured_options
                if option.get("name") == chosen_name
            ),
            {},
        ))

    if class_data.get("name") == "Wizard":
        for key in savant_spell_choice_keys_up_to_level(level):
            rule = (
                subclass_options.get("savant_spells", {})
                if key == "savant_spells"
                else savant_spell_choice_rule(
                    subclass_options,
                    selected.get("subclass", ""),
                    int(key.rsplit("_", 1)[-1]),
                )
            )
            if not rule:
                continue
            source = rule.get("from", {})
            spell_names = [
                spell.get("name", "")
                for spell in data.get("spells", [])
                if spell.get("name")
                and "Wizard" in spell.get("classes", [])
                and (
                    not source.get("levels")
                    or spell.get("level") in source.get("levels", [])
                )
                and (
                    not source.get("school")
                    or spell.get("school_code") == source.get("school")
                )
            ]
            options = build_class_feature_choice_catalog(
                spell_names,
                kind=f"pdf_import_{key}",
                source_label=selected.get("subclass", ""),
            )
            class_options[key] = render_medium_option_browser(
                options,
                list(class_options.get(key, []) or []),
                selection_limit=int(rule.get("choose", 0) or 0),
                state_key=f"pdf_import_subclass_choice_{key}",
                label=rule.get("label", key.replace("_", " ").title()),
                search_label="Search eligible Wizard spells",
            )


def _render_proficiency_controls(selected, data):
    class_data = data.get("classes_by_name", {}).get(selected.get("class_name"), {})
    skill_rule = class_data.get("skill_choices", {})
    skill_options = list(skill_rule.get("from", []))
    selected["class_skills"] = st.multiselect(
        f"Class skills (choose {skill_rule.get('choose', 0)})",
        skill_options,
        default=[
            skill for skill in selected.get("class_skills", [])
            if skill in skill_options
        ],
        max_selections=int(skill_rule.get("choose", 0) or 0) or None,
        key="pdf_import_class_skills",
    )
    _render_species_controls(selected, data)

    feat_ids = list(selected.get("general_feat_ids", []))
    feat_options = tuple(
        replace(
            option,
            selected=str(dict(option.payload).get("value", "")) in feat_ids,
            availability_status=(
                "selected"
                if str(dict(option.payload).get("value", "")) in feat_ids
                else option.availability_status
            ),
            eligibility_reasons=(
                ("Recovered from the PDF; confirm this feat.",)
                if str(dict(option.payload).get("value", "")) in feat_ids
                else option.eligibility_reasons
            ),
        )
        for option in build_feat_catalog(data.get("feats", []))
    )
    selected["general_feat_ids"] = render_medium_option_browser(
        feat_options,
        feat_ids,
        selection_limit=0,
        state_key="pdf_import_feat_browser",
        label="Current general feats",
        search_label="Search feats by name",
        add_label="Add recovered feat",
        remove_label="Remove feat",
    )
    _render_general_feat_choices(selected, data)
    selected["feats_confirmed"] = st.checkbox(
        "I confirm the current feats and understand historical ability increases are absorbed into the baseline.",
        value=bool(selected.get("feats_confirmed")),
        key="pdf_import_feats_confirmed",
    )

    candidate = _preview_candidate(selected, data)
    mastery_limit = int(
        get_class_resources(class_data, int(selected.get("level", 1))).get(
            "weapon_mastery_count", 0
        )
        or 0
    )
    mastery_options = build_weapon_mastery_catalog(
        data.get("weapons", []),
        eligible_names=eligible_weapon_mastery_names(candidate, data.get("weapons", [])),
        selected_names=selected.get("weapon_masteries", []),
        selection_limit=mastery_limit,
        mastery_descriptions=data.get("weapon_masteries", []),
    )
    selected["weapon_masteries"] = render_medium_option_browser(
        mastery_options,
        list(selected.get("weapon_masteries", [])),
        selection_limit=mastery_limit,
        state_key="pdf_import_mastery_browser",
        label="Current Weapon Masteries",
        search_label="Search weapons by name",
    )
    selected["masteries_confirmed"] = st.checkbox(
        "I confirm the current Weapon Mastery selections.",
        value=bool(selected.get("masteries_confirmed")),
        key="pdf_import_masteries_confirmed",
    )
    _render_origin_feat_choices(selected, data)


def _render_species_controls(selected, data):
    species_data = data.get("species_by_name", {}).get(selected.get("species"), {})
    species_options = dict(selected.get("species_options", {}) or {})
    skill_rule = species_data.get("skill_choices", {})
    if skill_rule.get("choose"):
        options = list(skill_rule.get("from", []))
        species_options["skill_proficiencies"] = st.multiselect(
            f"Species skill (choose {skill_rule.get('choose')})",
            options,
            default=[
                skill for skill in species_options.get("skill_proficiencies", [])
                if skill in options
            ],
            max_selections=int(skill_rule.get("choose", 0) or 0),
            key="pdf_import_species_skills",
        )

    if species_data.get("lineage_options"):
        lineage_catalog = build_lineage_catalog(
            species_data,
            species_options.get("lineage", ""),
        )
        species_options["lineage"] = render_medium_single_option_browser(
            lineage_catalog,
            species_options.get("lineage", ""),
            state_key="pdf_import_species_lineage",
            label="Species lineage",
            search_label="Search lineages",
        ) or ""

    choice_rule = species_data.get("choice_options")
    if choice_rule:
        choice_catalog = build_species_choice_catalog(
            species_data,
            choice_rule,
            species_options.get(choice_rule.get("key"), ""),
        )
        species_options[choice_rule["key"]] = render_medium_single_option_browser(
            choice_catalog,
            species_options.get(choice_rule["key"], ""),
            state_key=f"pdf_import_species_choice_{choice_rule['key']}",
            label=choice_rule.get("name", "Species choice"),
            search_label="Search choices",
        ) or ""

    if "Versatile" in species_data.get("traits", []):
        origin_names = set(data.get("rules", {}).get("origin_feats", []))
        origin_feats = [
            feat for feat in data.get("feats", [])
            if feat.get("name") in origin_names
        ]
        selected_names = list(species_options.get("origin_feats", []) or [])
        selected_ids = [
            feat.get("id")
            for feat in origin_feats
            if feat.get("name") in selected_names
        ]
        feat_options = tuple(
            replace(
                option,
                selected=str(dict(option.payload).get("value", "")) in selected_ids,
                availability_status=(
                    "selected"
                    if str(dict(option.payload).get("value", "")) in selected_ids
                    else option.availability_status
                ),
            )
            for option in build_feat_catalog(origin_feats)
        )
        chosen_ids = render_medium_option_browser(
            feat_options,
            selected_ids,
            selection_limit=1,
            state_key="pdf_import_species_origin_feat",
            label="Human Origin feat",
            search_label="Search Origin feats",
        )
        names_by_id = {
            feat.get("id"): feat.get("name")
            for feat in origin_feats
        }
        species_options["origin_feats"] = [
            names_by_id[feat_id]
            for feat_id in chosen_ids
            if feat_id in names_by_id
        ]
    selected["species_options"] = species_options


def _render_general_feat_choices(selected, data):
    selected_ids = list(selected.get("general_feat_ids", []) or [])
    if not selected_ids:
        selected["feat_choices"] = {}
        return
    feat_lookup = {
        feat.get("id"): feat
        for feat in data.get("feats", [])
        if feat.get("id")
    }
    feat_choices = deepcopy(selected.get("feat_choices", {}) or {})
    preview = _preview_candidate(selected, data)
    for feat_id in selected_ids:
        feat = feat_lookup.get(feat_id)
        if not feat:
            continue
        choices = dict(feat_choices.get(feat_id, {}) or {})
        schema = feat_choice_schema(feat, preview, data)
        if feat.get("name") == "Resilient":
            choices["ability"] = _catalog_select(
                "Resilient saving throw ability",
                [
                    ability for ability in ABILITIES
                    if ability not in preview.get("saving_throw_proficiencies", [])
                ],
                choices.get("ability", ""),
                f"pdf_import_feat_{feat_id}_ability",
            )
        for field in schema:
            values = [str(value) for value in field.get("options", []) if value]
            if not values:
                continue
            options = build_class_feature_choice_catalog(
                values,
                selected_name=(
                    choices.get(field["id"], "")
                    if field.get("type") != "multi"
                    else None
                ),
                kind=f"pdf_import_feat_{feat_id}_{field['id']}",
                source_label=feat.get("name", ""),
            )
            if field.get("type") == "multi":
                choices[field["id"]] = render_medium_option_browser(
                    options,
                    list(choices.get(field["id"], []) or []),
                    selection_limit=int(field.get("choose", 0) or 0),
                    state_key=f"pdf_import_feat_choice_{feat_id}_{field['id']}",
                    label=f"{feat.get('name')}: {field.get('label', field['id'])}",
                    search_label="Search feat choices",
                )
            else:
                choices[field["id"]] = render_medium_single_option_browser(
                    options,
                    choices.get(field["id"], ""),
                    state_key=f"pdf_import_feat_choice_{feat_id}_{field['id']}",
                    label=f"{feat.get('name')}: {field.get('label', field['id'])}",
                    search_label="Search feat choices",
                ) or ""
        feat_choices[feat_id] = choices
    selected["feat_choices"] = feat_choices


def _render_origin_feat_choices(selected, data):
    preview = _preview_candidate(selected, data)
    feats = active_origin_feats(preview)
    if not feats:
        return
    choices = deepcopy(selected.get("origin_feat_choices", {}) or {})
    choices.setdefault("skills", [])
    choices.setdefault("tools", [])
    choices.setdefault("cantrips", [])
    choices.setdefault("spell", "")
    choices.setdefault("spellcasting_ability", "")
    st.write("**Origin feat choices**")
    st.caption(", ".join(feats))

    if "Skilled" in feats:
        skill_options = [
            f"Skill: {skill}"
            for skill in data.get("rules", {}).get("skills", {})
        ]
        tool_options = [f"Tool: {tool}" for tool in GENERIC_TOOL_OPTIONS]
        combined = skill_options + tool_options
        current = [
            *[f"Skill: {skill}" for skill in choices.get("skills", [])],
            *[f"Tool: {tool}" for tool in choices.get("tools", [])],
        ]
        picked = st.multiselect(
            "Skilled proficiencies (choose 3)",
            combined,
            default=[value for value in current if value in combined],
            max_selections=3,
            key="pdf_import_origin_skilled",
        )
        choices["skills"] = [
            value.removeprefix("Skill: ")
            for value in picked
            if value.startswith("Skill: ")
        ]
        choices["tools"] = [
            value.removeprefix("Tool: ")
            for value in picked
            if value.startswith("Tool: ")
        ]
    elif "Crafter" in feats:
        choices["tools"] = st.multiselect(
            "Crafter tools (choose 3)",
            ARTISAN_TOOL_OPTIONS,
            default=[
                value for value in choices.get("tools", [])
                if value in ARTISAN_TOOL_OPTIONS
            ],
            max_selections=3,
            key="pdf_import_origin_crafter",
        )
    elif "Musician" in feats:
        choices["tools"] = st.multiselect(
            "Musician instruments (choose 3)",
            MUSICAL_INSTRUMENT_OPTIONS,
            default=[
                value for value in choices.get("tools", [])
                if value in MUSICAL_INSTRUMENT_OPTIONS
            ],
            max_selections=3,
            key="pdf_import_origin_musician",
        )

    magic_feat = next(
        (feat for feat in feats if feat.startswith("Magic Initiate")),
        "",
    )
    if magic_feat:
        source_class = magic_feat.split("(", 1)[1].split(")", 1)[0]
        cantrip_names = tuple(
            spell.get("name", "")
            for spell in data.get("spells", [])
            if spell.get("level") == 0
            and source_class in spell.get("classes", [])
        )
        spell_names = tuple(
            spell.get("name", "")
            for spell in data.get("spells", [])
            if spell.get("level") == 1
            and source_class in spell.get("classes", [])
        )
        groups = (
            SpellSelectionGroupSpec(
                "cantrips",
                "Magic Initiate cantrips",
                cantrip_names,
                tuple(choices.get("cantrips", [])),
                2,
            ),
            SpellSelectionGroupSpec(
                "spell",
                "Magic Initiate Level 1 spell",
                spell_names,
                (choices.get("spell", ""),) if choices.get("spell") else (),
                1,
            ),
        )
        updated = render_spell_choice_browser(
            data.get("spells", []),
            groups,
            {
                "cantrips": list(choices.get("cantrips", [])),
                "spell": [choices["spell"]] if choices.get("spell") else [],
            },
            state_key="pdf_import_origin_magic_initiate",
            label=f"{magic_feat} spell choices",
        )
        choices["cantrips"] = updated.get("cantrips", [])
        choices["spell"] = next(iter(updated.get("spell", [])), "")
        choices["spellcasting_ability"] = _catalog_select(
            "Magic Initiate spellcasting ability",
            ["Intelligence", "Wisdom", "Charisma"],
            choices.get("spellcasting_ability", ""),
            "pdf_import_origin_magic_ability",
        )
    selected["origin_feat_choices"] = choices


def _render_spell_controls(selected, data):
    class_data = data.get("classes_by_name", {}).get(selected.get("class_name"), {})
    spellcasting = effective_spellcasting(
        class_data,
        selected.get("subclass", ""),
        int(selected.get("level", 1)),
    ) or {}
    if not spellcasting:
        st.info("The selected class and subclass do not have modeled spell choices at this level.")
        selected["spells_confirmed"] = st.checkbox(
            "I confirm there are no class spell selections to recover.",
            value=bool(selected.get("spells_confirmed")),
            key="pdf_import_spells_confirmed",
        )
        return

    unmatched = list((selected.get("recovered", {}) or {}).get("unmatched_spells", []))
    if unmatched:
        kept_unmatched = st.multiselect(
            "Unmatched PDF spell entries (remove entries you do not want to recover)",
            unmatched,
            default=unmatched,
            key="pdf_import_unmatched_spells",
        )
        selected.setdefault("recovered", {})["unmatched_spells"] = kept_unmatched

    spell_list = spellcasting.get("spell_list", selected.get("class_name", ""))
    available_levels = set(get_available_spell_levels(class_data, int(selected.get("level", 1))))
    cantrip_names = tuple(
        spell["name"] for spell in data.get("spells", [])
        if int(spell.get("level", -1)) == 0 and spell_list in spell.get("classes", [])
    )
    leveled_names = tuple(
        spell["name"] for spell in data.get("spells", [])
        if int(spell.get("level", -1)) in available_levels
        and spell_list in spell.get("classes", [])
    )
    spells = selected.get("spells", {}) or {}
    groups = []
    if spellcasting.get("cantrips_known"):
        groups.append(SpellSelectionGroupSpec(
            "cantrips",
            "Cantrips",
            cantrip_names,
            tuple(spells.get("cantrips", [])),
            int(spellcasting.get("cantrips_known", 0)),
        ))
    if class_data.get("name") == "Wizard":
        groups.append(SpellSelectionGroupSpec(
            "spellbook",
            "Spellbook",
            leveled_names,
            tuple(spells.get("spellbook", [])),
            int(spellcasting.get("spellbook_spells", 0) or 0),
        ))
        groups.append(SpellSelectionGroupSpec(
            "prepared",
            "Prepared from spellbook",
            tuple(spells.get("spellbook", [])),
            tuple(spells.get("prepared", [])),
            int(spellcasting.get("prepared_spells", 0) or 0),
        ))
    elif spellcasting.get("known_spells"):
        groups.append(SpellSelectionGroupSpec(
            "known",
            "Known spells",
            leveled_names,
            tuple(spells.get("known", [])),
            int(spellcasting.get("known_spells", 0)),
        ))
    elif spellcasting.get("prepared_spells"):
        groups.append(SpellSelectionGroupSpec(
            "prepared",
            "Prepared spells",
            leveled_names,
            tuple(spells.get("prepared", [])),
            int(spellcasting.get("prepared_spells", 0)),
        ))
    selected["spells"] = render_spell_choice_browser(
        data.get("spells", []),
        groups,
        spells,
        state_key="pdf_import_spell_browser",
        label="Recovered class spell selections",
    )
    selected["spells_confirmed"] = st.checkbox(
        "I confirm these spell selections and their class source.",
        value=bool(selected.get("spells_confirmed")),
        key="pdf_import_spells_confirmed",
    )


def _render_equipment_controls(selected, data):
    preview = _preview_candidate(selected, data)
    class_data = data.get("classes_by_name", {}).get(selected.get("class_name"), {})
    background_data = data.get("backgrounds_by_name", {}).get(selected.get("background"), {})
    selected["include_default_equipment"] = st.toggle(
        "Restore matching class and background default equipment",
        value=bool(selected.get("include_default_equipment", False)),
        key="pdf_import_include_default_equipment",
    )
    preview["include_default_equipment"] = selected["include_default_equipment"]
    package_equipment = selected_default_equipment(preview, class_data, background_data)
    equipment_options = build_equipment_catalog(
        data.get("equipment", []),
        selected.get("custom_equipment", []),
        package_equipment,
    )
    selected["custom_equipment"] = render_equipment_browser(
        equipment_options,
        list(selected.get("custom_equipment", [])),
        state_key="pdf_import_equipment_browser",
        label="Recovered and custom equipment",
    )
    selected["equipment_confirmed"] = st.checkbox(
        "I confirm the recovered equipment and unmatched custom entries.",
        value=bool(selected.get("equipment_confirmed")),
        key="pdf_import_equipment_confirmed",
    )


def render_reconciliation_summary(reconciliation):
    blocker_count = sum(
        issue.severity == "blocker" for issue in reconciliation.issues
    )
    warning_count = sum(
        issue.severity == "warning" for issue in reconciliation.issues
    )
    if blocker_count:
        st.warning(f"{blocker_count} required reconciliation issue(s) remain.")
    else:
        st.success("The detached candidate has no remaining blockers.")
    st.caption(f"{warning_count} non-blocking comparison or validation warning(s).")

    for section in build_import_review_sections(reconciliation):
        if not section["issues"] and not section["comparisons"]:
            continue
        with st.expander(section["label"], expanded=section["key"] == "comparison"):
            for issue in section["issues"]:
                st.write(f"**{issue['state_label']}:** {issue['label']}")
                if issue.get("observed") not in ("", None):
                    st.caption(f"Observed: {issue['observed']}")
                if issue.get("remedy"):
                    st.caption(issue["remedy"])
            if section["comparisons"]:
                st.dataframe(
                    [
                        {
                            "Field": item["label"],
                            "Status": item["state_label"],
                            "Observed": item["observed"],
                            "Calculated": item["calculated"],
                        }
                        for item in section["comparisons"]
                    ],
                    hide_index=True,
                    width="stretch",
                )


def render_adoption_actions(reconciliation, import_result, data):
    buttons = st.container(horizontal=True, horizontal_alignment="left")
    with buttons:
        label = (
            "Open as working character"
            if reconciliation.recovered.get("source_kind") == "embedded_state"
            else "Create working character from PDF"
        )
        if st.button(
            label,
            type="primary",
            disabled=not reconciliation.can_confirm,
            key="pdf_import_stage_candidate",
        ):
            try:
                adopt_pdf_import_candidate(
                    st.session_state,
                    reconciliation,
                    import_result,
                    data,
                )
            except PdfImportAdoptionError as exc:
                st.error(str(exc))
            else:
                st.rerun()
        if st.button("Cancel PDF import", key="pdf_import_cancel"):
            clear_pdf_import_state()
            st.rerun()


class PdfImportAdoptionError(ValueError):
    pass


def adopt_pdf_import_candidate(
    session_state,
    reconciliation,
    import_result,
    data,
    *,
    imported_at=None,
):
    """Validate a detached copy completely before replacing session character state."""
    if not getattr(reconciliation, "can_confirm", False):
        raise PdfImportAdoptionError(
            "Resolve all PDF import blockers before creating the working character."
        )

    candidate = migrate_character(
        deepcopy(getattr(reconciliation, "candidate_character", {}) or {})
    )
    if not candidate:
        raise PdfImportAdoptionError(
            "The reconciled PDF candidate is unavailable."
        )

    existing_passthrough = candidate.get("pdf_passthrough_fields", {})
    imported_passthrough = getattr(import_result, "passthrough_fields", {}) or {}
    candidate["pdf_passthrough_fields"] = normalize_pdf_passthrough_fields({
        **existing_passthrough,
        **imported_passthrough,
    })
    candidate["import_provenance"] = build_import_provenance(
        reconciliation,
        import_result,
        imported_at=imported_at,
    )
    recalculate_character(candidate, data)
    validation = current_validation(candidate, data)
    if not validation.get("complete"):
        blockers = [
            *validation.get("missing", []),
            *validation.get("unsupported", []),
        ]
        raise PdfImportAdoptionError(
            "The candidate changed during final validation: "
            + "; ".join(blockers or ["unknown validation failure"])
        )

    summary = build_import_handoff_summary(
        candidate,
        reconciliation,
        import_result,
        validation,
    )
    preserved = {
        key: deepcopy(session_state[key])
        for key in ("data_source",)
        if key in session_state
    }
    for key in list(session_state):
        del session_state[key]
    for key, value in preserved.items():
        session_state[key] = value
    session_state["character"] = candidate
    session_state["level_up_draft"] = None
    session_state["pdf_import_handoff_summary"] = summary
    session_state["requested_builder_tab"] = "Character Sheet"
    return candidate


def build_import_provenance(reconciliation, import_result, *, imported_at=None):
    source_kind = str(getattr(import_result, "source_kind", "") or "")
    payload_info = getattr(import_result, "payload_info", {}) or {}
    issue_labels = [
        str(getattr(issue, "label", "") or "")
        for issue in [
            *(getattr(import_result, "issues", []) or []),
            *(getattr(reconciliation, "issues", []) or []),
        ]
        if getattr(issue, "severity", "") in {"warning", "info"}
        and getattr(issue, "label", "")
    ]
    return {
        "source_kind": source_kind,
        "payload_version": int(payload_info.get("payload_version", 0) or 0),
        "template_signature": str(payload_info.get("signature", "") or ""),
        "imported_at": imported_at or utc_timestamp(),
        "status": (
            "verified"
            if source_kind == "embedded_state"
            and getattr(import_result, "status", "") == "ready"
            else "reviewed"
        ),
        "ability_history_reconstructed": False,
        "hp_history_reconstructed": False,
        "warnings": list(dict.fromkeys(issue_labels)),
    }


def build_import_handoff_summary(
    candidate,
    reconciliation,
    import_result,
    validation,
):
    comparisons = getattr(reconciliation, "comparisons", []) or []
    calculated_changes = [
        comparison.label
        for comparison in comparisons
        if comparison.status == "conflict"
    ]
    provenance = candidate.get("import_provenance", {})
    return {
        "character_name": candidate.get("name", ""),
        "source_kind": getattr(import_result, "source_kind", ""),
        "status": provenance.get("status", ""),
        "preserved": [
            "Current structured character choices",
            "Final ability scores",
            "Maximum and current HP",
            "Safe unmodeled PDF fields",
        ],
        "calculated_changes": calculated_changes,
        "warnings": list(provenance.get("warnings", [])),
        "validation_warnings": list(validation.get("warnings", [])),
    }


def render_import_handoff_summary(summary):
    if not summary:
        return
    with st.container(border=True):
        st.success(
            f"{summary.get('character_name') or 'The imported character'} "
            "is now the working character."
        )
        st.caption(
            f"Import status: {summary.get('status', 'reviewed')} | "
            f"Source: {summary.get('source_kind', 'PDF')}"
        )
        if summary.get("preserved"):
            st.write("**Preserved**")
            for item in summary["preserved"]:
                st.write(f"- {item}")
        if summary.get("calculated_changes"):
            st.write(
                "**Calculated differences reviewed:** "
                + ", ".join(summary["calculated_changes"])
            )
        warnings = [
            *summary.get("warnings", []),
            *summary.get("validation_warnings", []),
        ]
        if warnings:
            st.caption("Review notes: " + "; ".join(dict.fromkeys(warnings)))


def clear_pdf_import_state():
    """Clear only import-owned state; never touch the active character or level-up draft."""
    for key in list(st.session_state):
        if key.startswith(PDF_IMPORT_WIDGET_PREFIX):
            del st.session_state[key]
    st.session_state["pdf_import_uploader_nonce"] = (
        int(st.session_state.get("pdf_import_uploader_nonce", 0)) + 1
    )


def _render_cancel_if_needed():
    if st.session_state.get(PDF_IMPORT_DRAFT_KEY):
        if st.button("Cancel PDF import", key="pdf_import_cancel_without_upload"):
            clear_pdf_import_state()
            st.rerun()


def _catalog_select(label, values, current, key):
    options = ["", *[str(value) for value in values if value]]
    if current and current not in options:
        options.append(str(current))
    return st.selectbox(
        label,
        options,
        index=options.index(current) if current in options else 0,
        format_func=lambda value: value or "Choose...",
        key=key,
    )


def _preview_candidate(selections, data):
    class PreviewImportResult:
        source_kind = "compatible_form"
        extracted_data = {}

    preview_selections = deepcopy(selections)
    preview_selections.update({
        "ability_scores_confirmed": True,
        "spells_confirmed": True,
        "feats_confirmed": True,
        "masteries_confirmed": True,
        "equipment_confirmed": True,
        "preserve_observed_maximum_hp": False,
        "observed_maximum_hp": preview_selections.get("observed_maximum_hp", 1) or 1,
    })
    return build_reconciliation_draft(
        PreviewImportResult(),
        preview_selections,
        data,
    ).candidate_character
