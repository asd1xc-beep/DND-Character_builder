"""Generate the level 13-16 feature and choice map from normalized 5e.tools data."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.level_feature_choice_map import COVERAGE_DIR, ROOT_DIR, generate_level_band_map


MAP_PATH = COVERAGE_DIR / "level_13_16_feature_choice_map.json"


def generate_level_13_16_map():
    return generate_level_band_map(13, 16, MAP_PATH)


def main():
    level_map = generate_level_13_16_map()
    summary = level_map["summary"]
    print(
        f"Wrote {MAP_PATH.relative_to(ROOT_DIR)} with "
        f"{summary['class_level_count']} class-level entries and "
        f"{summary['blocking_choice_count']} blockers."
    )


if __name__ == "__main__":
    main()
