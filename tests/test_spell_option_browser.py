from copy import deepcopy

from models.character import new_character
from presentation.option_catalog import (
    SpellSelectionGroupSpec,
    add_option_to_group_selection,
    add_option_to_selection,
    build_grouped_spell_option_catalog,
    build_spell_option_catalog,
    inspect_option,
    remove_option_from_group_selection,
    remove_option_from_selection,
)
from services.character_engine import recalculate_character
from services.character_sheet import build_character_sheet


SPELLS = [
    {
        "name": "Light",
        "source": "XPHB",
        "level": 0,
        "school": "Evocation",
        "casting_time": "1 action",
        "range": "Touch",
        "duration": "1 hour",
        "components": ["V", "M"],
        "description": "You touch one Large or smaller object.",
        "raw_ref": "Light|XPHB",
    },
    {
        "name": "Mage Hand",
        "source": "XPHB",
        "level": 0,
        "school": "Conjuration",
        "casting_time": "1 action",
        "range": "30 feet",
        "duration": "1 minute",
        "components": ["V", "S"],
        "description": "A spectral hand appears at a point you choose within range.",
        "raw_ref": "Mage Hand|XPHB",
    },
    {
        "name": "Fire Bolt",
        "source": "XPHB",
        "level": 0,
        "school": "Evocation",
        "casting_time": "1 action",
        "range": "120 feet",
        "duration": "Instantaneous",
        "components": ["V", "S"],
        "description": "You hurl a mote of fire at a creature or object within range.",
        "raw_ref": "Fire Bolt|XPHB",
    },
    {
        "name": "Cure Wounds",
        "source": "XPHB",
        "level": 1,
        "school": "Abjuration",
        "casting_time": "1 action",
        "range": "Touch",
        "duration": "Instantaneous",
        "components": ["V", "S"],
        "description": "A creature you touch regains Hit Points.",
        "raw_ref": "Cure Wounds|XPHB",
    },
]


def test_spell_option_view_models_are_built_from_complete_spell_data():
    options = build_spell_option_catalog(SPELLS, ["Light", "Mage Hand"], ["Light"], kind="cantrip", selection_limit=2)
    by_name = {option.name: option for option in options}

    assert by_name["Mage Hand"].full_description.startswith("A spectral hand")
    assert by_name["Mage Hand"].short_summary == "A spectral hand appears at a point you choose within range."
    assert by_name["Mage Hand"].source.source == "XPHB"
    assert dict(by_name["Mage Hand"].payload)["components"] == "V, S"
    assert by_name["Light"].selected is True
    assert by_name["Light"].availability_status == "selected"


def test_catalog_can_lookup_unselected_spell_description():
    options = build_spell_option_catalog(SPELLS, ["Light", "Mage Hand"], ["Light"], kind="cantrip", selection_limit=2)
    mage_hand = next(option for option in options if option.name == "Mage Hand")

    inspected = inspect_option(options, mage_hand.stable_id)

    assert inspected is not None
    assert inspected.name == "Mage Hand"
    assert "spectral hand" in inspected.full_description


def test_add_cantrip_below_limit_returns_expanded_selection():
    options = build_spell_option_catalog(SPELLS, ["Light", "Mage Hand"], ["Light"], kind="cantrip", selection_limit=2)
    mage_hand = next(option for option in options if option.name == "Mage Hand")

    result = add_option_to_selection(["Light"], options, mage_hand.stable_id, selection_limit=2)

    assert result.accepted is True
    assert result.changed is True
    assert list(result.selection) == ["Light", "Mage Hand"]


def test_add_cantrip_at_limit_is_rejected_with_reason():
    options = build_spell_option_catalog(SPELLS, ["Light", "Mage Hand", "Fire Bolt"], ["Light", "Mage Hand"], kind="cantrip", selection_limit=2)
    fire_bolt = next(option for option in options if option.name == "Fire Bolt")

    result = add_option_to_selection(["Light", "Mage Hand"], options, fire_bolt.stable_id, selection_limit=2)

    assert result.accepted is False
    assert result.changed is False
    assert list(result.selection) == ["Light", "Mage Hand"]
    assert "Selection is full (2/2)" in result.reason
    assert fire_bolt.availability_status == "unavailable"


def test_remove_selected_cantrip_returns_reduced_selection():
    options = build_spell_option_catalog(SPELLS, ["Light", "Mage Hand"], ["Light", "Mage Hand"], kind="cantrip", selection_limit=2)
    light = next(option for option in options if option.name == "Light")

    result = remove_option_from_selection(["Light", "Mage Hand"], light.stable_id, options)

    assert result.accepted is True
    assert result.changed is True
    assert list(result.selection) == ["Mage Hand"]


