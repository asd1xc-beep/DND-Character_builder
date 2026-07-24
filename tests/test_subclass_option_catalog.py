from presentation.compact_catalog import (
    build_subclass_catalog,
    option_value,
    subclass_stable_id,
)
from rules.level_up import (
    commit_level_up_draft,
    create_level_up_draft,
    finalize_level_up,
    get_level_up_plan,
    resolve_pending_choice,
)
from tests.test_level_one_builds import app_data, finalized
from tests.test_level_up import level_one_fighter


def metadata_for(option):
    return {metadata.label: metadata.value for metadata in option.display_metadata}


def test_subclass_catalog_builds_fighter_target_level_progression_and_follow_ups():
    data = app_data()
    fighter = data["classes_by_name"]["Fighter"]

    catalog = build_subclass_catalog(fighter, 3, option_names=["Battle Master", "Champion", "Eldritch Knight", "Psi Warrior"])

    assert [option.name for option in catalog] == ["Battle Master", "Champion", "Eldritch Knight", "Psi Warrior"]
    battle_master = next(option for option in catalog if option.name == "Battle Master")
    metadata = metadata_for(battle_master)
    assert battle_master.source.source == "XPHB"
    assert "Combat Superiority" in metadata["Target level gains"]
    assert "Maneuvers" in metadata["Follow-up choices"]
    assert "Student of War" in battle_master.full_description
    assert "Level 7: Know Your Enemy" in battle_master.full_description


def test_subclass_catalog_includes_full_caster_subclass_details():
    data = app_data()
    cleric = data["classes_by_name"]["Cleric"]

    catalog = build_subclass_catalog(cleric, 3, selected_name="Life Domain")
    life_domain = next(option for option in catalog if option.name == "Life Domain")

    assert life_domain.selected is True
    assert life_domain.availability_status == "selected"
    assert "Life Domain focuses on the positive energy" in life_domain.short_summary
    assert "Life Domain Spells" in metadata_for(life_domain)["Target level gains"]
    assert "Preserve Life" in life_domain.full_description


def test_subclass_catalog_surfaces_spell_choice_follow_ups_without_inventing_rules():
    data = app_data()
    wizard = data["classes_by_name"]["Wizard"]

    catalog = build_subclass_catalog(wizard, 3, selected_name="Abjurer")
    abjurer = next(option for option in catalog if option.name == "Abjurer")

    assert "Choose 2 Abjurer spells" in metadata_for(abjurer)["Follow-up choices"]
    assert "Choose 2 Abjurer spells" in abjurer.full_description
    assert option_value(abjurer) == "Abjurer"
    assert subclass_stable_id(wizard, "Abjurer") == abjurer.stable_id


def test_subclass_option_selection_remains_draft_only_until_commit():
    data = app_data()
    character = level_one_fighter()
    finalized(character, data)
    finalize_level_up(character, get_level_up_plan(character, 2, data))
    finalized(character, data)
    draft = create_level_up_draft(character, 3, data)
    choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "subclass_choice")
    fighter = data["classes_by_name"]["Fighter"]
    catalog = build_subclass_catalog(fighter, 3, option_names=choice["options"])
    champion = next(option for option in catalog if option.name == "Champion")

    assert resolve_pending_choice(draft, choice["id"], option_value(champion), choice)
    assert draft["can_finalize"]
    assert character["subclass"] == ""

    result = commit_level_up_draft(character, draft)

    assert result["ok"]
    assert character["subclass"] == "Champion"


def test_subclass_option_selection_can_be_discarded_without_character_changes():
    data = app_data()
    character = level_one_fighter()
    finalized(character, data)
    finalize_level_up(character, get_level_up_plan(character, 2, data))
    finalized(character, data)
    draft = create_level_up_draft(character, 3, data)
    choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "subclass_choice")

    assert resolve_pending_choice(draft, choice["id"], "Champion", choice)

    draft = None

    assert draft is None
    assert character["level"] == 2
    assert character["subclass"] == ""
    assert character["pending_choices"] == []


def test_streamlit_subclass_choice_uses_compact_inspector_and_resolves_draft():
    from streamlit.testing.v1 import AppTest

    script = '''
import streamlit as st
from app import render_level_choice_controls
from tests.test_level_one_builds import app_data

data = app_data()
fighter = data["classes_by_name"]["Fighter"]
draft = st.session_state.setdefault("draft", {
    "class_name": "Fighter",
    "target_level": 3,
    "pending_choices": [{
        "id": "fighter_3_subclass",
        "type": "subclass_choice",
        "name": "Choose Fighter subclass",
        "options": [subclass["name"] for subclass in fighter["subclasses"]],
        "status": "unresolved",
    }],
    "resolved_choices": [],
    "can_finalize": False,
})
render_level_choice_controls(draft, draft["pending_choices"], data)
'''
    at = AppTest.from_string(script, default_timeout=10).run()

    assert not at.exception
    assert at.selectbox[0].label == "Choose Fighter subclass"
    assert len(at.selectbox[0].options) == 4

    at.selectbox[0].set_value("subclass:battle_master_xphb").run()

    choice = at.session_state["draft"]["pending_choices"][0]
    assert choice["status"] == "resolved"
    assert choice["value"] == "Battle Master"
    assert any(markdown.value == "**Battle Master**" for markdown in at.markdown)
    assert any("Combat Superiority" in element.value for element in [*at.markdown, *at.caption])

    at.selectbox[0].set_value("subclass:champion_xphb").run()

    choice = at.session_state["draft"]["pending_choices"][0]
    assert choice["status"] == "resolved"
    assert choice["value"] == "Champion"
    assert any(markdown.value == "**Champion**" for markdown in at.markdown)
