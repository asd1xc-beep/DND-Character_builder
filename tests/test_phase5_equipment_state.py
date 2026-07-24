from models.character import new_character
from presentation.equipment_catalog import (
    MISSING_EQUIPMENT_DESCRIPTION,
    build_equipment_catalog,
    equipment_stable_id,
)
from services.character_sheet import build_character_sheet
from services.equipment_state import derive_equipment, selected_default_equipment, sync_equipment_state
from services.pdf_export import build_wotc_field_values
from services.save_load import CURRENT_SCHEMA_VERSION, migrate_character


CLASS_DATA = {
    "name": "Fighter",
    "equipment_packages": [
        {"name": "A", "items": ["Chain Mail", "Greatsword"]},
        {"name": "B", "items": ["Leather Armor", "Longbow"]},
    ],
    "starting_equipment": ["Fallback Sword"],
}
BACKGROUND_DATA = {
    "name": "Soldier",
    "equipment_packages": [
        {"name": "A", "items": ["Gaming Set", "Pouch"]},
        {"name": "B", "items": ["Traveler's Clothes"]},
    ],
    "equipment": ["Fallback Background Kit"],
}


def test_derive_equipment_uses_selected_packages_and_custom_equipment():
    character = new_character()
    character["class_options"]["equipment_package"] = "A"
    character["background_options"]["equipment_package"] = "A"
    character["custom_equipment"] = ["Rope"]

    sync_equipment_state(character, CLASS_DATA, BACKGROUND_DATA)

    assert selected_default_equipment(character, CLASS_DATA, BACKGROUND_DATA) == [
        "Chain Mail",
        "Greatsword",
        "Gaming Set",
        "Pouch",
    ]
    assert character["equipment"] == ["Chain Mail", "Greatsword", "Gaming Set", "Pouch", "Rope"]


def test_switching_package_does_not_accumulate_old_package_items_or_delete_custom_items():
    character = new_character()
    character["class_options"]["equipment_package"] = "A"
    character["background_options"]["equipment_package"] = "A"
    character["custom_equipment"] = ["Rope"]
    sync_equipment_state(character, CLASS_DATA, BACKGROUND_DATA)

    character["class_options"]["equipment_package"] = "B"
    sync_equipment_state(character, CLASS_DATA, BACKGROUND_DATA)

    assert character["equipment"] == ["Leather Armor", "Longbow", "Gaming Set", "Pouch", "Rope"]
    assert "Chain Mail" not in character["equipment"]
    assert character["custom_equipment"] == ["Rope"]


def test_disabling_default_equipment_leaves_custom_equipment_only():
    character = new_character()
    character["class_options"]["equipment_package"] = "A"
    character["background_options"]["equipment_package"] = "A"
    character["include_default_equipment"] = False
    character["custom_equipment"] = ["Rope"]

    sync_equipment_state(character, CLASS_DATA, BACKGROUND_DATA)

    assert character["equipment"] == ["Rope"]


def test_removing_custom_equipment_updates_derived_equipment_without_changing_packages():
    character = new_character()
    character["class_options"]["equipment_package"] = "A"
    character["custom_equipment"] = ["Rope", "Torch"]
    sync_equipment_state(character, CLASS_DATA, {})

    character["custom_equipment"] = ["Torch"]
    sync_equipment_state(character, CLASS_DATA, {})

    assert character["equipment"] == ["Chain Mail", "Greatsword", "Torch"]
    assert character["class_options"]["equipment_package"] == "A"


def test_legacy_equipment_migration_preserves_items_until_package_reconciliation():
    character = migrate_character({
        "name": "Legacy Gear",
        "equipment": ["Chain Mail", "Greatsword", "Rope"],
        "class_options": {"equipment_package": "A"},
    })

    assert character["schema_version"] == CURRENT_SCHEMA_VERSION
    assert character["custom_equipment"] == ["Chain Mail", "Greatsword", "Rope"]
    assert character["equipment_migration_pending"] is True

    sync_equipment_state(character, CLASS_DATA, {})

    assert character["custom_equipment"] == ["Rope"]
    assert character["equipment"] == ["Chain Mail", "Greatsword", "Rope"]
    assert character["equipment_migration_pending"] is False


