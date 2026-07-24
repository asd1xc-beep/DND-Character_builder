import json
import re
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
IMPORTED_5ETOOLS_DIR = DATA_DIR / "imported" / "5etools"
SAMPLE_SOURCE = "Sample data"
FIVETOOLS_SOURCE = "5e.tools 2024 import"


def data_source_dir(source_name):
    if source_name == FIVETOOLS_SOURCE and IMPORTED_5ETOOLS_DIR.exists():
        return IMPORTED_5ETOOLS_DIR
    return DATA_DIR


def available_data_sources():
    sources = [SAMPLE_SOURCE]
    if IMPORTED_5ETOOLS_DIR.exists():
        sources.insert(0, FIVETOOLS_SOURCE)
    return sources


def load_json(filename, source_name=SAMPLE_SOURCE):
    path = data_source_dir(source_name) / filename
    if not path.exists() and source_name != SAMPLE_SOURCE:
        path = DATA_DIR / filename
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if source_name == FIVETOOLS_SOURCE and IMPORTED_5ETOOLS_DIR in path.parents:
        return clean_5etools_data(data)
    return data


def load_classes(source_name=SAMPLE_SOURCE):
    return load_json("classes.json", source_name)


def load_species(source_name=SAMPLE_SOURCE):
    return load_json("species.json", source_name)


def load_backgrounds(source_name=SAMPLE_SOURCE):
    return load_json("backgrounds.json", source_name)


def load_feats(source_name=SAMPLE_SOURCE):
    path = data_source_dir(source_name) / "feats.json"
    if not path.exists():
        return []
    return load_json("feats.json", source_name)


def load_spells(source_name=SAMPLE_SOURCE):
    return load_json("spells.json", source_name)


def load_equipment(source_name=SAMPLE_SOURCE):
    return load_json("equipment.json", source_name)


def load_weapons(source_name=SAMPLE_SOURCE):
    path = data_source_dir(source_name) / "weapons.json"
    if not path.exists():
        return []
    return load_json("weapons.json", source_name)


def load_weapon_masteries(source_name=SAMPLE_SOURCE):
    if source_name == FIVETOOLS_SOURCE:
        path = DATA_DIR / "raw" / "5etools" / "items-base.json"
        if path.exists():
            with path.open("r", encoding="utf-8") as file:
                records = json.load(file).get("itemMastery", [])
            return [
                normalize_weapon_mastery_record(record)
                for record in records
                if record.get("source") == "XPHB"
            ]
    return []


def normalize_weapon_mastery_record(record):
    name = str(record.get("name") or "")
    return {
        "name": name,
        "description": clean_5etools_text(first_text_entry(record.get("entries", []))),
        "source": str(record.get("source") or ""),
        "raw_ref": f"{name}|{record.get('source', '')}",
    }


def load_beasts(source_name=SAMPLE_SOURCE):
    path = data_source_dir(source_name) / "beasts.json"
    if path.exists():
        return load_json("beasts.json", source_name)
    from rules.beasts import beast_catalog

    return beast_catalog()


def load_rules(source_name=SAMPLE_SOURCE):
    return load_json("rules.json", source_name)


def load_skills(source_name=SAMPLE_SOURCE):
    if source_name == FIVETOOLS_SOURCE:
        path = DATA_DIR / "raw" / "5etools" / "skills.json"
        if path.exists():
            with path.open("r", encoding="utf-8") as file:
                records = json.load(file).get("skill", [])
            return [
                normalize_skill_record(record)
                for record in records
                if record.get("source") == "XPHB"
            ]
    rules = load_rules(source_name)
    return [
        {
            "name": name,
            "ability": ability,
            "description": "",
            "source": "sample",
            "raw_ref": name,
        }
        for name, ability in rules.get("skills", {}).items()
    ]


def normalize_skill_record(record):
    return {
        "name": record.get("name", ""),
        "ability": ability_name(record.get("ability", "")),
        "description": first_text_entry(record.get("entries", [])),
        "source": record.get("source", ""),
        "raw_ref": f"{record.get('name', '')}|{record.get('source', '')}",
    }


def ability_name(abbreviation):
    return {
        "str": "Strength",
        "dex": "Dexterity",
        "con": "Constitution",
        "int": "Intelligence",
        "wis": "Wisdom",
        "cha": "Charisma",
    }.get(str(abbreviation).lower(), str(abbreviation or ""))


def first_text_entry(entries):
    for entry in entries or []:
        if isinstance(entry, str):
            return entry
    return ""


def clean_5etools_text(text):
    def replace_tag(match):
        content = match.group(1)
        tag, _, body = content.partition(" ")
        tag = tag.lower()
        parts = [part for part in body.split("|") if part]
        if tag == "dc" and parts:
            return f"DC {parts[0]}"
        if tag == "filter" and parts:
            return parts[0]
        if len(parts) >= 3:
            return parts[2]
        if parts:
            return parts[0]
        return parts[-1] if parts else body

    return re.sub(r"\{@([^{}]+)\}", replace_tag, str(text or "")).strip()


def clean_5etools_data(value):
    if isinstance(value, dict):
        return {key: clean_5etools_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean_5etools_data(item) for item in value]
    if isinstance(value, str) and "{@" in value:
        return clean_5etools_text(value)
    return value


def load_metadata(source_name=SAMPLE_SOURCE):
    if source_name == FIVETOOLS_SOURCE and (IMPORTED_5ETOOLS_DIR / "metadata.json").exists():
        return load_json("metadata.json", source_name)
    return {"source": "sample"}


def by_name(items):
    return {item["name"]: item for item in items}
