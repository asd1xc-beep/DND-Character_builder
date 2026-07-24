from models.character import new_character
from rules.class_choice_rules import class_level_up_option_choices
from rules.level_up import apply_resolved_choices
from services.character_engine import recalculate_character
from services.character_sheet import build_character_sheet
from tests.test_level_one_builds import app_data


def future_character(class_name, level):
    character = new_character()
    character.update({
        "name": "Future",
        "species": "Human",
        "background": "Sage",
        "class": class_name,
        "level": level,
    })
    character["background_options"] = {
        "primary_ability": "Dexterity",
        "secondary_ability": "Charisma",
    }
    character["class_options"] = {"class_skills": ["Arcana", "History", "Insight", "Perception", "Performance", "Persuasion"]}
    character["skill_proficiencies"] = ["Arcana", "History", "Insight", "Perception", "Performance", "Persuasion"]
    return character


def choice_by_key(character, class_data, current_level, target_level, data, key):
    choices = class_level_up_option_choices(character, class_data, current_level, target_level, data)
    return next(choice for choice in choices if choice.get("class_option_key") == key)


def test_bard_and_ranger_level_nine_expertise_choices_are_prepared():
    data = app_data()

    bard = future_character("Bard", 8)
    bard["class_options"]["bard_expertise"] = ["Arcana", "Performance"]
    bard["expertise"] = ["Arcana", "Performance"]
    bard_choice = choice_by_key(bard, data["classes_by_name"]["Bard"], 8, 9, data, "bard_level_9_expertise")

    assert bard_choice["choose"] == 2
    assert "Arcana" not in bard_choice["options"]
    assert {"History", "Insight"}.issubset(set(bard_choice["options"]))

    ranger = future_character("Ranger", 8)
    ranger["class_options"]["ranger_deft_explorer_expertise"] = ["Survival"]
    ranger["expertise"] = ["Survival"]
    ranger["skill_proficiencies"].append("Survival")
    ranger_choice = choice_by_key(ranger, data["classes_by_name"]["Ranger"], 8, 9, data, "ranger_level_9_expertise")

    assert ranger_choice["choose"] == 2
    assert "Survival" not in ranger_choice["options"]
    assert {"Arcana", "Perception"}.issubset(set(ranger_choice["options"]))


def test_sorcerer_level_ten_metamagic_choice_scales_existing_selection():
    data = app_data()
    sorcerer = future_character("Sorcerer", 9)
    sorcerer["class_options"]["metamagic"] = ["Quickened Spell", "Subtle Spell"]

    choice = choice_by_key(sorcerer, data["classes_by_name"]["Sorcerer"], 9, 10, data, "metamagic")

    assert choice["choose"] == 2
    assert "Quickened Spell" not in choice["options"]
    assert "Careful Spell" in choice["options"]


def test_bard_level_ten_magical_secrets_expands_prepared_spell_eligibility_without_bonus_grants():
    data = app_data()
    bard = future_character("Bard", 9)
    bard["spells"] = {
        "cantrips": ["Mage Hand", "Vicious Mockery", "Minor Illusion"],
        "prepared": [
            "Animal Friendship",
            "Bane",
            "Charm Person",
            "Color Spray",
            "Command",
            "Comprehend Languages",
            "Cure Wounds",
            "Detect Magic",
            "Dissonant Whispers",
            "Faerie Fire",
            "Feather Fall",
            "Healing Word",
            "Heroism",
            "Invisibility",
        ],
        "known": [],
    }

    choices = class_level_up_option_choices(bard, data["classes_by_name"]["Bard"], 9, 10, data)
    assert not any(choice.get("class_option_key") == "magical_secrets" for choice in choices)

    from rules.level_up import spell_level_up_choices

    spell_choices = spell_level_up_choices(bard, data["classes_by_name"]["Bard"], 9, 10, data["spells"])
    choice = next(choice for choice in spell_choices if choice.get("spell_field") == "prepared")
    selected = ["Cone of Cold"]

    assert choice["choose"] == 1
    assert "Cone of Cold" in choice["options"]
    assert "Mass Cure Wounds" in choice["options"]
    choice["value"] = selected
    choice["status"] = "resolved"
    apply_resolved_choices(bard, [choice])
    bard["level"] = 10
    recalculate_character(bard, data)
    sheet = build_character_sheet(bard)

    assert "Cone of Cold" in sheet["spells"]["prepared"]
    assert "Cone of Cold" not in sheet["spells"]["granted"]
    assert not any(detail["name"] == "Cone of Cold" and "Magical Secrets" in detail["sources"] for detail in sheet["spell_details"])


def test_warlock_level_eleven_mystic_arcanum_grants_sheet_spell_detail():
    data = app_data()
    warlock = future_character("Warlock", 10)
    warlock["background_options"] = {
        "primary_ability": "Charisma",
        "secondary_ability": "Dexterity",
    }
    warlock["class_options"]["eldritch_invocations"] = [
        "Eldritch Mind",
        "Agonizing Blast",
        "Armor of Shadows",
        "Fiendish Vigor",
        "Lessons of the First Ones",
        "Mask of Many Faces",
        "One with Shadows",
    ]
    warlock["spells"] = {
        "cantrips": ["Eldritch Blast", "Mage Hand", "Minor Illusion"],
        "prepared": ["Armor of Agathys", "Hex", "Invisibility", "Hunger of Hadar"],
        "known": [],
    }

    choice = choice_by_key(warlock, data["classes_by_name"]["Warlock"], 10, 11, data, "mystic_arcanum_6")

    assert choice["choose"] == 1
    assert "Arcane Gate" in choice["options"]
    choice["value"] = ["Arcane Gate"]
    choice["status"] = "resolved"
    apply_resolved_choices(warlock, [choice])
    warlock["level"] = 11
    recalculate_character(warlock, data)
    sheet = build_character_sheet(warlock)

    assert "Arcane Gate" in sheet["spells"]["granted"]
    assert warlock["mystic_arcanum"][0]["spell_name"] == "Arcane Gate"
    assert warlock["mystic_arcanum"][0]["spell_level"] == 6
    assert warlock["mystic_arcanum"][0]["source_level"] == 11
    assert warlock["mystic_arcanum"][0]["casting_rules"] == {
        "free_casts": 1,
        "recharge": "long_rest",
        "uses_pact_slots": False,
    }
    assert any(detail["name"] == "Arcane Gate" and "Mystic Arcanum" in detail["sources"] for detail in sheet["spell_details"])
