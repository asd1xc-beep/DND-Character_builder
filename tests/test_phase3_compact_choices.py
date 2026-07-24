from presentation.compact_catalog import (
    build_class_feature_choice_catalog,
    build_equipment_package_catalog,
    build_lineage_catalog,
    build_species_choice_catalog,
    option_value,
)
from tests.test_level_one_builds import app_data


def metadata_for(option):
    return {metadata.label: metadata.value for metadata in option.display_metadata}


def test_divine_order_catalog_uses_related_feature_descriptions_and_clean_text():
    data = app_data()
    cleric = data["classes_by_name"]["Cleric"]

    catalog = build_class_feature_choice_catalog(
        cleric["class_options"]["divine_order"],
        selected_name="Thaumaturge",
        kind="class_order",
        source_label=cleric.get("source", ""),
        description_lookup=cleric.get("feature_descriptions", {}),
        related_features=(cleric.get("feature_related_features") or {}).get("Divine Order", []),
        parent_description=cleric.get("feature_descriptions", {}).get("Divine Order", ""),
    )

    thaumaturge = next(option for option in catalog if option.name == "Thaumaturge")
    protector = next(option for option in catalog if option.name == "Protector")
    assert thaumaturge.selected is True
    assert "Cleric" in thaumaturge.full_description
    assert "class=Cleric" not in thaumaturge.full_description
    assert "martial weapon" in protector.full_description.casefold()
    assert "type=martial weapon" not in protector.full_description


def test_species_choice_catalog_extracts_option_specific_text_when_available():
    data = app_data()
    goliath = data["species_by_name"]["Goliath"]

    catalog = build_species_choice_catalog(goliath, goliath["choice_options"], "Cloud Giant")
    cloud = next(option for option in catalog if option.name == "Cloud Giant")

    assert cloud.selected is True
    assert "teleport up to 30 feet" in cloud.full_description
    assert metadata_for(cloud)["Rules entry"] == "Cloud's Jaunt (Cloud Giant)"


def test_lineage_catalog_shows_level_one_grants_and_later_grant_notice():
    data = app_data()
    tiefling = data["species_by_name"]["Tiefling"]

    catalog = build_lineage_catalog(tiefling, "Infernal")
    infernal = next(option for option in catalog if option.name == "Infernal")

    assert infernal.selected is True
    assert metadata_for(infernal)["Level 1 grant"] == "Thaumaturgy, Fire Bolt"
    assert "later character levels" in metadata_for(infernal)["Later grants"]
    assert option_value(infernal) == "Infernal"


def test_equipment_package_catalog_displays_items_but_preserves_package_id():
    data = app_data()
    fighter = data["classes_by_name"]["Fighter"]

    catalog = build_equipment_package_catalog(fighter["equipment_packages"], "A", source_label="Fighter")
    package_a = next(option for option in catalog if option_value(option) == "A")

    assert package_a.selected is True
    assert package_a.name.startswith("Package A - Chain Mail")
    assert "Greatsword" in package_a.full_description
    assert option_value(package_a) == "A"


def test_streamlit_phase3_compact_choice_updates_value_and_detail_panel():
    from streamlit.testing.v1 import AppTest

    script = '''
import streamlit as st
from app import compact_value_choice
from presentation.compact_catalog import build_class_feature_choice_catalog
from tests.test_level_one_builds import app_data

data = app_data()
cleric = data["classes_by_name"]["Cleric"]
current = st.session_state.get("divine_order")
catalog = build_class_feature_choice_catalog(
    cleric["class_options"]["divine_order"],
    selected_name=current,
    kind="class_order",
    source_label=cleric.get("source", ""),
    description_lookup=cleric.get("feature_descriptions", {}),
    related_features=(cleric.get("feature_related_features") or {}).get("Divine Order", []),
    parent_description=cleric.get("feature_descriptions", {}).get("Divine Order", ""),
)
selected = compact_value_choice(
    catalog,
    current,
    state_key="test_divine_order",
    label="Divine Order",
    placeholder="Choose Divine Order",
)
if selected:
    st.session_state["divine_order"] = selected
'''
    at = AppTest.from_string(script, default_timeout=10).run()

    assert not at.exception
    at.selectbox[0].set_value("class_order:cleric__1_thaumaturge").run()

    assert at.session_state["divine_order"] == "Thaumaturge"
    assert any(markdown.value == "**Thaumaturge**" for markdown in at.markdown)
    assert any("extra cantrip" in element.value for element in [*at.markdown, *at.caption])


def test_streamlit_equipment_package_choice_preserves_package_identifier():
    from streamlit.testing.v1 import AppTest

    script = '''
import streamlit as st
from app import compact_value_choice
from presentation.compact_catalog import build_equipment_package_catalog

packages = [
    {"name": "A", "items": ["Chain Mail", "Greatsword", "Explorer's Pack"]},
    {"name": "B", "items": ["50 GP"]},
]
current = st.session_state.get("package")
catalog = build_equipment_package_catalog(packages, current, source_label="Fighter")
selected = compact_value_choice(
    catalog,
    current,
    state_key="test_package",
    label="Class equipment package",
    placeholder="Choose a class package",
)
if selected:
    st.session_state["package"] = selected
'''
    at = AppTest.from_string(script, default_timeout=10).run()

    assert not at.exception
    at.selectbox[0].set_value("equipment_package:fighter|a").run()

    assert at.session_state["package"] == "A"
    assert any(markdown.value.startswith("**Package A - Chain Mail") for markdown in at.markdown)
