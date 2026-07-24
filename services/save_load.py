import json
import re
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from models.character import DEFAULT_CHARACTER, merge_unique
from rules.mystic_arcanum import migrate_legacy_mystic_arcanum
from services.equipment_state import migrate_legacy_equipment


ROOT_DIR = Path(__file__).resolve().parents[1]
SAVE_DIR = ROOT_DIR / "output" / "saved_characters"
CURRENT_SCHEMA_VERSION = 4


def safe_filename(name):
    base = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip()).strip("_")
    return base or "unnamed_character"


def save_character(character):
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    path = SAVE_DIR / f"{safe_filename(character.get('name', ''))}.json"
    character = migrate_character(character)
    with path.open("w", encoding="utf-8") as file:
        json.dump(character, file, indent=2)
    return path


def list_saved_characters():
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(SAVE_DIR.glob("*.json"))


def load_character(path):
    with Path(path).open("r", encoding="utf-8") as file:
        return migrate_character(json.load(file))


def migrate_character(saved_character):
    saved_character = saved_character or {}
    saved_hit_points = saved_character.get("hit_points", {})
    migrated = deep_merge(DEFAULT_CHARACTER, saved_character or {})
    if "maximum" not in saved_hit_points:
        migrated["hit_points"]["maximum"] = migrated["hit_points"].get("max", 0)
    if "max" not in saved_hit_points:
        migrated["hit_points"]["max"] = migrated["hit_points"].get("maximum", 0)
    migrated["hit_points"].setdefault("temporary", 0)
    if not migrated.get("character_id"):
        migrated["character_id"] = uuid4().hex
    migrated["general_feats"] = migrate_general_feats(migrated.get("general_feats", []))
    migrate_legacy_wizard_spellbook(migrated, saved_character)
    migrate_legacy_magical_secrets(migrated)
    migrate_legacy_equipment(migrated, saved_character)
    if migrated.get("class") == "Warlock":
        migrate_legacy_mystic_arcanum(migrated)
    migrated.setdefault("schema_version", CURRENT_SCHEMA_VERSION)
    migrated["schema_version"] = CURRENT_SCHEMA_VERSION
    return migrated


def migrate_legacy_wizard_spellbook(character, saved_character):
    spells = character.setdefault("spells", {})
    spells.setdefault("cantrips", [])
    spells.setdefault("known", [])
    spells.setdefault("prepared", [])
    spells.setdefault("spellbook", [])
    if character.get("class") != "Wizard":
        return

    saved_spells = (saved_character or {}).get("spells", {})
    legacy_known = saved_spells.get("known", [])
    if isinstance(legacy_known, str):
        legacy_known = [legacy_known] if legacy_known else []
    legacy_known = [spell for spell in legacy_known or [] if spell]
    if legacy_known:
        spells["spellbook"] = merge_unique(spells.get("spellbook", []), legacy_known)
        spells["known"] = []
    if legacy_known and not spells.get("prepared"):
        character.setdefault("migration_warnings", []).append(
            "Legacy Wizard known spells were moved into the spellbook. "
            "Review prepared spells before play."
        )


def migrate_legacy_magical_secrets(character):
    if character.get("class") != "Bard" or int(character.get("level", 1) or 1) < 10:
        return
    class_options = character.setdefault("class_options", {})
    legacy_spells = class_options.get("magical_secrets", [])
    if isinstance(legacy_spells, str):
        legacy_spells = [legacy_spells] if legacy_spells else []
    legacy_spells = [spell for spell in legacy_spells or [] if spell]
    if not legacy_spells:
        return

    spells = character.setdefault("spells", {})
    prepared = spells.setdefault("prepared", [])
    for spell in legacy_spells:
        if spell not in prepared:
            prepared.append(spell)
    class_options["legacy_magical_secrets"] = legacy_spells
    class_options.pop("magical_secrets", None)
    character.setdefault("migration_warnings", []).append(
        "Legacy Magical Secrets bonus spells were moved into Bard prepared spells. "
        "Review the prepared-spell total before play."
    )


def migrate_general_feats(general_feats):
    migrated = []
    for entry in general_feats or []:
        if isinstance(entry, dict):
            feat = deepcopy(entry)
            feat.setdefault("instance_id", uuid4().hex)
            feat.setdefault("feat_id", None)
            feat.setdefault("name", "")
            feat.setdefault("source", {"type": "legacy"})
            feat.setdefault("choices", {})
            migrated.append(feat)
        elif entry:
            migrated.append({
                "instance_id": uuid4().hex,
                "feat_id": None,
                "name": str(entry),
                "source": {"type": "legacy"},
                "choices": {},
            })
    return migrated


def deep_merge(default, saved):
    if isinstance(default, dict) and isinstance(saved, dict):
        merged = deepcopy(default)
        for key, value in saved.items():
            if key in merged:
                merged[key] = deep_merge(merged[key], value)
            else:
                merged[key] = deepcopy(value)
        return merged
    return deepcopy(saved)
