from presentation.feat_catalog import build_feat_catalog, feat_stable_id
from presentation.optional_feature_catalog import (
    MISSING_OPTIONAL_FEATURE_DESCRIPTION,
    build_optional_feature_catalog,
    optional_feature_stable_id,
)
from rules.invocations import invocation_eligibility_reasons
from tests.test_level_one_builds import app_data


def test_feat_catalog_keeps_blocked_feats_visible_with_reason():
    options = build_feat_catalog(
        [
            {
                "id": "actor_xphb",
                "name": "Actor",
                "category": "general",
                "description": "You are skilled at mimicry.",
                "ability_increase": {"mode": "choose", "from": ["Charisma"], "amount": 1},
                "eligible": True,
                "supported": True,
                "support": {"selection": "supported"},
            },
            {
                "id": "fey_touched_xphb",
                "name": "Fey-Touched",
                "category": "general",
                "description": "You learn Misty Step and another spell.",
                "eligible": False,
                "supported": True,
                "eligibility_reasons": ["Requires spellcasting or magical prerequisite."],
                "support": {"selection": "supported"},
            },
        ],
        selected_feat_id="actor_xphb",
    )
    by_id = {option.stable_id: option for option in options}

    assert by_id[feat_stable_id("actor_xphb")].availability_status == "selected"
    blocked = by_id[feat_stable_id("fey_touched_xphb")]
    assert blocked.availability_status == "unavailable"
    assert blocked.eligibility_reasons == ("Requires spellcasting or magical prerequisite.",)
    assert dict(blocked.payload)["category"] == "General"


def test_optional_feature_catalog_marks_existing_and_full_options_unavailable():
    options = build_optional_feature_catalog(
        [
            {"name": "Ambush", "category": "Battle Master maneuver", "eligible": True},
            {"name": "Parry", "category": "Battle Master maneuver", "eligible": True},
            {"name": "Trip Attack", "category": "Battle Master maneuver", "eligible": True},
        ],
        selected_names=["Ambush"],
        selection_limit=1,
        kind="maneuver",
        existing_names=["Parry"],
    )
    by_id = {option.stable_id: option for option in options}

    assert by_id[optional_feature_stable_id("maneuver", "Ambush")].availability_status == "selected"
    assert by_id[optional_feature_stable_id("maneuver", "Parry")].eligibility_reasons == ("Already selected for this character.",)
    trip = by_id[optional_feature_stable_id("maneuver", "Trip Attack")]
    assert trip.availability_status == "unavailable"
    assert "Selection is full (1/1)" in trip.eligibility_reasons[0]
    assert trip.full_description == MISSING_OPTIONAL_FEATURE_DESCRIPTION


def test_imported_battle_master_maneuvers_include_rules_descriptions():
    data = app_data()
    fighter = data["classes_by_name"]["Fighter"]
    battle_master = next(subclass for subclass in fighter["subclasses"] if subclass["short_name"] == "Battle Master")
    maneuver_rule = battle_master["subclass_options"]["maneuvers"]
    by_name = {
        option["name"]: option
        for option in maneuver_rule["options"]
    }

    assert len(by_name) == 20
    assert "Superiority Die" in by_name["Ambush"]["description"]
    assert "saving throw" in by_name["Trip Attack"]["description"]
    assert "{@" not in by_name["Commander's Strike"]["description"]


def test_optional_feature_catalog_uses_imported_descriptions_when_available():
    data = app_data()
    fighter = data["classes_by_name"]["Fighter"]
    battle_master = next(subclass for subclass in fighter["subclasses"] if subclass["short_name"] == "Battle Master")
    maneuver_rule = battle_master["subclass_options"]["maneuvers"]

    catalog = build_optional_feature_catalog(
        maneuver_rule["options"],
        selected_names=[],
        selection_limit=3,
        kind="maneuver",
    )
    ambush = next(option for option in catalog if option.name == "Ambush")

    assert ambush.full_description != MISSING_OPTIONAL_FEATURE_DESCRIPTION
    assert "Superiority Die" in ambush.full_description


def test_invocation_eligibility_reasons_explain_missing_prerequisites():
    character = {"level": 5, "class_options": {"eldritch_invocations": []}, "spells": {"cantrips": []}}
    invocation = {
        "name": "Thirsting Blade",
        "prerequisites": {"minimum_warlock_level": 5, "required_invocations": ["Pact of the Blade"]},
    }

    reasons = invocation_eligibility_reasons(character, invocation, 5)

    assert reasons == ["Requires invocation: Pact of the Blade."]


def test_invocation_eligibility_reasons_explain_damage_cantrip_requirement():
    character = {"level": 2, "class_options": {"eldritch_invocations": []}, "spells": {"cantrips": []}}
    invocation = {
        "name": "Agonizing Blast",
        "prerequisites": {"minimum_warlock_level": 2, "requires_damage_cantrip": True},
    }

    reasons = invocation_eligibility_reasons(character, invocation, 2)

    assert reasons == ["Requires a selected damaging cantrip."]


def test_streamlit_medium_single_browser_selects_feat():
    from streamlit.testing.v1 import AppTest

    script = '''
import streamlit as st
from presentation.feat_catalog import build_feat_catalog
from ui.medium_option_browser import BrowserFilter, render_medium_single_option_browser

selected = st.session_state.get("selected", "")
catalog = build_feat_catalog([
    {"id": "actor_xphb", "name": "Actor", "category": "general", "description": "Mimicry.", "eligible": True, "supported": True, "support": {"selection": "supported"}},
    {"id": "unsupported_xphb", "name": "Unsupported", "category": "general", "description": "Not ready.", "eligible": False, "supported": True, "eligibility_reasons": ["Blocked."], "support": {"selection": "supported"}},
], selected_feat_id=selected)
updated = render_medium_single_option_browser(
    catalog,
    selected,
    state_key="feat_test",
    label="General feat",
    search_label="Search feats by name",
    filters=(BrowserFilter("Filter by category", "category", "All categories"),),
    choose_label="Choose feat",
)
if updated != selected:
    st.session_state["selected"] = updated
    st.rerun()
'''
    at = AppTest.from_string(script, default_timeout=10).run()

    assert not at.exception
    at = at.button(key="feat_test_inspect_feat:actor_xphb").click().run()
    at = at.button(key="feat_test_choose_feat:actor_xphb").click().run()

    assert at.session_state["selected"] == "actor_xphb"
    assert at.button(key="feat_test_clear_feat:actor_xphb").label == "Clear choice"