def test_equipment_catalog_marks_package_items_unavailable_without_inventing_descriptions():
    options = build_equipment_catalog(["Rope", "Chain Mail"], ["Rope"], ["Chain Mail"])
    by_id = {option.stable_id: option for option in options}

    rope = by_id[equipment_stable_id("Rope")]
    chain_mail = by_id[equipment_stable_id("Chain Mail")]

    assert rope.availability_status == "selected"
    assert chain_mail.availability_status == "unavailable"
    assert chain_mail.full_description == MISSING_EQUIPMENT_DESCRIPTION
    assert "Already included" in chain_mail.eligibility_reasons[0]


def test_derived_equipment_remains_sheet_and_pdf_source():
    character = new_character()
    character.update({"name": "Equipment PDF"})
    character["class_options"]["equipment_package"] = "A"
    character["custom_equipment"] = ["Rope"]
    sync_equipment_state(character, CLASS_DATA, {})

    sheet = build_character_sheet(character)

    assert sheet["equipment"] == derive_equipment(character, CLASS_DATA, {})
    assert build_wotc_field_values(_complete_pdf_sheet(sheet))["Equipment"][0] == "Chain Mail, Greatsword, Rope"


def test_streamlit_equipment_browser_smoke_adds_custom_equipment():
    from streamlit.testing.v1 import AppTest

    script = '''
import streamlit as st
from presentation.equipment_catalog import build_equipment_catalog
from ui.equipment_browser import render_equipment_browser

selected = st.session_state.get("selected", [])
catalog = build_equipment_catalog(["Rope", "Chain Mail"], selected, ["Chain Mail"])
updated = render_equipment_browser(catalog, selected, state_key="test_equipment")
if updated != selected:
    st.session_state["selected"] = updated
    st.rerun()
'''
    at = AppTest.from_string(script, default_timeout=10).run()

    assert not at.exception
    at = at.button(key="test_equipment_inspect_equipment:rope").click().run()
    at = at.button(key="test_equipment_add_equipment:rope").click().run()
    assert at.session_state["selected"] == ["Rope"]

    package_row = at.button(key="test_equipment_inspect_equipment:chain mail")
    assert package_row.label.endswith("Unavailable")


def _complete_pdf_sheet(sheet):
    completed = dict(sheet)
    completed["identity"] = {
        "name": sheet["identity"]["name"],
        "class": "Fighter",
        "level": 1,
        "background": "Soldier",
        "species": "Human",
        "speed": 30,
    }
    completed["saving_throws"] = [
        {"name": ability, "bonus_display": "+0"}
        for ability in ("Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma")
    ]
    completed["skills"] = [
        {"name": skill, "bonus": 0, "bonus_display": "+0"}
        for skill in (
            "Acrobatics",
            "Animal Handling",
            "Arcana",
            "Athletics",
            "Deception",
            "History",
            "Insight",
            "Intimidation",
            "Investigation",
            "Medicine",
            "Nature",
            "Perception",
            "Performance",
            "Persuasion",
            "Religion",
            "Sleight of Hand",
            "Stealth",
            "Survival",
        )
    ]
    completed["proficiencies"] = {"armor": [], "weapons": [], "tools": [], "languages": []}
    completed["features"] = []
    completed["feature_details"] = []
    completed["origin_feats"] = []
    completed["general_feats"] = []
    completed["weapon_masteries"] = []
    completed["resources"] = {}
    completed["spells"] = {"cantrips": [], "known": [], "prepared": [], "granted": [], "spellcasting_ability": ""}
    completed["spell_details"] = []
    return completed