def test_grouped_spell_picker_keeps_cantrip_and_leveled_allowances_separate():
    options = build_grouped_spell_option_catalog(
        SPELLS,
        (
            SpellSelectionGroupSpec(
                key="cantrips",
                label="Cantrips",
                option_names=("Light",),
                selected_names=(),
                selection_limit=1,
                add_label="Add cantrip",
                remove_label="Remove cantrip",
            ),
            SpellSelectionGroupSpec(
                key="known",
                label="Known spells",
                option_names=("Cure Wounds",),
                selected_names=(),
                selection_limit=1,
                add_label="Add known spell",
                remove_label="Remove known spell",
            ),
        ),
    )
    light = next(option for option in options if option.name == "Light")
    cure_wounds = next(option for option in options if option.name == "Cure Wounds")

    wrong_known = add_option_to_group_selection([], options, light.stable_id, group_key="known", selection_limit=1)
    wrong_cantrip = add_option_to_group_selection([], options, cure_wounds.stable_id, group_key="cantrips", selection_limit=1)
    cantrips = add_option_to_group_selection([], options, light.stable_id, group_key="cantrips", selection_limit=1)
    known = add_option_to_group_selection([], options, cure_wounds.stable_id, group_key="known", selection_limit=1)

    assert wrong_known.accepted is False
    assert list(wrong_known.selection) == []
    assert wrong_cantrip.accepted is False
    assert list(wrong_cantrip.selection) == []
    assert cantrips.accepted is True
    assert list(cantrips.selection) == ["Light"]
    assert known.accepted is True
    assert list(known.selection) == ["Cure Wounds"]


def test_grouped_spell_picker_keeps_cantrip_and_prepared_allowances_separate():
    options = build_grouped_spell_option_catalog(
        SPELLS,
        (
            SpellSelectionGroupSpec(
                key="cantrips",
                label="Cantrips",
                option_names=("Light", "Mage Hand"),
                selected_names=("Light",),
                selection_limit=1,
                add_label="Add cantrip",
                remove_label="Remove cantrip",
            ),
            SpellSelectionGroupSpec(
                key="prepared",
                label="Prepared spells",
                option_names=("Cure Wounds",),
                selected_names=(),
                selection_limit=1,
                add_label="Add prepared spell",
                remove_label="Remove prepared spell",
            ),
        ),
    )
    light = next(option for option in options if option.name == "Light")
    mage_hand = next(option for option in options if option.name == "Mage Hand")
    cure_wounds = next(option for option in options if option.name == "Cure Wounds")

    cantrip_at_limit = add_option_to_group_selection(["Light"], options, mage_hand.stable_id, group_key="cantrips", selection_limit=1)
    wrong_prepared = add_option_to_group_selection([], options, light.stable_id, group_key="prepared", selection_limit=1)
    wrong_cantrip = add_option_to_group_selection(["Light"], options, cure_wounds.stable_id, group_key="cantrips", selection_limit=1)
    prepared = add_option_to_group_selection([], options, cure_wounds.stable_id, group_key="prepared", selection_limit=1)

    assert cantrip_at_limit.accepted is False
    assert list(cantrip_at_limit.selection) == ["Light"]
    assert wrong_prepared.accepted is False
    assert list(wrong_prepared.selection) == []
    assert wrong_cantrip.accepted is False
    assert list(wrong_cantrip.selection) == ["Light"]
    assert prepared.accepted is True
    assert list(prepared.selection) == ["Cure Wounds"]


def test_grouped_spell_picker_keeps_cantrip_and_spellbook_allowances_separate():
    options = build_grouped_spell_option_catalog(
        SPELLS,
        (
            SpellSelectionGroupSpec(
                key="cantrips",
                label="Cantrips",
                option_names=("Light", "Mage Hand"),
                selected_names=("Light",),
                selection_limit=1,
                add_label="Add cantrip",
                remove_label="Remove cantrip",
            ),
            SpellSelectionGroupSpec(
                key="spellbook",
                label="Spellbook spells",
                option_names=("Cure Wounds",),
                selected_names=(),
                selection_limit=1,
                add_label="Add spellbook spell",
                remove_label="Remove spellbook spell",
            ),
        ),
    )
    light = next(option for option in options if option.name == "Light")
    mage_hand = next(option for option in options if option.name == "Mage Hand")
    cure_wounds = next(option for option in options if option.name == "Cure Wounds")

    cantrip_at_limit = add_option_to_group_selection(["Light"], options, mage_hand.stable_id, group_key="cantrips", selection_limit=1)
    wrong_spellbook = add_option_to_group_selection([], options, light.stable_id, group_key="spellbook", selection_limit=1)
    wrong_cantrip = add_option_to_group_selection(["Light"], options, cure_wounds.stable_id, group_key="cantrips", selection_limit=1)
    spellbook = add_option_to_group_selection([], options, cure_wounds.stable_id, group_key="spellbook", selection_limit=1)

    assert cantrip_at_limit.accepted is False
    assert list(cantrip_at_limit.selection) == ["Light"]
    assert wrong_spellbook.accepted is False
    assert list(wrong_spellbook.selection) == []
    assert wrong_cantrip.accepted is False
    assert list(wrong_cantrip.selection) == ["Light"]
    assert spellbook.accepted is True
    assert list(spellbook.selection) == ["Cure Wounds"]


def test_remove_selected_prepared_spell_returns_reduced_group_selection():
    options = build_grouped_spell_option_catalog(
        SPELLS,
        (
            SpellSelectionGroupSpec(
                key="prepared",
                label="Prepared spells",
                option_names=("Cure Wounds",),
                selected_names=("Cure Wounds",),
                selection_limit=1,
                add_label="Add prepared spell",
                remove_label="Remove prepared spell",
            ),
        ),
    )
    cure_wounds = next(option for option in options if option.name == "Cure Wounds")

    result = remove_option_from_group_selection(["Cure Wounds"], cure_wounds.stable_id, options, group_key="prepared")

    assert result.accepted is True
    assert result.changed is True
    assert list(result.selection) == []


