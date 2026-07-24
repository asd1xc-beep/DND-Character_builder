import json
from pathlib import Path


MATRIX_PATH = Path("data/coverage/level_8_12_progression_matrix.json")
CLASSES_PATH = Path("data/imported/5etools/classes.json")


def load_matrix():
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))


def slug(value):
    return "".join(char.lower() if char.isalnum() else "_" for char in str(value)).strip("_")


def test_level_8_12_progression_matrix_covers_every_class_and_level_delta():
    matrix = load_matrix()
    class_names = [class_data["name"] for class_data in json.loads(CLASSES_PATH.read_text(encoding="utf-8"))]

    assert matrix["level_range"] == [8, 12]
    assert set(matrix["classes"]) == {slug(name) for name in class_names}
    assert matrix["summary"]["class_count"] == len(class_names)

    for class_entry in matrix["classes"].values():
        assert class_entry["baseline"]["level"] == 8
        assert set(class_entry["levels"]) == {"9", "10", "11", "12"}
        for level_entry in class_entry["levels"].values():
            assert "features" in level_entry
            assert "resource_changes" in level_entry
            assert "spellcasting_changes" in level_entry
            for choice in level_entry["required_choices"]:
                assert choice["status"] == "generic_ready", choice
                assert choice["handler"], choice


def test_level_8_12_progression_matrix_tracks_known_high_value_deltas():
    matrix = load_matrix()

    assert matrix["classes"]["barbarian"]["levels"]["10"]["resource_changes"]["weapon_mastery_count"] == {
        "before": 3,
        "after": 4,
    }
    assert matrix["classes"]["fighter"]["levels"]["11"]["features"] == ["Two Extra Attacks"]
    assert matrix["classes"]["warlock"]["levels"]["11"]["resource_changes"]["spell_slot_count"] == {
        "before": 2,
        "after": 3,
    }
    assert any(
        choice["id"] == "warlock_11_mystic_arcanum"
        for choice in matrix["classes"]["warlock"]["levels"]["11"]["required_choices"]
    )
    assert matrix["summary"]["partial_support_items"] == []
