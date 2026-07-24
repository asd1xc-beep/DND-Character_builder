import streamlit as st

from presentation.attack_profile_catalog import build_attack_profile_catalog
from rules.attack_profiles import cantrip_attack_profile_options, weapon_attack_profile_options


def render_pdf_export_options(character: dict, data: dict, *, state_key: str = "pdf_export_options") -> None:
    preferences = character.setdefault("presentation_preferences", {})
    weapon_profiles = weapon_attack_profile_options(character, data)
    cantrip_profiles = cantrip_attack_profile_options(character)

    st.caption("These choices only affect the exported PDF attack rows.")
    _render_profile_select(
        "Primary weapon",
        preferences,
        "primary_weapon",
        weapon_profiles,
        state_key=f"{state_key}_primary_weapon",
        empty_message="No carried weapon has enough rules data for an attack row.",
    )
    _render_profile_select(
        "Featured cantrip",
        preferences,
        "featured_cantrip",
        cantrip_profiles,
        state_key=f"{state_key}_featured_cantrip",
        empty_message="No selected damaging cantrip is available for an attack row.",
    )


def _render_profile_select(
    label: str,
    preferences: dict,
    preference_key: str,
    profiles: list[dict],
    *,
    state_key: str,
    empty_message: str,
) -> None:
    options = build_attack_profile_catalog(
        profiles,
        selected_name=preferences.get(preference_key, ""),
        kind=preference_key,
    )
    names = [option.name for option in options]
    if not names:
        preferences.pop(preference_key, None)
        st.caption(empty_message)
        return

    current = preferences.get(preference_key, "")
    if current not in names:
        current = names[0]
        preferences[preference_key] = current
    index = names.index(current)
    selected = st.selectbox(
        label,
        names,
        index=index,
        key=state_key,
        format_func=lambda name: _profile_label(name, profiles),
    )
    preferences[preference_key] = selected


def _profile_label(name: str, profiles: list[dict]) -> str:
    profile = next((item for item in profiles if item.get("name") == name), {})
    details = " | ".join(
        part
        for part in (
            str(profile.get("attack_display") or ""),
            str(profile.get("damage_display") or ""),
        )
        if part
    )
    return f"{name} ({details})" if details else name