def test_inspection_does_not_mutate_character_or_selection():
    character = new_character()
    character["spells"]["cantrips"] = ["Light"]
    original_character = deepcopy(character)
    options = build_spell_option_catalog(SPELLS, ["Light", "Mage Hand"], character["spells"]["cantrips"], kind="cantrip", selection_limit=2)
    mage_hand = next(option for option in options if option.name == "Mage Hand")

    inspected = inspect_option(options, mage_hand.stable_id)

    assert inspected.name == "Mage Hand"
    assert character == original_character


def test_stable_ids_preserve_selection_mapping_across_rebuilt_catalogs():
    first = build_spell_option_catalog(SPELLS, ["Light", "Mage Hand", "Fire Bolt"], ["Light"], kind="cantrip", selection_limit=2)
    second = build_spell_option_catalog(reversed(SPELLS), ["Fire Bolt", "Mage Hand", "Light"], ["Light"], kind="cantrip", selection_limit=2)

    first_ids = {option.name: option.stable_id for option in first}
    second_ids = {option.name: option.stable_id for option in second}

    assert first_ids == second_ids


def test_character_sheet_output_is_unchanged_for_browser_selected_cantrips():
    from tests.test_level_one_builds import app_data

    data = app_data()
    direct = new_character()
    direct.update({"class": "Wizard", "species": "Human", "background": "Sage"})
    direct["spells"]["cantrips"] = ["Fire Bolt", "Mage Hand", "Prestidigitation"]
    via_browser = deepcopy(direct)

    options = build_spell_option_catalog(
        data["spells"],
        ["Fire Bolt", "Mage Hand", "Prestidigitation"],
        [],
        kind="cantrip",
        selection_limit=3,
    )
    for name in ["Fire Bolt", "Mage Hand", "Prestidigitation"]:
        option = next(item for item in options if item.name == name)
        result = add_option_to_selection(via_browser["spells"]["cantrips"], options, option.stable_id, selection_limit=3)
        via_browser["spells"]["cantrips"] = list(result.selection)
        options = build_spell_option_catalog(
            data["spells"],
            ["Fire Bolt", "Mage Hand", "Prestidigitation"],
            via_browser["spells"]["cantrips"],
            kind="cantrip",
            selection_limit=3,
        )

    recalculate_character(direct, data)
    recalculate_character(via_browser, data)

    assert build_character_sheet(via_browser)["spells"]["cantrips"] == build_character_sheet(direct)["spells"]["cantrips"]
    assert build_character_sheet(via_browser)["spell_details"] == build_character_sheet(direct)["spell_details"]


def test_character_sheet_output_is_unchanged_for_browser_selected_prepared_spells():
    from tests.test_level_one_builds import app_data

    data = app_data()
    direct = new_character()
    direct.update({"class": "Cleric", "species": "Dwarf", "background": "Acolyte"})
    direct["spells"]["cantrips"] = ["Guidance", "Light", "Sacred Flame"]
    direct["spells"]["prepared"] = ["Bless", "Cure Wounds", "Guiding Bolt", "Shield of Faith"]
    direct["spells"]["known"] = []
    via_browser = deepcopy(direct)
    via_browser["spells"]["prepared"] = []

    options = build_grouped_spell_option_catalog(
        data["spells"],
        (
            SpellSelectionGroupSpec(
                key="prepared",
                label="Prepared spells",
                option_names=tuple(direct["spells"]["prepared"]),
                selected_names=tuple(via_browser["spells"]["prepared"]),
                selection_limit=4,
                add_label="Add prepared spell",
                remove_label="Remove prepared spell",
            ),
        ),
    )
    for name in direct["spells"]["prepared"]:
        option = next(item for item in options if item.name == name)
        result = add_option_to_group_selection(via_browser["spells"]["prepared"], options, option.stable_id, group_key="prepared", selection_limit=4)
        via_browser["spells"]["prepared"] = list(result.selection)
        options = build_grouped_spell_option_catalog(
            data["spells"],
            (
                SpellSelectionGroupSpec(
                    key="prepared",
                    label="Prepared spells",
                    option_names=tuple(direct["spells"]["prepared"]),
                    selected_names=tuple(via_browser["spells"]["prepared"]),
                    selection_limit=4,
                    add_label="Add prepared spell",
                    remove_label="Remove prepared spell",
                ),
            ),
        )

    recalculate_character(direct, data)
    recalculate_character(via_browser, data)

    assert build_character_sheet(via_browser)["spells"]["prepared"] == build_character_sheet(direct)["spells"]["prepared"]
    assert build_character_sheet(via_browser)["spell_details"] == build_character_sheet(direct)["spell_details"]


