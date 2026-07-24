from presentation.weapon_mastery_catalog import build_weapon_mastery_catalog, weapon_mastery_stable_id
from services.data_loader import clean_5etools_text, load_weapon_masteries


WEAPONS = [
    {"name": "Dagger", "category": "Simple", "damage": "1d4", "damage_type": "P", "mastery": "Nick"},
    {"name": "Longsword", "category": "Martial", "damage": "1d8", "damage_type": "S", "mastery": "Sap"},
    {"name": "Shortsword", "category": "Martial", "damage": "1d6", "damage_type": "P", "mastery": "Vex"},
]

MASTERIES = [
    {"name": "Nick", "description": "You can make the extra Light attack as part of the Attack action.", "source": "XPHB", "raw_ref": "Nick|XPHB"},
    {"name": "Sap", "description": "The target has Disadvantage on its next attack roll.", "source": "XPHB", "raw_ref": "Sap|XPHB"},
    {"name": "Vex", "description": "You gain Advantage on your next attack against that creature.", "source": "XPHB", "raw_ref": "Vex|XPHB"},
]


def test_weapon_mastery_catalog_shows_eligible_selected_and_blocked_weapons():
    options = build_weapon_mastery_catalog(
        WEAPONS,
        eligible_names=["Dagger", "Shortsword"],
        selected_names=["Dagger"],
        selection_limit=2,
        mastery_descriptions=MASTERIES,
    )
    by_id = {option.stable_id: option for option in options}

    dagger = by_id[weapon_mastery_stable_id("Dagger")]
    shortsword = by_id[weapon_mastery_stable_id("Shortsword")]
    longsword = by_id[weapon_mastery_stable_id("Longsword")]

    assert dagger.availability_status == "selected"
    assert shortsword.availability_status == "available"
    assert longsword.availability_status == "unavailable"
    assert "Requires proficiency" in longsword.eligibility_reasons[0]
    assert "Disadvantage" in longsword.full_description


def test_weapon_mastery_catalog_disables_add_when_selection_is_full():
    options = build_weapon_mastery_catalog(
        WEAPONS,
        eligible_names=["Dagger", "Shortsword"],
        selected_names=["Dagger"],
        selection_limit=1,
        mastery_descriptions=MASTERIES,
    )
    shortsword = next(option for option in options if option.name == "Shortsword")

    assert shortsword.availability_status == "unavailable"
    assert "Selection is full (1/1)" in shortsword.eligibility_reasons[0]


def test_weapon_mastery_catalog_preserves_legacy_saved_selection_for_removal():
    options = build_weapon_mastery_catalog(
        WEAPONS,
        eligible_names=["Dagger"],
        selected_names=["Old Mastery"],
        selection_limit=1,
        mastery_descriptions=MASTERIES,
    )
    old = next(option for option in options if option.name == "Old Mastery")

    assert old.selected is True
    assert old.availability_status == "selected"
    assert old.full_description


def test_weapon_mastery_descriptions_load_from_raw_source_data():
    records = load_weapon_masteries("5e.tools 2024 import")
    by_name = {record["name"]: record for record in records}

    assert "Nick" in by_name
    assert "Attack action" in by_name["Nick"]["description"]
    assert "{@" not in by_name["Nick"]["description"]


def test_clean_5etools_text_keeps_display_text_for_tags():
    text = clean_5etools_text("Make an {@action Attack|XPHB}; save is {@dc 8} plus {@variantrule Proficiency|XPHB|Proficiency Bonus}.")

    assert text == "Make an Attack; save is DC 8 plus Proficiency Bonus."


def test_streamlit_medium_browser_smoke_adds_weapon_mastery():
    from streamlit.testing.v1 import AppTest

    script = '''
import streamlit as st
from presentation.weapon_mastery_catalog import build_weapon_mastery_catalog
from ui.medium_option_browser import BrowserFilter, render_medium_option_browser

selected = st.session_state.get("selected", [])
catalog = build_weapon_mastery_catalog(
    [{"name": "Dagger", "category": "Simple", "damage": "1d4", "damage_type": "P", "mastery": "Nick"}],
    eligible_names=["Dagger"],
    selected_names=selected,
    selection_limit=1,
    mastery_descriptions=[{"name": "Nick", "description": "Light extra attack.", "source": "XPHB", "raw_ref": "Nick|XPHB"}],
)
updated = render_medium_option_browser(
    catalog,
    selected,
    selection_limit=1,
    state_key="mastery_test",
    label="Weapon Mastery",
    search_label="Search weapons by name",
    filters=(BrowserFilter("Filter by mastery", "mastery", "All masteries"),),
    add_label="Add mastery",
    remove_label="Remove mastery",
)
if updated != selected:
    st.session_state["selected"] = updated
    st.rerun()
'''
    at = AppTest.from_string(script, default_timeout=10).run()

    assert not at.exception
    at = at.button(key="mastery_test_inspect_weapon_mastery:dagger").click().run()
    at = at.button(key="mastery_test_add_weapon_mastery:dagger").click().run()
    assert at.session_state["selected"] == ["Dagger"]

    assert at.button(key="mastery_test_remove_weapon_mastery:dagger").label == "Remove mastery"
