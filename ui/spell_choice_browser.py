from collections.abc import Iterable

import streamlit as st

from presentation.option_catalog import SpellSelectionGroupSpec, build_grouped_spell_option_catalog
from ui.option_browser import render_unified_spell_picker


def render_spell_choice_browser(
    spells: Iterable[dict],
    groups: Iterable[SpellSelectionGroupSpec],
    selected_groups: dict[str, list[str]],
    *,
    state_key: str,
    label: str,
    search_label: str = "Search spells by name",
) -> dict[str, list[str]]:
    group_specs = tuple(groups or ())
    if not group_specs:
        st.info("No spell choices are available.")
        return selected_groups or {}
    catalog = build_grouped_spell_option_catalog(spells, group_specs, kind="spell")
    return render_unified_spell_picker(
        catalog,
        selected_groups,
        state_key=state_key,
        label=label,
        search_label=search_label,
    )