def test_character_sheet_output_is_unchanged_for_browser_selected_spellbook_spells():
    from tests.test_level_one_builds import app_data

    data = app_data()
    direct = new_character()
    direct.update({"class": "Wizard", "species": "Human", "background": "Sage"})
    direct["spells"]["cantrips"] = ["Fire Bolt", "Mage Hand", "Prestidigitation"]
    direct["spells"]["spellbook"] = ["Burning Hands", "Detect Magic", "Identify", "Mage Armor", "Magic Missile", "Sleep"]
    direct["spells"]["known"] = []
    direct["spells"]["prepared"] = []
    via_browser = deepcopy(direct)
    via_browser["spells"]["spellbook"] = []

    options = build_grouped_spell_option_catalog(
        data["spells"],
        (
            SpellSelectionGroupSpec(
                key="spellbook",
                label="Spellbook spells",
                option_names=tuple(direct["spells"]["spellbook"]),
                selected_names=tuple(via_browser["spells"]["spellbook"]),
                selection_limit=6,
                add_label="Add spellbook spell",
                remove_label="Remove spellbook spell",
            ),
        ),
    )
    for name in direct["spells"]["spellbook"]:
        option = next(item for item in options if item.name == name)
        result = add_option_to_group_selection(via_browser["spells"]["spellbook"], options, option.stable_id, group_key="spellbook", selection_limit=6)
        via_browser["spells"]["spellbook"] = list(result.selection)
        options = build_grouped_spell_option_catalog(
            data["spells"],
            (
                SpellSelectionGroupSpec(
                    key="spellbook",
                    label="Spellbook spells",
                    option_names=tuple(direct["spells"]["spellbook"]),
                    selected_names=tuple(via_browser["spells"]["spellbook"]),
                    selection_limit=6,
                    add_label="Add spellbook spell",
                    remove_label="Remove spellbook spell",
                ),
            ),
        )

    recalculate_character(direct, data)
    recalculate_character(via_browser, data)

    assert build_character_sheet(via_browser)["spells"]["spellbook"] == build_character_sheet(direct)["spells"]["spellbook"]
    assert build_character_sheet(via_browser)["spell_details"] == build_character_sheet(direct)["spell_details"]


def test_streamlit_browser_smoke_renders_with_native_widgets():
    from streamlit.testing.v1 import AppTest

    script = '''
import streamlit as st
from presentation.option_catalog import build_spell_option_catalog
from ui.option_browser import render_spell_option_browser

spells = [
    {"name": "Light", "source": "XPHB", "level": 0, "school": "Evocation", "casting_time": "1 action", "range": "Touch", "duration": "1 hour", "components": ["V"], "description": "Light description.", "raw_ref": "Light|XPHB"},
    {"name": "Mage Hand", "source": "XPHB", "level": 0, "school": "Conjuration", "casting_time": "1 action", "range": "30 feet", "duration": "1 minute", "components": ["V", "S"], "description": "Mage Hand description.", "raw_ref": "Mage Hand|XPHB"},
    {"name": "Sacred Flame", "source": "XPHB", "level": 0, "school": "Evocation", "casting_time": "1 action", "range": "60 feet", "duration": "Instantaneous", "components": ["V", "S"], "description": "Sacred Flame description.", "raw_ref": "Sacred Flame|XPHB"},
]
selected = st.session_state.setdefault("selected_cantrips", [])
options = build_spell_option_catalog(spells, ["Light", "Mage Hand", "Sacred Flame"], selected, kind="cantrip", selection_limit=2)
updated = render_spell_option_browser(
    options,
    selected,
    selection_limit=2,
    state_key="smoke_cantrips",
    label="Choose 2 cantrips",
)
if updated != selected:
    st.session_state["selected_cantrips"] = updated
    st.rerun()
st.session_state["selected_cantrips"] = updated
'''
    at = AppTest.from_string(script, default_timeout=10).run()

    assert not at.exception
    assert len(at.dataframe) == 0
    assert at.button[0].label == "Light | Cantrip | Evocation | 1 action | Touch | 1 hour | Available: Cantrip"
    assert at.button[0].help == ""
    assert at.button[1].label == "Mage Hand | Cantrip | Conjuration | 1 action | 30 feet | 1 minute | Available: Cantrip"
    assert at.button[1].help == ""
    assert at.button[2].label == "Sacred Flame | Cantrip | Evocation | 1 action | 60 feet | Instantaneous | Available: Cantrip"
    assert at.button[2].help == ""
    assert at.button[3].label == "Add cantrip"
    assert len(at.text_input) == 1
    assert len(at.selectbox) == 2

    at.button[1].click().run()

    assert at.session_state["smoke_cantrips_inspected_id"] == "spell:mage hand|xphb"
    assert any(markdown.value == "Mage Hand description." for markdown in at.markdown)
    assert at.button[0].label == "Light | Cantrip | Evocation | 1 action | Touch | 1 hour | Available: Cantrip"
    assert at.button[1].label == "Mage Hand | Cantrip | Conjuration | 1 action | 30 feet | 1 minute | Available: Cantrip"
    assert at.button[2].label == "Sacred Flame | Cantrip | Evocation | 1 action | 60 feet | Instantaneous | Available: Cantrip"
    assert at.button[3].label == "Add cantrip"

    at.button[3].click().run()

    assert at.session_state["selected_cantrips"] == ["Mage Hand"]
    assert any(markdown.value == "**Cantrip:** Selected" for markdown in at.markdown)
    assert at.button[3].label == "Remove cantrip"

    at.text_input[0].set_value("Mage").run()

    assert at.session_state["smoke_cantrips_search"] == "Mage"


