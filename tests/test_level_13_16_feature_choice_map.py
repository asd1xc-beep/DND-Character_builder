import json
from pathlib import Path


MAP_PATH = Path("data/coverage/level_13_16_feature_choice_map.json")
CLASSES_PATH = Path("data/imported/5etools/classes.json")
LEVELS = range(13, 17)


def load_map():
    return json.loads(MAP_PATH.read_text(encoding="utf-8"))


def load_classes():
    return json.loads(CLASSES_PATH.read_text(encoding="utf-8"))


def slug(value):
    return "".join(char.lower() if char.isalnum() else "_" for char in str(value)).strip("_")


def test_level_13_16_map_has_all_class_level_entries():
    level_map = load_map()
    classes = load_classes()
    expected_keys = {
        f"{slug(class_data['name'])}_{level}"
        for class_data in classes
        for level in LEVELS
    }

    assert level_map["generated_from"] == "data/imported/5etools/classes.json"
    assert level_map["level_range"] == [13, 16]
    assert set(level_map["class_levels"]) == expected_keys
    assert level_map["summary"]["class_level_count"] == len(expected_keys)


def test_level_13_16_map_lists_every_imported_class_and_subclass_feature():
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


def test_level_13_16_known_blockers_and_generic_ready_items_are_explicit():
    level_map = load_map()
    blockers = set(level_map["blocking_items"])
    generic_ready = set(level_map["generic_ready_items"])

    assert blockers == set()
    assert level_map["summary"]["blocking_choice_count"] == 0

    required_generic_items = {
        "bard_13_ritual_caster_bonus_spells",
        "fighter_14_ability_score_improvement",
        "fighter_16_ability_score_improvement",
        "fighter_16_weapon_mastery",
        "ranger_16_ability_score_improvement",
        "warlock_15_eldritch_invocations",
        "warlock_13_mystic_arcanum",
        "warlock_15_mystic_arcanum",
        "wizard_13_spell_progression",
        "wizard_16_spell_progression",
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


def test_level_13_16_partial_support_entries_are_classified():
    level_map = load_map()
    partial_entries = []
    feature_entries = {}
    subclass_feature_entries = {}

    for entry in level_map["class_levels"].values():
        for feature in entry["feature_entries"]:
            feature_entries[feature["id"]] = feature
            if feature.get("status") == "partial_support":
                partial_entries.append(feature)
        for subclass in entry["subclass_features"]:
            subclass_feature_entries[subclass["id"]] = subclass
            if subclass.get("status") == "partial_support":
                partial_entries.append(subclass)

    assert partial_entries == []
    assert feature_entries["monk_14_disciplined_survivor"]["classification"] == "proficiency_grant"
    assert feature_entries["rogue_15_slippery_mind"]["classification"] == "proficiency_grant"
    assert subclass_feature_entries["wizard_diviner_14"]["feature_classifications"] == [
        {
            "name": "Greater Portent",
            "classification": "resource_progression",
            "handler": "services.character_engine.subclass_resources",
        }
    ]
    assert subclass_feature_entries["ranger_fey_wanderer_15"]["feature_classifications"] == [
        {
            "name": "Misty Wanderer",
            "classification": "spell_grant",
            "handler": "rules.feature_spell_grants.feature_spell_grant_records",
        }
    ]
