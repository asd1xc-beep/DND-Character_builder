from models.character import new_character
from rules.character_validation import build_validation_report
from rules.class_choice_rules import battle_master_progression, metamagic_feature_level, metamagic_total_for_level
from rules.level_up import create_level_up_draft, resolve_pending_choice
from rules.leveling import effective_spellcasting
from services.character_engine import recalculate_character
from services.character_sheet import build_character_sheet
from tests.test_level_one_builds import app_data, finalized
from tests.test_level_9_12_enablement import level_eight_lore_bard, resolve_basic_level_up_choices
from tests.test_level_up import level_three_character, level_one_fighter


def test_level_ten_bard_magical_secrets_changes_eligibility_not_prepared_total():
    data = app_data()
    character = level_eight_lore_bard()

    finalized(character, data)
    level_nine = create_level_up_draft(character, 9, data)
    resolve_basic_level_up_choices(level_nine)
    from rules.level_up import commit_level_up_draft

    assert commit_level_up_draft(character, level_nine, data)["ok"]

    level_ten = create_level_up_draft(character, 10, data)
    prepared_choice = next(choice for choice in level_ten["pending_choices"] if choice.get("spell_field") == "prepared")
    bard_data = data["classes_by_name"]["Bard"]

    assert effective_spellcasting(bard_data, "College of Lore", 10)["prepared_spells"] == 15
    assert prepared_choice["choose"] == 1
    assert "Cone of Cold" in prepared_choice["options"]
    assert not any(choice.get("class_option_key") == "magical_secrets" for choice in level_ten["pending_choices"])


def test_level_ten_bard_validation_accepts_cross_list_prepared_spells_and_rejects_over_limit():
    data = app_data()
    bard_data = data["classes_by_name"]["Bard"]
    character = level_eight_lore_bard()
    character["level"] = 10
    character["spells"]["cantrips"] = ["Blade Ward", "Dancing Lights", "Mage Hand", "Vicious Mockery"]
    character["spells"]["prepared"] = character["spells"]["prepared"] + [
        "Heroism",
        "Invisibility",
        "Cone of Cold",
    ]

    report = build_validation_report(character, bard_data, spells=data["spells"])

    assert "Cone of Cold is not on the Bard, Cleric, Druid, Wizard spell list" not in report["missing"]
    assert "Choose no more than 15 prepared spells" not in report["missing"]

    character["spells"]["prepared"].append("Mass Cure Wounds")
    report = build_validation_report(character, bard_data, spells=data["spells"])

    assert "Choose no more than 15 prepared spells" in report["missing"]


def test_sorcerer_metamagic_semantic_totals():
    assert metamagic_total_for_level(2) == 2
    assert metamagic_total_for_level(10) == 4
    assert metamagic_total_for_level(17) == 6
    assert metamagic_feature_level(2) == 2
    assert metamagic_feature_level(10) == 10
    assert metamagic_feature_level(17) == 17

    data = app_data()
    character = new_character()
    character.update({
        "name": "Ember",
        "species": "Human",
        "background": "Sage",
        "class": "Sorcerer",
        "level": 9,
    })
    character["class_options"] = {
        "class_skills": ["Arcana", "Persuasion"],
        "metamagic": ["Quickened Spell", "Subtle Spell"],
    }

    draft = create_level_up_draft(character, 10, data)
    choice = next(choice for choice in draft["pending_choices"] if choice.get("class_option_key") == "metamagic")

    assert choice["choose"] == 2


def test_battle_master_progression_semantics_at_levels_seven_and_ten():
    assert battle_master_progression(3) == {
        "maneuvers_known": 3,
        "superiority_dice": 4,
        "superiority_die": "d8",
    }
    assert battle_master_progression(7) == {
        "maneuvers_known": 5,
        "superiority_dice": 5,
        "superiority_die": "d8",
    }
    assert battle_master_progression(10) == {
        "maneuvers_known": 7,
        "superiority_dice": 5,
        "superiority_die": "d10",
    }
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

    data = app_data()
    character = level_three_character(level_one_fighter(), "Battle Master", data)
    character["class_options"].update({
        "maneuvers": ["Ambush", "Parry", "Trip Attack"],
        "battle_master_save_ability": "Strength",
        "student_of_war_skill": "Athletics",
        "student_of_war_tool": "Smith's Tools",
    })
    character["level"] = 7
    recalculate_character(character, data)
    sheet = build_character_sheet(character)

    assert "Choose 5 Battle Master maneuvers" in build_validation_report(
        character,
        data["classes_by_name"]["Fighter"],
    )["missing"]
    assert sheet["resources"]["maneuvers_known"] == 5
    assert sheet["resources"]["superiority_dice"] == 5
    assert sheet["resources"]["superiority_die"] == "d8"

    character["class_options"]["maneuvers"].extend(["Commander's Strike", "Disarming Attack"])
    character["level"] = 9
    draft = create_level_up_draft(character, 10, data)
    choice = next(choice for choice in draft["pending_choices"] if choice.get("class_option_key") == "maneuvers")

    assert choice["choose"] == 2

    character["level"] = 10
    character["class_options"]["maneuvers"].extend(choice["options"][:2])
    recalculate_character(character, data)
    sheet = build_character_sheet(character)

    assert sheet["resources"]["maneuvers_known"] == 7
    assert sheet["resources"]["superiority_dice"] == 5
    assert sheet["resources"]["superiority_die"] == "d10"