def test_streamlit_browser_recovers_stale_inspected_id_to_selected_spell():
    from streamlit.testing.v1 import AppTest

    script = '''
import streamlit as st
from presentation.option_catalog import build_spell_option_catalog
from ui.option_browser import render_spell_option_browser

spells = [
    {"name": "Light", "source": "XPHB", "level": 0, "school": "Evocation", "casting_time": "1 action", "range": "Touch", "duration": "1 hour", "components": ["V"], "description": "Light description.", "raw_ref": "Light|XPHB"},
    {"name": "Mage Hand", "source": "XPHB", "level": 0, "school": "Conjuration", "casting_time": "1 action", "range": "30 feet", "duration": "1 minute", "components": ["V", "S"], "description": "Mage Hand description.", "raw_ref": "Mage Hand|XPHB"},
]
st.session_state.setdefault("stale_cantrips_inspected_id", "spell:missing|xphb")
selected = ["Mage Hand"]
options = build_spell_option_catalog(spells, ["Light", "Mage Hand"], selected, kind="cantrip", selection_limit=2)
render_spell_option_browser(options, selected, selection_limit=2, state_key="stale_cantrips", label="Choose 2 cantrips")
'''
    at = AppTest.from_string(script, default_timeout=10).run()

    assert not at.exception
    assert at.session_state["stale_cantrips_inspected_id"] == "spell:mage hand|xphb"
    assert any(markdown.value == "Mage Hand description." for markdown in at.markdown)


def test_streamlit_magic_initiate_uses_spell_browser_without_mutating_on_inspection():
    from streamlit.testing.v1 import AppTest

    script = '''
import streamlit as st
from app import render_origin_feat_controls
from models.character import new_character

spells = [
    {"name": "Light", "source": "XPHB", "level": 0, "school": "Evocation", "casting_time": "1 action", "range": "Touch", "duration": "1 hour", "components": ["V"], "description": "Light description.", "raw_ref": "Light|XPHB", "classes": ["Wizard"]},
    {"name": "Mage Hand", "source": "XPHB", "level": 0, "school": "Conjuration", "casting_time": "1 action", "range": "30 feet", "duration": "1 minute", "components": ["V", "S"], "description": "Mage Hand description.", "raw_ref": "Mage Hand|XPHB", "classes": ["Wizard"]},
    {"name": "Magic Missile", "source": "XPHB", "level": 1, "school": "Evocation", "casting_time": "1 action", "range": "120 feet", "duration": "Instantaneous", "components": ["V", "S"], "description": "Magic Missile description.", "raw_ref": "Magic Missile|XPHB", "classes": ["Wizard"]},
]
character = st.session_state.setdefault("character", new_character())
character["origin_feats"] = ["Magic Initiate (Wizard)"]
character.setdefault("origin_feat_choices", {"cantrips": [], "tools": [], "skills": [], "spell": "", "spellcasting_ability": ""})
render_origin_feat_controls(character, {"spells": spells, "rules": {"skills": {}}})
'''
    at = AppTest.from_string(script, default_timeout=10).run()

    assert not at.exception
    assert at.button[0].label == "Light | Cantrip | Evocation | 1 action | Touch | 1 hour | Available: Cantrips"
    assert at.button[2].label == "Magic Missile | Level 1 | Evocation | 1 action | 120 feet | Instantaneous | Available: Level 1 spell"

    at.button[2].click().run()

    assert at.session_state["origin_magic_initiate_(wizard)_spells_inspected_id"] == "spell:magic missile|xphb"
    assert at.session_state["character"]["origin_feat_choices"]["spell"] == ""

    assert at.button[3].label == "Add Level 1 spell"
    at.button[3].click().run()

    assert at.session_state["character"]["origin_feat_choices"]["spell"] == "Magic Missile"


def test_streamlit_fighting_style_cantrip_grant_uses_spell_browser():
    from streamlit.testing.v1 import AppTest

    script = '''
import streamlit as st
from presentation.option_catalog import SpellSelectionGroupSpec
from ui.spell_choice_browser import render_spell_choice_browser

spells = [
    {"name": "Guidance", "source": "XPHB", "level": 0, "school": "Divination", "casting_time": "1 action", "range": "Touch", "duration": "Concentration, up to 1 minute", "components": ["V", "S"], "description": "Guidance description.", "raw_ref": "Guidance|XPHB"},
    {"name": "Light", "source": "XPHB", "level": 0, "school": "Evocation", "casting_time": "1 action", "range": "Touch", "duration": "1 hour", "components": ["V"], "description": "Light description.", "raw_ref": "Light|XPHB"},
]
class_options = st.session_state.setdefault("class_options", {"blessed_warrior_cantrips": []})
current = class_options.get("blessed_warrior_cantrips", [])
updated = render_spell_choice_browser(
    spells,
    (SpellSelectionGroupSpec("blessed_warrior_cantrips", "Blessed Warrior cantrips", ("Guidance", "Light"), tuple(current), 2, "Add cantrip", "Remove cantrip"),),
    {"blessed_warrior_cantrips": current},
    state_key="blessed_warrior_cantrips_smoke",
    label="Blessed Warrior: choose 2 Cleric cantrips",
)
if updated.get("blessed_warrior_cantrips", current) != current:
    class_options["blessed_warrior_cantrips"] = updated["blessed_warrior_cantrips"]
    st.rerun()
'''
    at = AppTest.from_string(script, default_timeout=10).run()

    assert not at.exception
    at.button[0].click().run()
    assert at.session_state["class_options"]["blessed_warrior_cantrips"] == []
    at.button[2].click().run()
    assert at.session_state["class_options"]["blessed_warrior_cantrips"] == ["Guidance"]


