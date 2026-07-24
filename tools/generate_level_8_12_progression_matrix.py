"""Generate a class progression matrix for the enabled level 8-12 band."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from rules.leveling import effective_spellcasting, get_class_resources
from tools.level_feature_choice_map import changed_values, read_json, slug


IMPORTED_DIR = ROOT_DIR / "data" / "imported" / "5etools"
COVERAGE_DIR = ROOT_DIR / "data" / "coverage"
LEVEL_MAP_PATH = COVERAGE_DIR / "level_9_12_feature_choice_map.json"
MATRIX_PATH = COVERAGE_DIR / "level_8_12_progression_matrix.json"


def spellcasting_snapshot(class_data, level):
    spellcasting = effective_spellcasting(class_data, "", level)
    if not spellcasting:
        return {}
    return {
        key: value
        for key, value in spellcasting.items()
        if key
        in {
            "type",
            "ability",
            "spell_list",
            "cantrips_known",
            "known_spells",
            "prepared_spells",
            "spell_slots",
            "maximum_spell_level",
        }
    }


def class_matrix_entry(class_data, level_map):
    class_name = class_data["name"]
    baseline = {
        "level": 8,
        "resources": get_class_resources(class_data, 8),
        "spellcasting": spellcasting_snapshot(class_data, 8),
    }
    levels = {}
    previous_resources = baseline["resources"]
    previous_spellcasting = baseline["spellcasting"]
    for level in range(9, 13):
        class_level = level_map["class_levels"][f"{slug(class_name)}_{level}"]
        resources = get_class_resources(class_data, level)
        spellcasting = spellcasting_snapshot(class_data, level)
        levels[str(level)] = {
            "features": class_level["features"],
            "required_choices": [
                {
                    "id": choice["id"],
                    "choice_type": choice["choice_type"],
                    "handler": choice["handler"],
                    "status": choice["status"],
                }
                for choice in class_level["required_choices"]
            ],
            "resource_changes": changed_values(previous_resources, resources),
            "spellcasting_changes": changed_values(previous_spellcasting, spellcasting),
            "subclass_features": [
                {
                    "subclass": entry["subclass"],
                    "features": entry["features"],
                    "status": entry["status"],
                    "unsupported_features": entry.get("unsupported_features", []),
                }
                for entry in class_level["subclass_features"]
            ],
        }
        previous_resources = resources
        previous_spellcasting = spellcasting
    return {
        "class": class_name,
        "baseline": baseline,
        "levels": levels,
    }


def generate_level_8_12_progression_matrix():
    classes = read_json(IMPORTED_DIR / "classes.json")
    level_map = read_json(LEVEL_MAP_PATH)
    matrix = {
        "generated_from": [
            "data/imported/5etools/classes.json",
            "data/coverage/level_9_12_feature_choice_map.json",
        ],
        "level_range": [8, 12],
        "classes": {
            slug(class_data["name"]): class_matrix_entry(class_data, level_map)
            for class_data in classes
        },
    }
    matrix["summary"] = {
        "class_count": len(matrix["classes"]),
        "level_count_per_class": 5,
        "partial_support_items": sorted(
            f"{class_entry['class']} {level}: {subclass['subclass']} - {', '.join(subclass['unsupported_features'])}"
            for class_entry in matrix["classes"].values()
            for level, level_entry in class_entry["levels"].items()
            for subclass in level_entry["subclass_features"]
            if subclass.get("unsupported_features")
        ),
    }
    COVERAGE_DIR.mkdir(parents=True, exist_ok=True)
    MATRIX_PATH.write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")
    return matrix


def main():
    matrix = generate_level_8_12_progression_matrix()
    print(f"Wrote {MATRIX_PATH.relative_to(ROOT_DIR)} with {matrix['summary']['class_count']} classes.")


if __name__ == "__main__":
    main()
