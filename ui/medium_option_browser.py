from dataclasses import dataclass

import streamlit as st

from presentation.option_models import OptionViewModel


@dataclass(frozen=True)
class BrowserFilter:
    label: str
    payload_key: str
    all_label: str


def render_medium_option_browser(
    options: tuple[OptionViewModel, ...],
    selected_values: list[str],
    *,
    selection_limit: int,
    state_key: str,
    label: str,
    search_label: str,
    filters: tuple[BrowserFilter, ...] = (),
    add_label: str = "Add",
    remove_label: str = "Remove",
) -> list[str]:
    st.write(f"**{label}**")
    selected = [value for value in selected_values or [] if value]
    _initialize_state(state_key, options, selected)

    left, right = st.columns([3, 2], vertical_alignment="top")
    with left:
        filtered = _render_controls(state_key, options, search_label, filters)
        limit_label = str(selection_limit) if selection_limit else "any"
        st.caption(f"{len(selected)} / {limit_label} selected")
        st.caption("Selected: " + (", ".join(selected) if selected else "none"))
        inspected_id = _render_table(state_key, filtered)
        if inspected_id:
            st.session_state[f"{state_key}_inspected_id"] = inspected_id

    inspected = _option_by_id(options, st.session_state.get(f"{state_key}_inspected_id", ""))
    with right:
        updated = _render_inspector(
            inspected,
            selected,
            selection_limit=selection_limit,
            state_key=state_key,
            add_label=add_label,
            remove_label=remove_label,
        )
    return updated or selected


def render_medium_single_option_browser(
    options: tuple[OptionViewModel, ...],
    selected_value: str | None,
    *,
    state_key: str,
    label: str,
    search_label: str,
    filters: tuple[BrowserFilter, ...] = (),
    choose_label: str = "Choose",
    clear_label: str = "Clear choice",
) -> str | None:
    st.write(f"**{label}**")
    selected = str(selected_value or "")
    _initialize_state(state_key, options, [selected] if selected else [])

    left, right = st.columns([3, 2], vertical_alignment="top")
    with left:
        filtered = _render_controls(state_key, options, search_label, filters)
        st.caption("Selected: " + (selected if selected else "none"))
        inspected_id = _render_table(state_key, filtered)
        if inspected_id:
            st.session_state[f"{state_key}_inspected_id"] = inspected_id

    inspected = _option_by_id(options, st.session_state.get(f"{state_key}_inspected_id", ""))
    with right:
        updated = _render_single_inspector(
            inspected,
            selected,
            state_key=state_key,
            choose_label=choose_label,
            clear_label=clear_label,
        )
    return selected if updated is None else updated


def _initialize_state(state_key: str, options: tuple[OptionViewModel, ...], selected: list[str]) -> None:
    st.session_state.setdefault(f"{state_key}_search", "")
    st.session_state.setdefault(f"{state_key}_status", "All statuses")
    inspected_key = f"{state_key}_inspected_id"
    current_id = st.session_state.get(inspected_key, "")
    if current_id and _option_by_id(options, current_id):
        return
    selected_set = set(selected)
    initial = next((option for option in options if option_value(option) in selected_set), None)
    if initial is None:
        initial = next((option for option in options if option.availability_status == "available"), None)
    st.session_state[inspected_key] = initial.stable_id if initial else ""


def _render_controls(
    state_key: str,
    options: tuple[OptionViewModel, ...],
    search_label: str,
    filters: tuple[BrowserFilter, ...],
) -> tuple[OptionViewModel, ...]:
    st.text_input(search_label, key=f"{state_key}_search")
    status_options = ["All statuses", "Available", "Selected", "Unavailable"]
    if st.session_state.get(f"{state_key}_status") not in status_options:
        st.session_state[f"{state_key}_status"] = "All statuses"
    st.selectbox("Filter by status", status_options, key=f"{state_key}_status")

    for filter_spec in filters:
        key = f"{state_key}_filter_{filter_spec.payload_key}"
        values = [filter_spec.all_label] + sorted({
            str(_payload_value(option, filter_spec.payload_key))
            for option in options
            if _payload_value(option, filter_spec.payload_key)
        })
        if st.session_state.get(key) not in values:
            st.session_state[key] = filter_spec.all_label
        st.selectbox(filter_spec.label, values, key=key)

    search = st.session_state.get(f"{state_key}_search", "").strip().casefold()
    status = st.session_state.get(f"{state_key}_status", "All statuses")
    filtered = [
        option
        for option in options
        if (not search or search in option.name.casefold())
        and _matches_status(option, status)
        and _matches_filters(option, state_key, filters)
    ]
    if not filtered:
        st.info("No options match the current filters.")
    return tuple(filtered)


