import json
from pathlib import Path

from tests.test_level_one_builds import app_data


def coverage_key(class_name, subclass):
    return (
        f"{class_name.lower().replace(' ', '_')}_"
        f"{subclass['short_name'].lower().replace(' ', '_')}_"
        f"{subclass.get('source', '').lower()}"
    )


def test_level_three_subclass_coverage_lists_every_imported_subclass():
    data = app_data()
    coverage = json.loads(Path("data/coverage/subclass_level_3_coverage.json").read_text(encoding="utf-8"))

    expected_keys = {
        coverage_key(class_data["name"], subclass)
        for class_data in data["classes"]
        for subclass in class_data.get("subclasses", [])
    }

    assert set(coverage) == expected_keys
    assert coverage["druid_land_xphb"]["choice_types"] == ["structured_spell_choice"]
    assert coverage["fighter_battle_master_xphb"]["required_choices_supported"] is True
    assert "Primal Companion stat-block choice is supported" in coverage["ranger_beast_master_xphb"]["notes"][0]
