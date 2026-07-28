def test_cancel_clears_only_pdf_import_owned_session_state():
    from streamlit.testing.v1 import AppTest

    script = '''
import streamlit as st
from ui.pdf_import import clear_pdf_import_state

st.session_state.character = {"name": "Active Hero"}
st.session_state.level_up_draft = {"target_level": 4}
st.session_state.pdf_import_draft = {"candidate": {"name": "Recovered Hero"}}
st.session_state.pdf_import_name = "Recovered Hero"
clear_pdf_import_state()
st.write("done")
'''
    at = AppTest.from_string(script, default_timeout=10).run()

    assert not at.exception
    assert at.session_state["character"] == {"name": "Active Hero"}
    assert at.session_state["level_up_draft"] == {"target_level": 4}
    assert "pdf_import_draft" not in at.session_state
    assert "pdf_import_name" not in at.session_state


def test_ready_confirmation_adopts_candidate_and_clears_stale_character_state():
    from streamlit.testing.v1 import AppTest

    script = '''
import streamlit as st
from types import SimpleNamespace
from tests.test_level_one_builds import app_data, finalized
from tests.test_level_up import level_one_fighter
from ui.pdf_import import render_adoption_actions

if "character" not in st.session_state:
    st.session_state.character = {"name": "Active Hero"}
    st.session_state.level_up_draft = {"target_level": 9}
    st.session_state.old_character_widget = "stale"
candidate = level_one_fighter()
candidate["name"] = "Recovered Hero"
finalized(candidate, app_data())
result = SimpleNamespace(
    can_confirm=True,
    recovered={"identity": "Recovered"},
    candidate_character=candidate,
    issues=[],
    comparisons=[],
)
import_result = SimpleNamespace(
    source_kind="compatible_form",
    status="review_required",
    payload_info={"signature": "abc"},
    passthrough_fields={"Alignment": "Neutral Good"},
    issues=[],
)
render_adoption_actions(result, import_result, app_data())
'''
    at = AppTest.from_string(script, default_timeout=10).run()
    create_button = next(
        button for button in at.button
        if button.label == "Create working character from PDF"
    )
    at = create_button.click().run()

    assert not at.exception
    assert at.session_state["character"]["name"] == "Recovered Hero"
    assert at.session_state["character"]["schema_version"] == 5
    assert at.session_state["character"]["pdf_passthrough_fields"] == {
        "Alignment": "Neutral Good"
    }
    assert at.session_state["level_up_draft"] is None
    assert "old_character_widget" not in at.session_state
    assert at.session_state["requested_builder_tab"] == "Character Sheet"


def test_blocked_confirmation_button_is_disabled():
    from streamlit.testing.v1 import AppTest

    script = '''
from types import SimpleNamespace
from ui.pdf_import import render_adoption_actions

render_adoption_actions(SimpleNamespace(
    can_confirm=False,
    recovered={"identity": "Recovered"},
    candidate_character={"name": "Recovered Hero"},
), SimpleNamespace(source_kind="compatible_form"), {})
'''
    at = AppTest.from_string(script, default_timeout=10).run()
    create_button = next(
        button for button in at.button
        if button.label == "Create working character from PDF"
    )

    assert not at.exception
    assert create_button.disabled
