from presentation.proficiency_catalog import (
    build_prefixed_skill_tool_catalog,
    build_skill_catalog,
    build_tool_catalog,
    compact_selected_ids,
    values_from_ids,
)
from services.data_loader import FIVETOOLS_SOURCE, load_skills


def metadata_for(option):
    return {metadata.label: metadata.value for metadata in option.display_metadata}


def test_load_skills_normalizes_xphb_skill_descriptions():
    skills = load_skills(FIVETOOLS_SOURCE)
    acrobatics = next(skill for skill in skills if skill["name"] == "Acrobatics")

    assert acrobatics["ability"] == "Dexterity"
    assert acrobatics["description"] == "Stay on your feet in a tricky situation, or perform an acrobatic stunt."
    assert acrobatics["source"] == "XPHB"


def test_skill_catalog_uses_ability_metadata_and_stable_ids():
    skills = load_skills(FIVETOOLS_SOURCE)

    catalog = build_skill_catalog(skills, ["Arcana", "Stealth"], ["Arcana"])
    arcana = next(option for option in catalog if option.name == "Arcana")
    stealth = next(option for option in catalog if option.name == "Stealth")

    assert arcana.selected is True
    assert arcana.availability_status == "selected"
    assert metadata_for(arcana)["Ability"] == "Intelligence"
    assert "Recall lore about spells" in arcana.full_description
    assert arcana.stable_id == "skill:arcana|xphb"
    assert stealth.selected is False


def test_tool_catalog_states_missing_rules_description_explicitly():
    catalog = build_tool_catalog(["Smith's Tools"], ["Smith's Tools"], category="Artisan's Tool", source_label="XPHB")
    option = catalog[0]

    assert option.selected is True
    assert "No further rules description" in option.full_description
    assert metadata_for(option)["Category"] == "Artisan's Tool"


def test_prefixed_skill_tool_catalog_round_trips_existing_values():
    skills = load_skills(FIVETOOLS_SOURCE)
    catalog = build_prefixed_skill_tool_catalog(
        skills,
        ["Arcana"],
        ["Smith's Tools"],
        ["Skill: Arcana", "Tool: Smith's Tools"],
    )

    selected_ids = compact_selected_ids(catalog, ["Skill: Arcana", "Tool: Smith's Tools"])

    assert values_from_ids(catalog, selected_ids) == ["Skill: Arcana", "Tool: Smith's Tools"]
    assert all(option.selected for option in catalog)


def test_streamlit_compact_class_skill_choice_preserves_exact_count_and_details():
    from streamlit.testing.v1 import AppTest

    script = '''
import streamlit as st
from app import compact_values_choice
from presentation.proficiency_catalog import build_skill_catalog
from services.data_loader import FIVETOOLS_SOURCE, load_skills

current = st.session_state.setdefault("class_skills", [])
catalog = build_skill_catalog(load_skills(FIVETOOLS_SOURCE), ["Acrobatics", "Arcana"], current)
selected = compact_values_choice(
    catalog,
    current,
    selection_limit=2,
    state_key="test_class_skills",
    label="Choose 2 class skills",
)
st.session_state["class_skills"] = selected
'''
    at = AppTest.from_string(script, default_timeout=10).run()

    assert not at.exception
    at.multiselect[0].set_value(["skill:acrobatics|xphb", "skill:arcana|xphb"]).run()

    assert at.session_state["class_skills"] == ["Acrobatics", "Arcana"]
    assert "About selected options" in [expander.label for expander in at.expander]


def test_streamlit_compact_skilled_choice_keeps_skill_tool_prefixes():
    from streamlit.testing.v1 import AppTest

    script = '''
import streamlit as st
from app import compact_values_choice
from presentation.proficiency_catalog import build_prefixed_skill_tool_catalog
from services.data_loader import FIVETOOLS_SOURCE, load_skills

current = st.session_state.setdefault("selected", [])
catalog = build_prefixed_skill_tool_catalog(
    load_skills(FIVETOOLS_SOURCE),
    ["Arcana"],
    ["Smith's Tools"],
    current,
)
selected = compact_values_choice(
    catalog,
    current,
    selection_limit=2,
    state_key="test_skilled",
    label="Skilled",
)
st.session_state["selected"] = selected
'''
    at = AppTest.from_string(script, default_timeout=10).run()

    assert not at.exception
    ids = list(at.multiselect[0].options)
    at.multiselect[0].set_value(ids).run()

    assert at.session_state["selected"] == ["Skill: Arcana", "Tool: Smith's Tools"]
