import streamlit as st

from presentation.compact_catalog import build_legacy_review_option
from presentation.option_models import OptionViewModel


def render_compact_single_choice(
    options: tuple[OptionViewModel, ...],
    selected_id: str | None,
    *,
    state_key: str,
    label: str,
    placeholder: str = "Choose an option",
    control: str = "selectbox",
    detail_label: str = "View full details",
) -> str | None:
    options = _options_with_legacy_review(options, [selected_id] if selected_id else [])
    ids = [option.stable_id for option in options]
    labels = {option.stable_id: option.name for option in options}
    default_id = selected_id if selected_id in ids else None
    widget_key = f"{state_key}_single"
    if st.session_state.get(widget_key) not in {None, *ids}:
        st.session_state.pop(widget_key, None)

    if control == "segmented" and len(options) <= 5:
        selected = st.segmented_control(
            label,
            ids,
            default=default_id,
            format_func=lambda option_id: labels.get(option_id, option_id),
            key=widget_key,
        )
    else:
        selected = st.selectbox(
            label,
            ids,
            index=ids.index(default_id) if default_id in ids else None,
            placeholder=placeholder,
            format_func=lambda option_id: labels.get(option_id, option_id),
            key=widget_key,
        )

    selected_option = _option_by_id(options, selected)
    if selected_option is None:
        st.caption(placeholder)
        return selected
    _render_option_detail(selected_option, detail_label=detail_label)
    return selected


def render_compact_multi_choice(
    options: tuple[OptionViewModel, ...],
    selected_ids: list[str],
    *,
    selection_limit: int,
    state_key: str,
    label: str,
    detail_label: str = "View full details",
) -> list[str]:
    selected_ids = [item for item in selected_ids or [] if item]
    options = _options_with_legacy_review(options, selected_ids)
    ids = [option.stable_id for option in options]
    labels = {option.stable_id: option.name for option in options}
    default = [item for item in selected_ids if item in ids]
    widget_key = f"{state_key}_multi"
    current_widget_value = st.session_state.get(widget_key)
    if isinstance(current_widget_value, list) and any(item not in ids for item in current_widget_value):
        st.session_state.pop(widget_key, None)

    st.caption(f"{len(default)} / {selection_limit} selected")
    selected = st.multiselect(
        label,
        ids,
        default=default,
        max_selections=selection_limit or None,
        format_func=lambda option_id: labels.get(option_id, option_id),
        key=widget_key,
    )
    if selection_limit and len(selected) > selection_limit:
        st.warning(f"Choose up to {selection_limit}.")
        selected = selected[:selection_limit]

    selected_options = [
        option
        for option in options
        if option.stable_id in set(selected)
    ]
    if selected_options:
        with st.expander("About selected options", expanded=False):
            for option in selected_options:
                _render_option_detail(option, detail_label=detail_label)
    return list(selected)


def _options_with_legacy_review(
    options: tuple[OptionViewModel, ...],
    selected_ids: list[str],
) -> tuple[OptionViewModel, ...]:
    existing_ids = {option.stable_id for option in options}
    legacy = [
        build_legacy_review_option(selected_id)
        for selected_id in selected_ids
        if selected_id and selected_id not in existing_ids
    ]
    return tuple(legacy) + tuple(options)


def _option_by_id(options: tuple[OptionViewModel, ...], stable_id: str | None) -> OptionViewModel | None:
    return next((option for option in options if option.stable_id == stable_id), None)


def _render_option_detail(option: OptionViewModel, *, detail_label: str = "View full details") -> None:
    with st.container(border=True):
        st.markdown(f"**{option.name}**")
        st.caption(f"Status: {_status_label(option.availability_status)}")
        for reason in option.eligibility_reasons:
            st.caption(reason)
        if option.short_summary:
            st.write(option.short_summary)
        for metadata in option.display_metadata[:4]:
            st.write(f"**{metadata.label}:** {metadata.value}")
        if option.source.source:
            st.caption(f"Source: {option.source.source}")
        if option.full_description:
            with st.expander(detail_label):
                st.markdown(option.full_description)
        elif option.short_summary == "No description available.":
            st.caption("No description available.")


def _status_label(status: str) -> str:
    labels = {
        "available": "Available",
        "selected": "Selected",
        "unavailable": "Unavailable",
    }
    return labels.get(status, status.title())