def _render_table(state_key: str, options: tuple[OptionViewModel, ...]) -> str:
    inspected_id = ""
    with st.container(height=360):
        st.caption("Option | Details | Status")
        for option in options:
            if st.button(
                _row_button_label(option),
                key=f"{state_key}_inspect_{option.stable_id}",
                width="stretch",
            ):
                inspected_id = option.stable_id
    return inspected_id


def _render_inspector(
    option: OptionViewModel | None,
    selected: list[str],
    *,
    selection_limit: int,
    state_key: str,
    add_label: str,
    remove_label: str,
) -> list[str] | None:
    if option is None:
        st.info("Select an option to inspect it.")
        return None

    value = option_value(option)
    st.subheader(option.name)
    st.write(f"**Status:** {_status_label(option.availability_status)}")
    for reason in option.eligibility_reasons:
        st.caption(reason)

    if value in selected:
        if st.button(
            remove_label,
            key=f"{state_key}_remove_{option.stable_id}",
            icon=":material/remove:",
        ):
            return [item for item in selected if item != value]
    else:
        disabled = option.availability_status != "available" or (selection_limit and len(selected) >= selection_limit)
        if st.button(
            add_label,
            key=f"{state_key}_add_{option.stable_id}",
            icon=":material/add:",
            disabled=disabled,
        ):
            return [*selected, value] if value not in selected else selected

    for metadata in option.display_metadata:
        st.write(f"**{metadata.label}:** {metadata.value}")
    st.write(f"**Source:** {option.source.source or '-'}")
    if option.full_description:
        st.markdown(option.full_description)
    else:
        st.caption("No description is available for this option.")
    return None


def _render_single_inspector(
    option: OptionViewModel | None,
    selected: str,
    *,
    state_key: str,
    choose_label: str,
    clear_label: str,
) -> str | None:
    if option is None:
        st.info("Select an option to inspect it.")
        return None

    value = option_value(option)
    st.subheader(option.name)
    st.write(f"**Status:** {_status_label(option.availability_status)}")
    for reason in option.eligibility_reasons:
        st.caption(reason)

    if value == selected:
        if st.button(
            clear_label,
            key=f"{state_key}_clear_{option.stable_id}",
            icon=":material/remove:",
        ):
            return ""
    else:
        if st.button(
            choose_label,
            key=f"{state_key}_choose_{option.stable_id}",
            icon=":material/check:",
            disabled=option.availability_status != "available",
        ):
            return value

    for metadata in option.display_metadata:
        st.write(f"**{metadata.label}:** {metadata.value}")
    st.write(f"**Source:** {option.source.source or '-'}")
    if option.full_description:
        st.markdown(option.full_description)
    else:
        st.caption("No description is available for this option.")
    return None


def _row_button_label(option: OptionViewModel) -> str:
    details = " | ".join(
        metadata.value
        for metadata in option.display_metadata[:3]
        if metadata.value
    )
    return f"{option.name} | {details or '-'} | {_status_label(option.availability_status)}"


def _matches_status(option: OptionViewModel, status: str) -> bool:
    if status == "Available":
        return option.availability_status == "available"
    if status == "Selected":
        return option.selected
    if status == "Unavailable":
        return option.availability_status == "unavailable"
    return True


def _matches_filters(option: OptionViewModel, state_key: str, filters: tuple[BrowserFilter, ...]) -> bool:
    for filter_spec in filters:
        selected = st.session_state.get(f"{state_key}_filter_{filter_spec.payload_key}", filter_spec.all_label)
        if selected != filter_spec.all_label and _payload_value(option, filter_spec.payload_key) != selected:
            return False
    return True


def _option_by_id(options: tuple[OptionViewModel, ...], stable_id: str) -> OptionViewModel | None:
    return next((option for option in options if option.stable_id == stable_id), None)


def option_value(option: OptionViewModel) -> str:
    return str(dict(option.payload).get("value", option.name))


def _payload_value(option: OptionViewModel, key: str):
    return dict(option.payload).get(key, "")


def _status_label(status: str) -> str:
    labels = {
        "available": "Available",
        "selected": "Selected",
        "unavailable": "Unavailable",
    }
    return labels.get(status, status.title())
