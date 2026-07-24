from copy import deepcopy

from models.character import new_character
from rules.character_validation import build_validation_report
from rules.class_choice_rules import battle_master_progression, metamagic_total_for_level
from rules.level_up import commit_level_up_draft, create_level_up_draft, resolve_pending_choice
from services.character_engine import recalculate_character
from services.character_sheet import build_character_sheet
from tests.test_level_9_12_enablement import human_options, resolve_basic_level_up_choices
from tests.test_level_one_builds import app_data


def level_sixteen_sorcerer():
    character = new_character()
    character.update({
        "name": "Ember",
        "species": "Human",
        "background": "Sage",
        "class": "Sorcerer",
        "subclass": "Draconic Sorcery",
        "level": 16,
    })
    character.update(human_options("Charisma", "Constitution"))
    character["base_ability_scores"]["Charisma"] = 18
    character["class_options"] = {
        "class_skills": ["Arcana", "Persuasion"],
        "metamagic": ["Careful Spell", "Quickened Spell", "Subtle Spell", "Twinned Spell"],
        "elemental_affinity": "Fire",
    }
    return character


def level_fourteen_battle_master():
    character = new_character()
    character.update({
        "name": "Astra",
        "species": "Human",
        "background": "Soldier",
        "class": "Fighter",
        "subclass": "Battle Master",
        "level": 14,
        "weapon_masteries": ["Longsword", "Longbow", "Dagger", "Shortsword", "Greatsword"],
    })
    character.update(human_options("Strength", "Constitution"))
    character["base_ability_scores"]["Strength"] = 18
    character["class_options"] = {
        "class_skills": ["Acrobatics", "Survival"],
        "fighting_style": "Defense",
        "maneuvers": [
            "Ambush",
            "Commander's Strike",
            "Disarming Attack",
            "Distracting Strike",
            "Evasive Footwork",
            "Feinting Attack",
            "Goading Attack",
        ],
        "battle_master_save_ability": "Strength",
        "student_of_war_skill": "Athletics",
        "student_of_war_tool": "Smith's Tools",
    }
    return character


def level_eighteen_fighter_for_feat_choice():
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
    character.update(human_options("Strength", "Constitution"))
    character["base_ability_scores"]["Strength"] = 18
    character["base_ability_scores"]["Constitution"] = 16
    character["class_options"] = {
        "class_skills": ["Athletics", "Survival"],
        "fighting_style": "Defense",
        "champion_additional_fighting_styles": ["Dueling"],
    }
    return character


def test_sorcerer_level_seventeen_requires_two_new_metamagic_options():
    data = app_data()
    character = level_sixteen_sorcerer()
    recalculate_character(character, data)

    assert metamagic_total_for_level(17) == 6
    draft = create_level_up_draft(character, 17, data)
    metamagic = next(choice for choice in draft["pending_choices"] if choice.get("class_option_key") == "metamagic")

    assert metamagic["choose"] == 2
    assert set(character["class_options"]["metamagic"]).isdisjoint(set(metamagic["options"]))
    assert not draft["can_finalize"]
    assert not commit_level_up_draft(character, draft, data)["ok"]

    assert resolve_pending_choice(draft, metamagic["id"], metamagic["options"][:2], metamagic)
    resolve_basic_level_up_choices(draft)
    result = commit_level_up_draft(character, draft, data)
    assert result["ok"], result

    recalculate_character(character, data)
    assert character["level"] == 17
    assert len(character["class_options"]["metamagic"]) == 6
    assert character["class_options"]["metamagic"][:4] == [
        "Careful Spell",
        "Quickened Spell",
        "Subtle Spell",
        "Twinned Spell",
    ]


def test_battle_master_level_fifteen_and_eighteen_progression_is_complete():
    data = app_data()
    character = level_fourteen_battle_master()
    recalculate_character(character, data)

    assert battle_master_progression(15) == {
        "maneuvers_known": 9,
        "superiority_dice": 6,
        "superiority_die": "d10",
    }
    assert battle_master_progression(18) == {
        "maneuvers_known": 9,
        "superiority_dice": 6,
        "superiority_die": "d12",
    }

    draft = create_level_up_draft(character, 15, data)
    maneuver_choice = next(choice for choice in draft["pending_choices"] if choice.get("class_option_key") == "maneuvers")
    assert maneuver_choice["choose"] == 2

    validation_character = deepcopy(character)
    validation_character["level"] = 15
    missing = build_validation_report(validation_character, data["classes_by_name"]["Fighter"])["missing"]
    assert "Choose 9 Battle Master maneuvers" in missing

    resolve_basic_level_up_choices(draft, asi_ability="Strength")
    result = commit_level_up_draft(character, draft, data)
    assert result["ok"], result
    recalculate_character(character, data)
    sheet = build_character_sheet(character)

    assert len(character["class_options"]["maneuvers"]) == 9
    assert sheet["resources"]["maneuvers_known"] == 9
    assert sheet["resources"]["superiority_dice"] == 6
    assert sheet["resources"]["superiority_die"] == "d10"

    character["level"] = 17
    recalculate_character(character, data)
    level_eighteen = create_level_up_draft(character, 18, data)
    assert not any(choice.get("class_option_key") == "maneuvers" for choice in level_eighteen["pending_choices"])

    resolve_basic_level_up_choices(level_eighteen, asi_ability="Strength")
    result = commit_level_up_draft(character, level_eighteen, data)
    assert result["ok"], result
    recalculate_character(character, data)
    sheet = build_character_sheet(character)

    assert sheet["resources"]["maneuvers_known"] == 9
    assert sheet["resources"]["superiority_dice"] == 6
    assert sheet["resources"]["superiority_die"] == "d12"


def test_level_nineteen_allows_epic_boons_or_qualified_general_feats():
    data = app_data()
    character = level_eighteen_fighter_for_feat_choice()
    recalculate_character(character, data)

    draft = create_level_up_draft(character, 19, data)
    feat_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "feat_selection")
    feat_names = {feat["name"] for feat in feat_choice["feat_options"]}
    categories = {feat["category"] for feat in feat_choice["feat_options"]}

    assert "epic_boon" in categories
    assert "general" in categories
    assert "Boon of Speed" in feat_names
    assert "Great Weapon Master" in feat_names

    great_weapon_master = next(feat for feat in feat_choice["feat_options"] if feat["name"] == "Great Weapon Master")
    assert resolve_pending_choice(
        draft,
        feat_choice["id"],
        {
            "mode": "feat",
            "feat_id": great_weapon_master["id"],
            "feat_name": great_weapon_master["name"],
            "feat_ability_choice": "",
            "feat_choices": {},
        },
        feat_choice,
    )
    result = commit_level_up_draft(character, draft, data)
    assert result["ok"], result

    recalculate_character(character, data)
    sheet = build_character_sheet(character)
    assert character["level"] == 19
    assert "Great Weapon Master" in sheet["general_feats"]
    assert sheet["resources"]["great_weapon_master_damage_bonus"] == character["proficiency_bonus"]
