import streamlit as st

from presentation.equipment_catalog import option_value
from presentation.option_models import OptionViewModel


def render_equipment_browser(
    options: tuple[OptionViewModel, ...],
    custom_equipment: list[str],
    *,
    state_key: str,
    label: str = "Custom equipment",
) -> list[str]:
    st.write(f"**{label}**")
    selected = [item for item in custom_equipment or [] if item]
    _initialize_state(state_key, options, selected)

    left, right = st.columns([3, 2], vertical_alignment="top")
    with left:
        filtered = _render_controls(state_key, options)
        st.caption(f"Custom equipment: {len(selected)} item(s)")
        st.caption("Selected: " + (", ".join(selected) if selected else "none"))
        inspected_id = _render_table(state_key, filtered)
        if inspected_id:
            st.session_state[f"{state_key}_inspected_id"] = inspected_id

    inspected = _option_by_id(options, st.session_state.get(f"{state_key}_inspected_id", ""))
    with right:
        updated = _render_inspector(inspected, selected, state_key=state_key)
    return updated or selected


def _initialize_state(state_key: str, options: tuple[OptionViewModel, ...], selected: list[str]) -> None:
    st.session_state.setdefault(f"{state_key}_search", "")
    st.session_state.setdefault(f"{state_key}_status", "All items")
    inspected_key = f"{state_key}_inspected_id"
    current_id = st.session_state.get(inspected_key, "")
    if current_id and _option_by_id(options, current_id):
        return
    initial = next((option for option in options if option.name in set(selected)), None)
    if initial is None:
        initial = next((option for option in options if option.availability_status == "available"), None)
    st.session_state[inspected_key] = initial.stable_id if initial else ""


def _render_controls(state_key: str, options: tuple[OptionViewModel, ...]) -> tuple[OptionViewModel, ...]:
    st.text_input("Search equipment by name", key=f"{state_key}_search")
    status_options = ["All items", "Custom only", "Default package only", "Available to add"]
    current = st.session_state.get(f"{state_key}_status", "All items")
    if current not in status_options:
        st.session_state[f"{state_key}_status"] = "All items"
    st.selectbox("Filter by equipment status", status_options, key=f"{state_key}_status")

    search = st.session_state.get(f"{state_key}_search", "").strip().casefold()
    status = st.session_state.get(f"{state_key}_status", "All items")
    filtered = [
        option
        for option in options
        if (not search or search in option.name.casefold())
        and _matches_status(option, status)
    ]
    if not filtered:
        st.info("No equipment matches the current filters.")
    return tuple(filtered)


def _render_table(state_key: str, options: tuple[OptionViewModel, ...]) -> str:
    inspected_id = ""
    with st.container(height=360):
        st.caption("Equipment | Category | Provenance | Status")
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
    state_key: str,
) -> list[str] | None:
    if option is None:
        st.info("Select equipment to inspect it.")
        return None

    st.subheader(option.name)
    st.write(f"**Status:** {_status_label(option.availability_status)}")
    for reason in option.eligibility_reasons:
        st.caption(reason)

    if option.selected:
        if st.button(
            "Remove custom equipment",
            key=f"{state_key}_remove_{option.stable_id}",
            icon=":material/remove:",
        ):
            return [item for item in selected if item != option_value(option)]
    else:
        if st.button(
            "Add custom equipment",
            key=f"{state_key}_add_{option.stable_id}",
            icon=":material/add:",
            disabled=option.availability_status != "available",
        ):
            value = option_value(option)
            return [*selected, value] if value not in selected else selected

    for metadata in option.display_metadata:
        st.write(f"**{metadata.label}:** {metadata.value}")
    st.write(f"**Source:** {option.source.source or '-'}")
    st.caption(option.full_description)
    return None


def _matches_status(option: OptionViewModel, status: str) -> bool:
    payload = dict(option.payload)
    if status == "Custom only":
        return option.selected
    if status == "Default package only":
        return bool(payload.get("package_included"))
    if status == "Available to add":
        return option.availability_status == "available"
    return True


def _row_button_label(option: OptionViewModel) -> str:
    category = _metadata_line(option, "Category") or "-"
    provenance = _metadata_line(option, "Provenance") or "-"
    return f"{option.name} | {category} | {provenance} | {_status_label(option.availability_status)}"


def _metadata_line(option: OptionViewModel, label: str) -> str:
    return next(
        (metadata.value for metadata in option.display_metadata if metadata.label == label),
        "",
    )


def _option_by_id(options: tuple[OptionViewModel, ...], stable_id: str) -> OptionViewModel | None:
    return next((option for option in options if option.stable_id == stable_id), None)


def _status_label(status: str) -> str:
    labels = {
        "available": "Available",
        "selected": "Selected",
        "unavailable": "Unavailable",
    }
    return labels.get(status, status.title())