def test_streamlit_wizard_prepared_spells_use_spell_browser():
    from streamlit.testing.v1 import AppTest

    script = '''
import streamlit as st
from presentation.option_catalog import SpellSelectionGroupSpec
from ui.spell_choice_browser import render_spell_choice_browser

spells = [
    {"name": "Magic Missile", "source": "XPHB", "level": 1, "school": "Evocation", "casting_time": "1 action", "range": "120 feet", "duration": "Instantaneous", "components": ["V", "S"], "description": "Magic Missile description.", "raw_ref": "Magic Missile|XPHB"},
    {"name": "Sleep", "source": "XPHB", "level": 1, "school": "Enchantment", "casting_time": "1 action", "range": "60 feet", "duration": "1 minute", "components": ["V", "S", "M"], "description": "Sleep description.", "raw_ref": "Sleep|XPHB"},
]
character = st.session_state.setdefault("character", {"spells": {"prepared": []}})
current = character["spells"].get("prepared", [])
updated = render_spell_choice_browser(
    spells,
    (SpellSelectionGroupSpec("prepared", "Prepared spells", ("Magic Missile", "Sleep"), tuple(current), 1, "Add prepared spell", "Remove prepared spell"),),
    {"prepared": current},
    state_key="wizard_prepared_smoke",
    label="Choose up to 1 prepared Wizard spell",
)
if updated.get("prepared", current) != current:
    character["spells"]["prepared"] = updated["prepared"]
    st.rerun()
'''
    at = AppTest.from_string(script, default_timeout=10).run()

    assert not at.exception
    at.button[1].click().run()
    assert at.session_state["character"]["spells"]["prepared"] == []
    at.button[2].click().run()
    assert at.session_state["character"]["spells"]["prepared"] == ["Sleep"]


def test_streamlit_savant_choice_uses_spell_browser():
    from streamlit.testing.v1 import AppTest

    script = '''
import streamlit as st
from app import render_subclass_option_controls

spells = [
    {"name": "Color Spray", "source": "XPHB", "level": 1, "school": "Illusion", "school_code": "I", "casting_time": "1 action", "range": "Self", "duration": "Instantaneous", "components": ["V", "S", "M"], "description": "Color Spray description.", "raw_ref": "Color Spray|XPHB", "classes": ["Wizard"]},
    {"name": "Disguise Self", "source": "XPHB", "level": 1, "school": "Illusion", "school_code": "I", "casting_time": "1 action", "range": "Self", "duration": "1 hour", "components": ["V", "S"], "description": "Disguise Self description.", "raw_ref": "Disguise Self|XPHB", "classes": ["Wizard"]},
]
character = st.session_state.setdefault("character", {"subclass": "Illusionist", "level": 3, "spells": {"spellbook": []}, "class_options": {}})
class_data = {"subclasses": [{"name": "Illusionist", "subclass_options": {"savant_spells": {"label": "Choose Savant spell", "choose": 1, "from": {"class": "Wizard", "levels": [1], "school": "I"}}}}]}
render_subclass_option_controls(character, class_data, {"spells": spells})
'''
    at = AppTest.from_string(script, default_timeout=10).run()

    assert not at.exception
    at.button[0].click().run()
    assert at.session_state["character"]["class_options"].get("savant_spells", []) == []
    at.button[2].click().run()
    assert at.session_state["character"]["class_options"]["savant_spells"] == ["Color Spray"]


def test_streamlit_spell_mastery_uses_spell_browser_groups():
    from streamlit.testing.v1 import AppTest

    script = '''
import streamlit as st
from app import render_spell_mastery_choice

spells = [
    {"name": "Magic Missile", "source": "XPHB", "level": 1, "school": "Evocation", "casting_time": "1 action", "range": "120 feet", "duration": "Instantaneous", "components": ["V", "S"], "description": "Magic Missile description.", "raw_ref": "Magic Missile|XPHB"},
    {"name": "Blur", "source": "XPHB", "level": 2, "school": "Illusion", "casting_time": "1 action", "range": "Self", "duration": "Concentration, up to 1 minute", "components": ["V"], "description": "Blur description.", "raw_ref": "Blur|XPHB"},
]
draft = st.session_state.setdefault("draft", {"pending_choices": [{"id": "wizard_18_mastery", "type": "spell_mastery_selection", "name": "Spell Mastery", "level_1_options": ["Magic Missile"], "level_2_options": ["Blur"], "status": "unresolved"}], "resolved_choices": [], "can_finalize": False})
render_spell_mastery_choice(draft, draft["pending_choices"][0], spells)
'''
    at = AppTest.from_string(script, default_timeout=10).run()

    assert not at.exception
    assert at.button[0].label == "Magic Missile | Level 1 | Evocation | 1 action | 120 feet | Instantaneous | Available: Level 1 Spell Mastery"
    assert at.button[1].label == "Blur | Level 2 | Illusion | 1 action | Self | Concentration, up to 1 minute | Available: Level 2 Spell Mastery"
    at.button[0].click().run()
    at.button[2].click().run()
    assert at.session_state["draft"]["pending_choices"][0]["value"] == {"level_1": "Magic Missile", "level_2": ""}
    at.button[1].click().run()
    at.button[2].click().run()
    assert at.session_state["draft"]["pending_choices"][0]["status"] == "resolved"
    assert at.session_state["draft"]["pending_choices"][0]["value"] == {"level_1": "Magic Missile", "level_2": "Blur"}


