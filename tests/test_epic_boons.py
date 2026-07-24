import pytest

from models.character import new_character
from rules.level_up import commit_level_up_draft, create_level_up_draft, resolve_pending_choice
from services.character_engine import recalculate_character
from services.character_sheet import build_character_sheet
from tests.test_level_one_builds import app_data


@pytest.fixture
def enable_level_17_20_for_test(monkeypatch):
    levels = list(range(1, 21))
    import rules.character_validation as character_validation
    import rules.leveling as leveling

    monkeypatch.setattr(leveling, "SUPPORTED_LEVELS", levels)
    monkeypatch.setattr(character_validation, "SUPPORTED_LEVELS", levels)


def level_eighteen_fighter():
    character = new_character()
    character.update({
        "name": "Epic Fighter",
        "species": "Human",
        "background": "Soldier",
        "class": "Fighter",
        "subclass": "Champion",
        "level": 18,
        "weapon_masteries": ["Longsword", "Longbow", "Dagger", "Shortsword", "Greatsword", "Battleaxe"],
    })
    character["background_options"] = {
        "primary_ability": "Strength",
        "secondary_ability": "Constitution",
    }
    character["species_options"] = {
        "skill_proficiencies": ["Perception"],
        "origin_feats": ["Tough"],
    }
    character["class_options"] = {
        "class_skills": ["Athletics", "Survival"],
        "fighting_style": "Defense",
        "champion_additional_fighting_styles": ["Dueling"],
    }
    character["base_ability_scores"].update({
        "Strength": 18,
        "Dexterity": 14,
        "Constitution": 16,
        "Intelligence": 10,
        "Wisdom": 12,
        "Charisma": 10,
    })
    return character


def test_level_nineteen_prompts_for_epic_boon_and_applies_boon_of_speed(enable_level_17_20_for_test):
    data = app_data()
    character = level_eighteen_fighter()
    recalculate_character(character, data)
    before_speed = character["speed"]

    draft = create_level_up_draft(character, 19, data)
    epic_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "feat_selection")
    speed_boon = next(feat for feat in epic_choice["feat_options"] if feat["name"] == "Boon of Speed")

    assert epic_choice["name"] == "Epic Boon"
    assert "epic_boon" in {feat["category"] for feat in epic_choice["feat_options"]}
    assert "general" in {feat["category"] for feat in epic_choice["feat_options"]}
    assert "Boon of Spell Recall" not in {feat["name"] for feat in epic_choice["feat_options"]}

    assert resolve_pending_choice(
        draft,
        epic_choice["id"],
        {
            "mode": "feat",
            "feat_id": speed_boon["id"],
            "feat_name": speed_boon["name"],
            "feat_ability_choice": "Strength",
            "feat_choices": {},
        },
        epic_choice,
    )
    result = commit_level_up_draft(character, draft, data)
    assert result["ok"], result

    recalculate_character(character, data)
    sheet = build_character_sheet(character)

    assert character["level"] == 19
    assert character["ability_scores"]["Strength"] == 21
    assert character["speed"] == before_speed + 30
    assert "Boon of Speed" in sheet["general_feats"]


def test_epic_boon_sheet_value_effects_apply_during_recalculation(enable_level_17_20_for_test):
    data = app_data()
    character = level_eighteen_fighter()
    character["level"] = 19
    character["general_feats"] = [
        {
            "instance_id": "fortitude",
            "feat_id": "boon_of_fortitude_xphb",
            "name": "Boon of Fortitude",
            "source": {},
            "choices": {"ability": "Constitution"},
        },
        {
            "instance_id": "skill",
            "feat_id": "boon_of_skill_xphb",
            "name": "Boon of Skill",
            "source": {},
            "choices": {"ability": "Wisdom", "expertise": "Perception"},
        },
        {
            "instance_id": "energy",
            "feat_id": "boon_of_energy_resistance_xphb",
            "name": "Boon of Energy Resistance",
            "source": {},
            "choices": {"ability": "Constitution", "damage_types": ["Fire", "Cold"]},
        },
    ]

    recalculate_character(character, data)
    sheet = build_character_sheet(character)
    fortitude = next(detail for detail in sheet["general_feat_details"] if detail["name"] == "Boon of Fortitude")
    energy = next(detail for detail in sheet["general_feat_details"] if detail["name"] == "Boon of Energy Resistance")

    assert character["hit_points"]["max"] >= 40
    assert set(data["rules"]["skills"]).issubset(set(character["skill_proficiencies"]))
    assert "Perception" in character["expertise"]
    assert fortitude["choices"]["ability"] == "Constitution"
    assert energy["choices"]["damage_types"] == ["Fire", "Cold"]
