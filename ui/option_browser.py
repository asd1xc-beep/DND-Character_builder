import streamlit as st

from presentation.option_catalog import (
    add_option_to_group_selection,
    remove_option_from_group_selection,
)
from presentation.option_models import OptionGroupState, OptionViewModel


def render_spell_option_browser(
    options: tuple[OptionViewModel, ...],
    selected_names: list[str],
    *,
    selection_limit: int,
    state_key: str,
    label: str,
) -> list[str]:
    group_key = _single_group_key(options, "cantrip")
    updated = render_unified_spell_picker(
        options,
        {group_key: selected_names},
        state_key=state_key,
        label=label,
        search_label="Search cantrips by name",
    )
    return updated.get(group_key, [name for name in selected_names or [] if name])


def render_unified_spell_picker(
    options: tuple[OptionViewModel, ...],
    selected_groups: dict[str, list[str]],
    *,
    state_key: str,
    label: str,
    search_label: str = "Search spells by name",
) -> dict[str, list[str]]:
    st.write(f"**{label}**")
    selections = {
        key: [name for name in values or [] if name]
        for key, values in (selected_groups or {}).items()
    }
    _initialize_browser_state(state_key, options, selections)

    left, right = st.columns([3, 2], vertical_alignment="top")
    with left:
        filtered_options = _render_browser_controls(state_key, options, search_label)
        _render_group_counts(options)
        _render_selected_groups(options, selections)
        inspected_id = _render_option_table(state_key, filtered_options)
        if inspected_id:
            st.session_state[f"{state_key}_inspected_id"] = inspected_id

    inspected = _selected_inspected_option(
        options,
        st.session_state.get(f"{state_key}_inspected_id", ""),
    )
    with right:
        updated = _render_spell_inspector(
            inspected,
            selections,
            options,
            state_key=state_key,
        )
    return updated or selections


def _initialize_browser_state(
    state_key: str,
    options: tuple[OptionViewModel, ...],
    selected_groups: dict[str, list[str]],
) -> None:
    st.session_state.setdefault(f"{state_key}_search", "")
    st.session_state.setdefault(f"{state_key}_school", "All schools")
    st.session_state.setdefault(f"{state_key}_level", "All levels")
    inspected_key = f"{state_key}_inspected_id"
    current_id = st.session_state.get(inspected_key, "")
    if current_id and _selected_inspected_option(options, current_id):
        return

    selected_names = {
        name
        for values in selected_groups.values()
        for name in values
    }
    initial = next((option for option in options if option.name in selected_names), None)
    if initial is None:
        initial = next((option for option in options if option.availability_status == "available"), None)
    st.session_state[inspected_key] = initial.stable_id if initial else ""


def _render_browser_controls(
    state_key: str,
    options: tuple[OptionViewModel, ...],
    search_label: str,
) -> tuple[OptionViewModel, ...]:
    st.text_input(search_label, key=f"{state_key}_search")
    schools = ["All schools"] + sorted({
        str(_payload_value(option, "school"))
        for option in options
        if _payload_value(option, "school")
    })
    current_school = st.session_state.get(f"{state_key}_school", "All schools")
    if current_school not in schools:
        st.session_state[f"{state_key}_school"] = "All schools"
    st.selectbox("Filter by school", schools, key=f"{state_key}_school")

    levels = ["All levels"] + _level_filter_options(options)
    current_level = st.session_state.get(f"{state_key}_level", "All levels")
    if current_level not in levels:
        st.session_state[f"{state_key}_level"] = "All levels"
    st.selectbox("Filter by spell level", levels, key=f"{state_key}_level")

    search = st.session_state.get(f"{state_key}_search", "").strip().casefold()
    school = st.session_state.get(f"{state_key}_school", "All schools")
    level_filter = st.session_state.get(f"{state_key}_level", "All levels")
    filtered = [
        option
        for option in options
        if (not search or search in option.name.casefold())
        and (school == "All schools" or _payload_value(option, "school") == school)
        and (level_filter == "All levels" or _level_label(option) == level_filter)
    ]
    if not filtered:
        st.info("No spells match the current filters.")
    return tuple(filtered)


def _render_group_counts(options: tuple[OptionViewModel, ...]) -> None:
    for group in _group_definitions(options):
        limit = group.selection_limit
        limit_label = str(limit) if limit is not None else "any"
        st.caption(f"{group.label}: {group.selected_count} / {limit_label} selected")


def _render_selected_groups(
    options: tuple[OptionViewModel, ...],
    selected_groups: dict[str, list[str]],
) -> None:
    labels_by_key = {group.key: group.label for group in _group_definitions(options)}
    for key, selected in selected_groups.items():
        label = labels_by_key.get(key, key.replace("_", " ").title())
        st.caption(f"{label}: " + (", ".join(selected) if selected else "none"))


def _render_option_table(
    state_key: str,
    options: tuple[OptionViewModel, ...],
) -> str:
    inspected_id = ""
    with st.container(height=360):
        st.caption("Spell | Level | School | Casting time | Range | Duration | Status")
        for option in options:
            if st.button(
                _row_button_label(option),
                key=f"{state_key}_inspect_{option.stable_id}",
                width="stretch",
            ):
                inspected_id = option.stable_id
    return inspected_id