def test_streamlit_feat_spell_choice_uses_level_up_spell_browser():
    from streamlit.testing.v1 import AppTest

    script = '''
import streamlit as st
from app import render_level_choice_controls

spells = [
    {"name": "Alarm", "source": "XPHB", "level": 1, "school": "Abjuration", "casting_time": "1 minute", "range": "30 feet", "duration": "8 hours", "components": ["V", "S", "M"], "description": "Alarm description.", "raw_ref": "Alarm|XPHB"},
    {"name": "Identify", "source": "XPHB", "level": 1, "school": "Divination", "casting_time": "1 minute", "range": "Touch", "duration": "Instantaneous", "components": ["V", "S", "M"], "description": "Identify description.", "raw_ref": "Identify|XPHB"},
]
draft = st.session_state.setdefault("draft", {"pending_choices": [{"id": "ritual_caster_5_ritual_spells", "type": "feat_spell_selection", "name": "Choose 1 additional Ritual Caster spell", "choose": 1, "options": ["Alarm", "Identify"], "status": "unresolved"}], "resolved_choices": [], "can_finalize": False})
render_level_choice_controls(draft, draft["pending_choices"], spells)
'''
    at = AppTest.from_string(script, default_timeout=10).run()

    assert not at.exception
    at.button[1].click().run()
    assert at.session_state["draft"]["pending_choices"][0]["status"] == "unresolved"
    at.button[2].click().run()
    assert at.session_state["draft"]["pending_choices"][0]["status"] == "resolved"
    assert at.session_state["draft"]["pending_choices"][0]["value"] == ["Identify"]


def test_streamlit_level_up_spell_picker_combines_spell_choices_and_inspects_before_resolving_draft():
    from streamlit.testing.v1 import AppTest

    script = '''
import streamlit as st
from app import render_level_choice_controls

spells = [
    {"name": "Light", "source": "XPHB", "level": 0, "school": "Evocation", "casting_time": "1 action", "range": "Touch", "duration": "1 hour", "components": ["V", "M"], "description": "Light description.", "raw_ref": "Light|XPHB"},
    {"name": "Bless", "source": "XPHB", "level": 1, "school": "Enchantment", "casting_time": "1 action", "range": "30 feet", "duration": "Concentration, up to 1 minute", "components": ["V", "S", "M"], "description": "Bless description.", "raw_ref": "Bless|XPHB"},
    {"name": "Cure Wounds", "source": "XPHB", "level": 1, "school": "Abjuration", "casting_time": "1 action", "range": "Touch", "duration": "Instantaneous", "components": ["V", "S"], "description": "Cure Wounds description.", "raw_ref": "Cure Wounds|XPHB"},
]
draft = st.session_state.setdefault("draft", {
    "pending_choices": [{
        "id": "cleric_4_cantrips",
        "type": "spell_selection",
        "name": "Choose Cleric cantrip gained at level 4",
        "spell_field": "cantrips",
        "required": True,
        "choose": 1,
        "options": ["Light"],
        "status": "unresolved",
    }, {
        "id": "cleric_4_prepared_spells",
        "type": "spell_selection",
        "name": "Choose Cleric prepared spell gained at level 4",
        "spell_field": "prepared",
        "required": True,
        "choose": 1,
        "options": ["Bless", "Cure Wounds"],
        "status": "unresolved",
    }],
    "resolved_choices": [],
    "can_finalize": False,
})
render_level_choice_controls(draft, draft["pending_choices"], spells)
'''
    at = AppTest.from_string(script, default_timeout=10).run()

    assert not at.exception
    assert at.button[0].label == "Light | Cantrip | Evocation | 1 action | Touch | 1 hour | Available: Cantrips"
    assert at.button[1].label == "Bless | Level 1 | Enchantment | 1 action | 30 feet | Concentration, up to 1 minute | Available: Prepared spells"
    assert at.button[2].label == "Cure Wounds | Level 1 | Abjuration | 1 action | Touch | Instantaneous | Available: Prepared spells"
    assert at.button[3].label == "Add cantrip"

    at.button[2].click().run()

    assert at.session_state["level_spell_choices_cleric_4_cantrips_cleric_4_prepared_spells_inspected_id"] == "spell:cure wounds|xphb"
    assert at.session_state["draft"]["pending_choices"][0]["status"] == "unresolved"
    assert at.session_state["draft"]["pending_choices"][1]["status"] == "unresolved"
    assert "value" not in at.session_state["draft"]["pending_choices"][1]

    assert at.button[3].label == "Add prepared spell"
    at.button[3].click().run()

    choice = at.session_state["draft"]["pending_choices"][1]
    assert choice["status"] == "resolved"
    assert choice["value"] == ["Cure Wounds"]
    assert at.session_state["draft"]["pending_choices"][0]["status"] == "unresolved"


