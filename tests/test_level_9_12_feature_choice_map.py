import json
from pathlib import Path


MAP_PATH = Path("data/coverage/level_9_12_feature_choice_map.json")
CLASSES_PATH = Path("data/imported/5etools/classes.json")
LEVELS = range(9, 13)


def load_map():
    return json.loads(MAP_PATH.read_text(encoding="utf-8"))


def load_classes():
    return json.loads(CLASSES_PATH.read_text(encoding="utf-8"))


def slug(value):
    return "".join(char.lower() if char.isalnum() else "_" for char in str(value)).strip("_")


def test_level_9_12_map_has_all_class_level_entries():
    level_map = load_map()
    classes = load_classes()
    expected_keys = {
        f"{slug(class_data['name'])}_{level}"
        for class_data in classes
        for level in LEVELS
    }

    assert level_map["generated_from"] == "data/imported/5etools/classes.json"
    assert level_map["level_range"] == [9, 12]
    assert set(level_map["class_levels"]) == expected_keys
    assert level_map["summary"]["class_level_count"] == len(expected_keys)


def test_level_9_12_map_lists_every_imported_class_and_subclass_feature():
    level_map = load_map()

    for class_data in load_classes():
        for level in LEVELS:
            class_key = f"{slug(class_data['name'])}_{level}"
            entry = level_map["class_levels"][class_key]
            expected_features = class_data.get("level_features", {}).get(str(level), [])
            assert entry["features"] == expected_features

            expected_subclasses = {
                subclass["name"]
                for subclass in class_data.get("subclasses", [])
                if subclass.get("level_features", {}).get(str(level), [])
                or subclass.get("grants_by_level", {}).get(str(level), {})
            }
            mapped_subclasses = {
                subclass_entry["subclass"]
                for subclass_entry in entry["subclass_features"]
            }
            assert mapped_subclasses == expected_subclasses


def test_level_9_12_known_blockers_and_generic_ready_items_are_explicit():
    level_map = load_map()
    blockers = set(level_map["blocking_items"])
    generic_ready = set(level_map["generic_ready_items"])

    assert blockers == set()
    assert level_map["summary"]["blocking_choice_count"] == 0

    required_generic_items = {
        "bard_9_expertise",
        "barbarian_10_weapon_mastery",
        "fighter_10_weapon_mastery",
        "ranger_9_expertise",
        "sorcerer_10_metamagic",
        "warlock_9_eldritch_invocations",
        "warlock_11_mystic_arcanum",
        "warlock_12_eldritch_invocations",
        "rogue_10_ability_score_improvement",
        "wizard_12_ability_score_improvement",
        "wizard_9_spell_progression",
        "bard_9_ritual_caster_bonus_spells",
    }
    assert required_generic_items.issubset(generic_ready)

    for entry in level_map["class_levels"].values():
        for choice in entry["required_choices"]:
            assert choice["choice_type"]
            assert choice["status"] in {"generic_ready", "needs_handler"}
            if choice["status"] == "needs_handler":
                assert choice["blocks_level_path"] is True
                assert not choice["handler"]
                assert choice["notes"]
            else:
                assert choice["blocks_level_path"] is False
                assert choice["handler"]


def test_level_9_12_automatic_features_are_classified_before_enablement():
    level_map = load_map()
    old_statuses = {
        feature.get("status")
        for entry in level_map["class_levels"].values()
        for feature in entry["feature_entries"]
    } | {
        subclass.get("status")
        for entry in level_map["class_levels"].values()
        for subclass in entry["subclass_features"]
    }
    partial_subclasses = {
        subclass["id"]: subclass
        for entry in level_map["class_levels"].values()
        for subclass in entry["subclass_features"]
        if subclass.get("status") == "partial_support"
    }

    assert "automatic_or_descriptive_review" not in old_statuses
    assert partial_subclasses == {}

    for entry in level_map["class_levels"].values():
        for feature in entry["feature_entries"]:
            if feature.get("choice_type") == "none":
                assert feature.get("classification"), feature
                assert feature.get("status") in {"audited_automatic", "partial_support"}, feature
                assert feature.get("handler"), feature
                assert feature.get("handler_verified") is True, feature
        for subclass in entry["subclass_features"]:
            assert subclass.get("handler"), subclass
            assert subclass.get("handler_verified") is True, subclass
