from presentation.compact_catalog import (
    build_legacy_review_option,
    build_named_feature_catalog,
    stable_compact_id,
)


def test_named_feature_catalog_uses_stable_ids_and_missing_description_state():
    selected_id = stable_compact_id("subclass", "Champion", source_label="XPHB")

    first = build_named_feature_catalog(
        ["Champion", "Battle Master"],
        {"Champion": "You focus on physical excellence."},
        kind="subclass",
        selected_ids=[selected_id],
        source_label="XPHB",
        metadata_lookup={"Champion": {"Level": "3"}},
    )
    second = build_named_feature_catalog(
        ["Battle Master", "Champion"],
        {"Champion": "You focus on physical excellence."},
        kind="subclass",
        selected_ids=[selected_id],
        source_label="XPHB",
        metadata_lookup={"Champion": {"Level": "3"}},
    )

    assert {option.name: option.stable_id for option in first} == {option.name: option.stable_id for option in second}
    champion = next(option for option in first if option.name == "Champion")
    battle_master = next(option for option in first if option.name == "Battle Master")
    assert champion.selected is True
    assert champion.availability_status == "selected"
    assert champion.short_summary == "You focus on physical excellence."
    assert dict((metadata.label, metadata.value) for metadata in champion.display_metadata)["Level"] == "3"
    assert battle_master.short_summary == "No description available."
    assert battle_master.full_description == ""


def test_legacy_review_option_preserves_unavailable_saved_selection():
    option = build_legacy_review_option("subclass:xphb|old-subclass", kind="subclass", source_label="XPHB")

    assert option.selected is True
    assert option.availability_status == "unavailable"
    assert "no longer available" in option.short_summary
    assert option.source.source == "XPHB"


def test_streamlit_compact_single_choice_updates_details_and_preserves_rerun_selection():
    from streamlit.testing.v1 import AppTest

    script = '''
import streamlit as st
from presentation.compact_catalog import build_named_feature_catalog
from ui.compact_choice import render_compact_single_choice

options = build_named_feature_catalog(
    ["Champion", "Battle Master"],
    {
        "Champion": "You focus on physical excellence.",
        "Battle Master": "You learn maneuvers fueled by superiority dice.",
    },
    kind="subclass",
    selected_ids=[st.session_state.get("selected", "")],
    source_label="XPHB",
)
selected = render_compact_single_choice(
    options,
    st.session_state.get("selected"),
    state_key="subclass_choice",
    label="Subclass",
)
st.session_state["selected"] = selected
st.button("Unrelated rerun")
'''
    at = AppTest.from_string(script, default_timeout=10).run()

    assert not at.exception
    assert at.selectbox[0].label == "Subclass"

    at.selectbox[0].set_value("subclass:xphb|battle master").run()

    assert at.session_state["selected"] == "subclass:xphb|battle master"
    assert any(markdown.value == "**Battle Master**" for markdown in at.markdown)
    assert any("maneuvers" in markdown.value for markdown in at.markdown)

    at.button[0].click().run()

    assert at.session_state["selected"] == "subclass:xphb|battle master"
    assert any(markdown.value == "**Battle Master**" for markdown in at.markdown)


def test_streamlit_compact_single_choice_preserves_invalid_selection_for_review():
    from streamlit.testing.v1 import AppTest

    script = '''
import streamlit as st
from presentation.compact_catalog import build_named_feature_catalog
from ui.compact_choice import render_compact_single_choice

options = build_named_feature_catalog(["Champion"], {"Champion": "Champion description."}, kind="subclass", source_label="XPHB")
selected = render_compact_single_choice(
    options,
    "subclass:xphb|archived",
    state_key="legacy_subclass",
    label="Subclass",
)
st.session_state["selected"] = selected
'''
    at = AppTest.from_string(script, default_timeout=10).run()

    assert not at.exception
    assert at.session_state["selected"] == "subclass:xphb|archived"
    assert any("no longer available" in caption.value for caption in at.caption)


def test_streamlit_compact_multi_choice_returns_ids_and_shows_collapsed_details():
    from streamlit.testing.v1 import AppTest

    script = '''
import streamlit as st
from presentation.compact_catalog import build_named_feature_catalog
from ui.compact_choice import render_compact_multi_choice

selected_ids = st.session_state.setdefault("selected_ids", [])
options = build_named_feature_catalog(
    ["Acrobatics", "Stealth"],
    {
        "Acrobatics": "Stay on your feet in a tricky situation.",
        "Stealth": "Avoid notice.",
    },
    kind="skill",
    selected_ids=selected_ids,
    source_label="XPHB",
)
updated = render_compact_multi_choice(
    options,
    selected_ids,
    selection_limit=2,
    state_key="skill_choice",
    label="Skills",
)
st.session_state["selected_ids"] = updated
'''
    at = AppTest.from_string(script, default_timeout=10).run()

    assert not at.exception
    at.multiselect[0].set_value(["skill:xphb|acrobatics", "skill:xphb|stealth"]).run()

    assert at.session_state["selected_ids"] == ["skill:xphb|acrobatics", "skill:xphb|stealth"]
    assert "About selected options" in [expander.label for expander in at.expander]
