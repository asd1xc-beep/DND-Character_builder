from app import choice_current_value


def test_choice_current_value_preserves_unresolved_partial_feat_selection():
    choice = {
        "status": "unresolved",
        "value": {
            "mode": "feat",
            "feat_id": "chef_xphb",
            "feat_name": "Chef",
            "feat_ability_choice": "",
            "feat_choices": {},
        },
    }

    assert choice_current_value(choice)["feat_id"] == "chef_xphb"


def test_streamlit_general_feat_ability_dropdown_resolves_unfinished_feat():
    from streamlit.testing.v1 import AppTest

    script = '''
import streamlit as st
from app import render_asi_or_feat_choice

chef = {
    "id": "chef_xphb",
    "name": "Chef",
    "category": "general",
    "source": "XPHB",
    "description": "You gain cooking benefits.",
    "ability_increase": {"mode": "choose", "from": ["Constitution", "Wisdom"], "amount": 1, "maximum": 20},
    "choice_schema": [],
    "eligible": True,
    "supported": True,
    "support": {"selection": "supported"},
}

if "draft" not in st.session_state:
    st.session_state.draft = {
        "pending_choices": [{
            "id": "fighter_level_4_asi_or_feat",
            "type": "asi_or_feat",
            "name": "Ability Score Improvement or general feat",
            "status": "unresolved",
            "value": {
                "mode": "feat",
                "feat_id": "chef_xphb",
                "feat_name": "Chef",
                "feat_ability_choice": "",
                "feat_choices": {},
            },
            "feat_options": [chef],
            "feat_candidates": [chef],
            "ability_scores": {
                "Strength": 10,
                "Dexterity": 10,
                "Constitution": 10,
                "Intelligence": 10,
                "Wisdom": 10,
                "Charisma": 10,
            },
            "skill_proficiencies": [],
            "expertise": [],
            "saving_throw_proficiencies": [],
            "weapon_proficiencies": [],
            "weapon_masteries": [],
            "general_feats": [],
            "weapons": [],
            "rules": {},
            "spells": [],
        }],
        "resolved_choices": [],
        "can_finalize": False,
    }

choice = st.session_state.draft["pending_choices"][0]
render_asi_or_feat_choice(st.session_state.draft, choice, {})
st.write(f"status={choice.get('status')}")
'''
    at = AppTest.from_string(script, default_timeout=10).run()

    assert not at.exception
    assert at.session_state["draft"]["pending_choices"][0]["value"]["feat_id"] == "chef_xphb"

    at = at.selectbox(key="general_feat_ability_fighter_level_4_asi_or_feat").select("Wisdom").run()

    choice = at.session_state["draft"]["pending_choices"][0]
    assert choice["status"] == "resolved"
    assert choice["value"]["feat_id"] == "chef_xphb"
    assert choice["value"]["feat_ability_choice"] == "Wisdom"