def test_streamlit_level_up_spell_picker_handles_wizard_spellbook_additions():
    from streamlit.testing.v1 import AppTest

    script = '''
import streamlit as st
from app import render_level_choice_controls

spells = [
    {"name": "Magic Missile", "source": "XPHB", "level": 1, "school": "Evocation", "casting_time": "1 action", "range": "120 feet", "duration": "Instantaneous", "components": ["V", "S"], "description": "Magic Missile description.", "raw_ref": "Magic Missile|XPHB"},
    {"name": "Sleep", "source": "XPHB", "level": 1, "school": "Enchantment", "casting_time": "1 action", "range": "60 feet", "duration": "1 minute", "components": ["V", "S", "M"], "description": "Sleep description.", "raw_ref": "Sleep|XPHB"},
]
draft = st.session_state.setdefault("draft", {
    "pending_choices": [{
        "id": "wizard_2_spellbook_spells",
        "type": "spellbook_spells",
        "name": "Add 2 Wizard spellbook spells",
        "source": "Wizard",
        "level": 2,
        "required": True,
        "choose": 2,
        "options": ["Magic Missile", "Sleep"],
        "status": "unresolved",
    }],
    "resolved_choices": [],
    "can_finalize": False,
})
render_level_choice_controls(draft, draft["pending_choices"], spells)
'''
    at = AppTest.from_string(script, default_timeout=10).run()

    assert not at.exception
    assert at.button[0].label == "Magic Missile | Level 1 | Evocation | 1 action | 120 feet | Instantaneous | Available: Spellbook spells"
    assert at.button[1].label == "Sleep | Level 1 | Enchantment | 1 action | 60 feet | 1 minute | Available: Spellbook spells"
    assert at.button[2].label == "Add spellbook spell"

    at.button[0].click().run()

    assert at.session_state["level_spell_choices_wizard_2_spellbook_spells_inspected_id"] == "spell:magic missile|xphb"
    assert at.session_state["draft"]["pending_choices"][0]["status"] == "unresolved"
    assert "value" not in at.session_state["draft"]["pending_choices"][0]

    at.button[2].click().run()

    choice = at.session_state["draft"]["pending_choices"][0]
    assert choice["status"] == "unresolved"
    assert choice["value"] == ["Magic Missile"]

    at.button[1].click().run()
    assert at.button[2].label == "Add spellbook spell"
    at.button[2].click().run()

    choice = at.session_state["draft"]["pending_choices"][0]
    assert choice["status"] == "resolved"
    assert choice["value"] == ["Magic Missile", "Sleep"]


def test_streamlit_level_up_spell_picker_preserves_partial_wizard_savant_additions_after_refresh():
    from streamlit.testing.v1 import AppTest

    script = '''
import streamlit as st
from app import render_level_choice_controls
from rules.level_up import (
    commit_level_up_draft,
    create_level_up_draft,
    refresh_level_up_draft_choices,
    resolve_pending_choice,
)
from tests.test_level_one_builds import app_data, finalized
from tests.test_level_up import level_one_wizard

data = app_data()
if "character" not in st.session_state:
    character = level_one_wizard()
    finalized(character, data)
    level_two = create_level_up_draft(character, 2, data)
    spellbook_choice = next(choice for choice in level_two["pending_choices"] if choice["type"] == "spellbook_spells")
    scholar_choice = next(choice for choice in level_two["pending_choices"] if choice.get("class_option_key") == "wizard_scholar_skill")
    resolve_pending_choice(level_two, spellbook_choice["id"], ["Magic Missile", "Sleep"], spellbook_choice)
    resolve_pending_choice(level_two, scholar_choice["id"], "Arcana", scholar_choice)
    commit_level_up_draft(character, level_two, data)
    finalized(character, data)
    draft = create_level_up_draft(character, 3, data)
    subclass_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "subclass_choice")
    resolve_pending_choice(draft, subclass_choice["id"], "Diviner", subclass_choice)
    refresh_level_up_draft_choices(character, draft, data)
    spellbook_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "spellbook_spells")
    resolve_pending_choice(draft, spellbook_choice["id"], spellbook_choice["options"][:2], spellbook_choice)
    refresh_level_up_draft_choices(character, draft, data)
    st.session_state.character = character
    st.session_state.draft = draft

character = st.session_state.character
draft = st.session_state.draft
refresh_level_up_draft_choices(character, draft, data)
render_level_choice_controls(draft, draft["pending_choices"], data)
refresh_level_up_draft_choices(character, draft, data)
'''
    at = AppTest.from_string(script, default_timeout=10).run()

    assert not at.exception
    savant_choice = next(choice for choice in at.session_state["draft"]["pending_choices"] if choice.get("class_option_key") == "savant_spells")
    first_savant = savant_choice["options"][0]
    first_row = next(index for index, button in enumerate(at.button) if button.label.startswith(f"{first_savant} |"))
    at.button[first_row].click().run()
    add_button = next(index for index, button in enumerate(at.button) if button.label == "Add spell")
    at.button[add_button].click().run()

    savant_choice = next(choice for choice in at.session_state["draft"]["pending_choices"] if choice.get("class_option_key") == "savant_spells")
    assert savant_choice["status"] == "unresolved"
    assert savant_choice["value"] == [first_savant]

    second_savant = next(option for option in savant_choice["options"] if option != first_savant)
    second_row = next(index for index, button in enumerate(at.button) if button.label.startswith(f"{second_savant} |"))
    at.button[second_row].click().run()
    add_button = next(index for index, button in enumerate(at.button) if button.label == "Add spell")
    at.button[add_button].click().run()

    savant_choice = next(choice for choice in at.session_state["draft"]["pending_choices"] if choice.get("class_option_key") == "savant_spells")
    assert savant_choice["status"] == "resolved"
    assert savant_choice["value"] == [first_savant, second_savant]
