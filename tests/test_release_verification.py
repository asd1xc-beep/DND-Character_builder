import json
import zipfile

from models.character import new_character
from services.character_engine import recalculate_character
from services.character_sheet import build_character_sheet
from services.save_load import migrate_character
from tests.test_level_one_builds import app_data
from tools.package_project import build_zip


def test_all_classes_and_supported_subclasses_build_level_twenty_sheets_after_round_trip():
    data = app_data()
    cases = []
    for class_data in data["classes"]:
        cases.append((class_data["name"], ""))
        for subclass in class_data.get("subclasses", []):
            cases.append((class_data["name"], subclass.get("name", "")))

    assert len(cases) >= 12

    for class_name, subclass_name in cases:
        character = release_character(class_name, subclass_name)
        recalculate_character(character, data)
        loaded = migrate_character(json.loads(json.dumps(character)))
        recalculate_character(loaded, data)
        sheet = build_character_sheet(loaded)

        assert sheet["identity"]["level"] == 20
        assert sheet["identity"]["class"] == class_name
        assert sheet["features"]
        assert isinstance(sheet["resources"], dict)
        assert isinstance(sheet["feature_details"], list)


def test_portable_package_excludes_generated_and_local_only_files(tmp_path):
    package_path = build_zip(tmp_path / "portable.zip")

    with zipfile.ZipFile(package_path) as archive:
        names = set(archive.namelist())

    assert "app.py" in names
    assert "requirements.txt" in names
    assert "Start Character Builder.cmd" in names
    assert "Setup First Time.cmd" in names
    assert "data/imported/5etools/classes.json" in names
    assert not any(name.startswith(".venv/") for name in names)
    assert not any(name.startswith(".pytest-tmp/") for name in names)
    assert not any("__pycache__" in name for name in names)
    assert not any(name.startswith("output/pdf/") and not name.endswith(".gitkeep") for name in names)
    assert not any(name.startswith("output/saved_characters/") and name.endswith(".json") for name in names)
    assert not any(name.endswith(".zip") for name in names)


def release_character(class_name, subclass_name):
    character = new_character()
    character.update({
        "name": f"Release {class_name}",
        "species": "Human",
        "background": "Sage",
        "class": class_name,
        "subclass": subclass_name,
        "level": 20,
    })
    character["background_options"] = {
        "primary_ability": "Constitution",
        "secondary_ability": "Dexterity",
    }
    character["species_options"] = {
        "skill_proficiencies": ["Perception"],
        "origin_feats": ["Tough"],
    }
    character["class_options"] = {
        "class_skills": ["Arcana", "Insight"],
        "wizard_scholar_skill": "Arcana",
        "battle_master_save_ability": "Strength",
    }
    character["base_ability_scores"].update({
        "Strength": 16,
        "Dexterity": 16,
        "Constitution": 16,
        "Intelligence": 16,
        "Wisdom": 16,
        "Charisma": 16,
    })
    return character