def _render_spell_inspector(
    option: OptionViewModel | None,
    selected_groups: dict[str, list[str]],
    options: tuple[OptionViewModel, ...],
    *,
    state_key: str,
) -> dict[str, list[str]] | None:
    if option is None:
        st.info("Select a spell to inspect its rules.")
        return None

    st.subheader(option.name)
    st.caption(_metadata_line(option, "Level"))

    action_result = _render_group_actions(option, selected_groups, options, state_key)
    if action_result is not None:
        return action_result

    for label in ("School", "Casting time", "Range", "Duration", "Components"):
        st.write(f"**{label}:** {_metadata_line(option, label) or '-'}")
    st.write(f"**Source:** {option.source.source or '-'}")
    if option.full_description:
        st.markdown(option.full_description)
    else:
        st.caption("No description is available for this spell.")
    return None


def _render_group_actions(
    option: OptionViewModel,
    selected_groups: dict[str, list[str]],
    options: tuple[OptionViewModel, ...],
    state_key: str,
) -> dict[str, list[str]] | None:
    visible_groups = [
        group
        for group in option.group_states
        if group.selected or group.eligible
    ] or list(option.group_states)

    for group in visible_groups:
        st.write(f"**{group.label}:** {_status_label(group.availability_status)}")
        for reason in group.eligibility_reasons:
            st.caption(reason)

        if group.selected:
            if st.button(
                group.remove_label,
                key=f"{state_key}_remove_{group.key}_{option.stable_id}",
                icon=":material/remove:",
            ):
                result = remove_option_from_group_selection(
                    selected_groups.get(group.key, []),
                    option.stable_id,
                    options,
                    group_key=group.key,
                )
                return _updated_groups(selected_groups, group.key, result.selection)
            continue

        if st.button(
            group.add_label,
            key=f"{state_key}_add_{group.key}_{option.stable_id}",
            icon=":material/add:",
            disabled=group.availability_status != "available",
        ):
            result = add_option_to_group_selection(
                selected_groups.get(group.key, []),
                options,
                option.stable_id,
                group_key=group.key,
                selection_limit=group.selection_limit,
            )
            if not result.accepted and result.reason:
                st.warning(result.reason)
            return _updated_groups(selected_groups, group.key, result.selection)
    return None


def _selected_inspected_option(
    options: tuple[OptionViewModel, ...],
    stable_id: str,
) -> OptionViewModel | None:
    return next((option for option in options if option.stable_id == stable_id), None)


def _table_row(option: OptionViewModel) -> dict:
    return {
        "_id": option.stable_id,
        "Name": option.name,
        "Level": _level_label(option),
        "School": _payload_value(option, "school"),
        "Casting time": _payload_value(option, "casting_time"),
        "Range": _payload_value(option, "range"),
        "Duration": _payload_value(option, "duration"),
        "Status": _status_label(option.availability_status),
        "Summary": option.short_summary,
    }


def _row_button_label(option: OptionViewModel) -> str:
    parts = [
        option.name,
        _level_label(option),
        str(_payload_value(option, "school") or "-"),
        str(_payload_value(option, "casting_time") or "-"),
        str(_payload_value(option, "range") or "-"),
        str(_payload_value(option, "duration") or "-"),
        _row_status_label(option),
    ]
    return " | ".join(parts)


def _metadata_line(option: OptionViewModel, label: str) -> str:
    return next(
        (metadata.value for metadata in option.display_metadata if metadata.label == label),
        "",
    )


def _payload_value(option: OptionViewModel, key: str):
    return dict(option.payload).get(key, "")


def _status_label(status: str) -> str:
    labels = {
        "available": "Available",
        "selected": "Selected",
        "unavailable": "Unavailable",
    }
    return labels.get(status, status.title())


def _single_group_key(options: tuple[OptionViewModel, ...], fallback: str) -> str:
    if options and options[0].group_states:
        return options[0].group_states[0].key
    return fallback


def _group_definitions(options: tuple[OptionViewModel, ...]) -> tuple[OptionGroupState, ...]:
    groups = {}
    for option in options:
        for group in option.group_states:
            groups.setdefault(group.key, group)
    return tuple(groups.values())


def _updated_groups(
    selected_groups: dict[str, list[str]],
    group_key: str,
    selection: tuple[str, ...],
) -> dict[str, list[str]]:
    updated = {
        key: list(values)
        for key, values in selected_groups.items()
    }
    updated[group_key] = list(selection)
    return updated


def _level_label(option: OptionViewModel) -> str:
    return _metadata_line(option, "Level") or "Unknown level"


def _level_filter_options(options: tuple[OptionViewModel, ...]) -> list[str]:
    labels_by_sort = set()
    for option in options:
        level = _payload_value(option, "level")
        label = _level_label(option)
        sort_key = level if isinstance(level, int) else 99
        labels_by_sort.add((sort_key, label))
    return [
        label
        for _sort_key, label in sorted(labels_by_sort)
    ]


def _row_status_label(option: OptionViewModel) -> str:
    selected = [group.label for group in option.group_states if group.selected]
    if selected:
        return "Selected: " + ", ".join(selected)
    available = [group.label for group in option.group_states if group.availability_status == "available"]
    if available:
        return "Available: " + ", ".join(available)
    return _status_label(option.availability_status)
