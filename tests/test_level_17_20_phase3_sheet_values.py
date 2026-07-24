import json

from models.character import new_character
from services.character_engine import recalculate_character
from services.character_sheet import build_character_sheet
from services.save_load import migrate_character
from tests.test_level_one_builds import app_data


def high_level_character(class_name, level, subclass=""):
    character = new_character()
    character.update({
        "name": f"Level {level} {class_name}",
        "species": "Human",
        "background": "Soldier",
        "class": class_name,
        "subclass": subclass,
        "level": level,
    })
    character["background_options"] = {
        "primary_ability": "Strength",
        "secondary_ability": "Constitution",
    }
    character["species_options"] = {
        "skill_proficiencies": ["Perception"],
        "origin_feats": ["Tough"],
    }
    character["class_options"] = {"class_skills": ["Athletics", "Survival"]}
    return character


def test_fighter_action_surge_uses_scale_and_round_trip_to_sheet():
    data = app_data()
    level_two = high_level_character("Fighter", 2, "Champion")
    level_seventeen = high_level_character("Fighter", 17, "Champion")

    recalculate_character(level_two, data)
    recalculate_character(level_seventeen, data)

    assert build_character_sheet(level_two)["resources"]["action_surge_uses"] == 1
    assert build_character_sheet(level_two)["resources"]["action_surge_recharge"] == "short_or_long_rest"
    assert build_character_sheet(level_seventeen)["resources"]["action_surge_uses"] == 2

    loaded = migrate_character(json.loads(json.dumps(level_seventeen)))
    recalculate_character(loaded, data)

    assert build_character_sheet(loaded)["resources"]["action_surge_uses"] == 2


def test_ranger_feral_senses_adds_source_aware_blindsight():
    data = app_data()
    level_seventeen = high_level_character("Ranger", 17, "Hunter")
    level_eighteen = high_level_character("Ranger", 18, "Hunter")

    recalculate_character(level_seventeen, data)
    recalculate_character(level_eighteen, data)
    sheet = build_character_sheet(level_eighteen)

    assert "blindsight_range" not in build_character_sheet(level_seventeen)["resources"]
    assert sheet["resources"]["blindsight_range"] == 30
    assert sheet["resources"]["blindsight_source"] == "Feral Senses"
    assert sheet["senses"] == [{
        "type": "Blindsight",
        "range": 30,
        "sources": [{
            "type": "class_feature",
            "class_name": "Ranger",
            "feature_name": "Feral Senses",
            "level": 18,
        }],
        "source_names": ["Feral Senses"],
    }]

    level_eighteen["class"] = "Fighter"
    recalculate_character(level_eighteen, data)

    assert build_character_sheet(level_eighteen)["senses"] == []
    assert "blindsight_range" not in build_character_sheet(level_eighteen)["resources"]


def test_blindsight_sources_merge_and_keep_the_greatest_range():
    data = app_data()
    ranger = high_level_character("Ranger", 18, "Hunter")
    ranger["general_feats"] = [{
        "name": "Skulker",
        "choices": {},
        "source": {"type": "test"},
    }]

    recalculate_character(ranger, data)
    sheet = build_character_sheet(ranger)
    blindsight = next(sense for sense in sheet["senses"] if sense["type"] == "Blindsight")

    assert sheet["resources"]["blindsight_range"] == 30
    assert set(sheet["resources"]["blindsight_sources"]) == {"Skulker", "Feral Senses"}
    assert blindsight["range"] == 30
    assert set(blindsight["source_names"]) == {"Skulker", "Feral Senses"}


def test_paladin_aura_ranges_expand_at_level_eighteen_and_apply_to_subclass_auras():
    data = app_data()
    level_six = high_level_character("Paladin", 6, "Oath of Devotion")
    level_eighteen = high_level_character("Paladin", 18, "Oath of Devotion")

    recalculate_character(level_six, data)
    recalculate_character(level_eighteen, data)
    level_six_sheet = build_character_sheet(level_six)
    level_eighteen_sheet = build_character_sheet(level_eighteen)

    assert level_six_sheet["resources"]["aura_of_protection_range"] == 10
    assert level_six_sheet["resources"]["paladin_aura_range"] == 10
    assert level_eighteen_sheet["resources"]["aura_of_protection_range"] == 30
    assert level_eighteen_sheet["resources"]["aura_of_courage_range"] == 30
    assert level_eighteen_sheet["resources"]["aura_of_devotion_range"] == 30

    loaded = migrate_character(json.loads(json.dumps(level_eighteen)))
    recalculate_character(loaded, data)

    assert build_character_sheet(loaded)["resources"]["aura_of_protection_range"] == 30
