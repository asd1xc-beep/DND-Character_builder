def test_streamlit_resolved_additional_fighting_style_does_not_rerun_loop():
    from streamlit.testing.v1 import AppTest

    script = '''
import streamlit as st
from app import render_level_compact_single_choice

choice = {
    "id": "fighter_7_champion_additional_fighting_style",
    "type": "class_option_selection",
    "class_option_key": "champion_additional_fighting_styles",
    "name": "Choose Additional Fighting Style",
    "choose": 1,
    "options": ["Archery", "Dueling"],
    "value": ["Archery"],
    "status": "resolved",
}
draft = {
    "class_name": "Fighter",
    "pending_choices": [choice],
    "resolved_choices": [choice],
    "can_finalize": True,
    "base_character": {
        "class": "Fighter",
        "subclass": "Champion",
        "class_options": {
            "fighting_style": "Defense",
            "champion_additional_fighting_styles": [],
        },
    },
}
data = {
    "classes_by_name": {
        "Fighter": {
            "name": "Fighter",
            "source": "XPHB",
            "feature_descriptions": {
                "Additional Fighting Style": "You gain another Fighting Style feat of your choice.",
            },
            "subclasses": [
                {
                    "short_name": "Champion",
                    "source": "XPHB",
                    "feature_descriptions": {},
                }
            ],
        }
    }
}

render_level_compact_single_choice(draft, choice, data, choice["options"], choice["name"])
st.write("rendered")
'''
    at = AppTest.from_string(script, default_timeout=10).run()

    assert not at.exception
    assert any(markdown.value == "rendered" for markdown in at.markdown)
