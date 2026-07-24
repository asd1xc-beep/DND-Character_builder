from models.character import new_character
from rules.level_up import commit_level_up_draft, create_level_up_draft, refresh_level_up_draft_choices, resolve_pending_choice
from rules.leveling import selected_subclass_options
from services.character_engine import recalculate_character
from tests.test_level_one_builds import app_data, finalized


def level_three_land_druid():
    character = new_character()
    character.update({
        "name": "Mira",
        "species": "Dwarf",
        "background": "Farmer",
        "class": "Druid",
        "subclass": "Circle of the Land",
        "level": 3,
    })
    character["background_options"] = {
        "primary_ability": "Wisdom",
        "secondary_ability": "Constitution",
    }
    character["class_options"] = {
        "class_skills": ["Medicine", "Survival"],
        "primal_order": "Warden",
        "wild_shape_forms": ["Rat", "Riding Horse", "Spider", "Wolf"],
    }
    character["spells"] = {
        "cantrips": ["Druidcraft", "Starry Wisp"],
        "prepared": ["Animal Friendship", "Cure Wounds", "Entangle", "Healing Word", "Moonbeam", "Spike Growth"],
        "known": [],
    }
    character["base_ability_scores"]["Wisdom"] = 16
    return character


def level_three_lore_bard():
    character = new_character()
    character.update({
        "name": "Lyra",
        "species": "Dwarf",
        "background": "Farmer",
        "class": "Bard",
        "subclass": "College of Lore",
        "level": 3,
    })
    character["background_options"] = {
        "primary_ability": "Constitution",
        "secondary_ability": "Wisdom",
    }
    character["class_options"] = {
        "class_skills": ["Performance", "Persuasion", "Stealth"],
        "bard_expertise": ["Performance", "Persuasion"],
    }
    character["spells"] = {
        "cantrips": ["Mage Hand", "Vicious Mockery"],
        "prepared": ["Charm Person", "Cure Wounds", "Detect Magic", "Faerie Fire", "Healing Word", "Invisibility"],
        "known": [],
    }
    return character


def level_three_ranger(subclass):
    character = new_character()
    character.update({
        "name": "Tamsin",
        "species": "Dwarf",
        "background": "Farmer",
        "class": "Ranger",
        "subclass": subclass,
        "level": 3,
        "weapon_masteries": ["Longbow", "Shortsword"],
    })
    character["background_options"] = {
        "primary_ability": "Wisdom",
        "secondary_ability": "Dexterity",
    }
    character["class_options"] = {
        "class_skills": ["Athletics", "Perception", "Stealth"],
        "ranger_deft_explorer_expertise": ["Perception"],
        "ranger_languages": ["Elvish", "Sylvan"],
        "fighting_style": "Archery",
    }
    character["spells"] = {
        "cantrips": [],
        "prepared": ["Cure Wounds", "Ensnaring Strike", "Hunter's Mark", "Jump"],
        "known": [],
    }
    return character


def test_circle_of_the_land_requires_one_land_spell_group():
    data = app_data()
    druid_data = data["classes_by_name"]["Druid"]
    rule = selected_subclass_options(druid_data, "Circle of the Land")["structured_spell_choice"]

    assert rule["choose"] == 1
    assert [option["name"] for option in rule["options"]] == [
        "Arid Land",
        "Polar Land",
        "Temperate Land",
        "Tropical Land",
    ]

    character = level_three_land_druid()
    sheet, report = finalized(character, data)

    assert not report["complete"]
    assert "Choose Subclass spell group" in report["missing"]
    assert "Burning Hands" not in sheet["spells"]["granted"]
    assert "Ray of Frost" not in sheet["spells"]["granted"]


def test_circle_of_the_land_grants_only_selected_land_spells():
    data = app_data()
    character = level_three_land_druid()

    character["class_options"]["structured_spell_choice"] = "Arid Land"
    sheet, report = finalized(character, data)

    assert report["complete"]
    assert "Blur" in sheet["spells"]["granted"]
    assert "Burning Hands" in sheet["spells"]["granted"]
    assert "Fire Bolt" in sheet["spells"]["granted"]
    assert "Ray of Frost" not in sheet["spells"]["granted"]
    assert "Web" not in sheet["spells"]["granted"]

    from rules.feature_configurations import update_feature_configuration

    assert update_feature_configuration(character, "structured_spell_choice", "Tropical Land")
    sheet, report = finalized(character, data)

    assert "Acid Splash" in sheet["spells"]["granted"]
    assert "Ray of Sickness" in sheet["spells"]["granted"]
    assert "Web" in sheet["spells"]["granted"]
    assert "Blur" not in sheet["spells"]["granted"]
    assert "Burning Hands" not in sheet["spells"]["granted"]


def test_circle_of_the_land_grants_later_terrain_spells_and_can_change_after_rest():
    data = app_data()
    character = level_three_land_druid()
    character["level"] = 9
    character["class_options"]["structured_spell_choice"] = "Arid Land"

    sheet, report = finalized(character, data)

    assert "Fireball" in sheet["spells"]["granted"]
    assert "Blight" in sheet["spells"]["granted"]
    assert "Wall of Stone" in sheet["spells"]["granted"]
    assert "Cone of Cold" not in sheet["spells"]["granted"]

    from rules.feature_configurations import update_feature_configuration

    assert update_feature_configuration(character, "structured_spell_choice", "Polar Land")
    recalculate_character(character, data)
    sheet = finalized(character, data)[0]

    assert character["class_options"]["structured_spell_choice"] == "Arid Land"
    assert "Cone of Cold" in sheet["spells"]["granted"]
    assert "Wall of Stone" not in sheet["spells"]["granted"]


def test_changing_subclass_ignores_old_structured_spell_choice():
    data = app_data()
    character = level_three_land_druid()
    character["subclass"] = "Circle of the Moon"
    character["class_options"]["structured_spell_choice"] = "Arid Land"

    sheet, report = finalized(character, data)

    assert report["complete"]
    assert "Burning Hands" not in sheet["spells"]["granted"]
    assert "Fire Bolt" not in sheet["spells"]["granted"]
    assert "Cure Wounds" in sheet["spells"]["granted"]
    assert "Moonbeam" in sheet["spells"]["granted"]


def test_college_of_lore_bonus_skills_are_required_and_applied():
    data = app_data()
    character = level_three_lore_bard()

    sheet, report = finalized(character, data)
    assert not report["complete"]
    assert "Choose 3 College of Lore skills" in report["missing"]

    character["class_options"]["lore_skills"] = ["Arcana", "History", "Insight"]
    sheet, report = finalized(character, data)

    assert report["complete"]
    assert "Arcana" in character["skill_proficiencies"]
    assert "History" in character["skill_proficiencies"]
    assert "Insight" in character["skill_proficiencies"]


def test_hunter_prey_choice_is_required_and_added_as_feature():
    data = app_data()
    character = level_three_ranger("Hunter")

    sheet, report = finalized(character, data)
    assert not report["complete"]
    assert "Choose Hunter's Prey" in report["missing"]

    character["class_options"]["hunters_prey"] = "Colossus Slayer"
    sheet, report = finalized(character, data)

    assert report["complete"]
    assert "Colossus Slayer" in sheet["features"]


def test_beast_master_companion_choice_is_required_and_added_as_feature():
    data = app_data()
    character = level_three_ranger("Beast Master")

    sheet, report = finalized(character, data)
    assert not report["complete"]
    assert "Choose Primal Companion" in report["missing"]

    character["class_options"]["primal_companion"] = "Beast of the Sky"
    sheet, report = finalized(character, data)

    assert report["complete"]
    assert "Beast of the Sky" in sheet["features"]


def test_subclass_sheet_value_proficiencies_and_ac_are_automated():
    data = app_data()

    dance_bard = level_three_bard("College of Dance")
    recalculate_character(dance_bard, data)
    assert dance_bard["armor_class"] == 15

    valor_bard = level_three_bard("College of Valor")
    recalculate_character(valor_bard, data)
    assert "Medium Armor" in valor_bard["armor_proficiencies"]
    assert "Shields" in valor_bard["armor_proficiencies"]
    assert "Martial Weapons" in valor_bard["weapon_proficiencies"]

    mercy_monk = level_three_monk("Warrior of Mercy")
    recalculate_character(mercy_monk, data)
    assert "Insight" in mercy_monk["skill_proficiencies"]
    assert "Medicine" in mercy_monk["skill_proficiencies"]
    assert "Herbalism Kit" in mercy_monk["tool_proficiencies"]

    draconic_sorcerer = level_six_draconic_sorcerer()
    recalculate_character(draconic_sorcerer, data)
    assert draconic_sorcerer["armor_class"] == 15
    assert draconic_sorcerer["hit_points"]["max"] == 50


def test_fey_wanderer_otherworldly_glamour_skill_is_required_and_applied():
    data = app_data()
    character = level_three_ranger("Fey Wanderer")

    sheet, report = finalized(character, data)
    assert not report["complete"]
    assert "Choose Otherworldly Glamour skill" in report["missing"]

    character["class_options"]["fey_wanderer_skill"] = "Persuasion"
    sheet, report = finalized(character, data)

    assert report["complete"]
    assert "Persuasion" in character["skill_proficiencies"]


def test_fey_wanderer_level_up_flow_prompts_for_otherworldly_glamour_skill():
    data = app_data()
    character = level_three_ranger("Hunter")
    character["subclass"] = ""
    character["level"] = 2
    character["class_options"].pop("hunters_prey", None)
    finalized(character, data)

    draft = create_level_up_draft(character, 3, data)
    subclass_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "subclass_choice")
    assert resolve_pending_choice(draft, subclass_choice["id"], "Fey Wanderer")
    refresh_level_up_draft_choices(character, draft, data)
    skill_choice = next(choice for choice in draft["pending_choices"] if choice.get("class_option_key") == "fey_wanderer_skill")
    assert resolve_pending_choice(draft, skill_choice["id"], "Persuasion")

    result = commit_level_up_draft(character, draft, data)
    sheet, report = finalized(character, data)

    assert result["ok"]
    assert report["complete"]
    assert character["subclass"] == "Fey Wanderer"
    assert "Persuasion" in character["skill_proficiencies"]


def level_three_bard(subclass):
    character = new_character()
    character.update({
        "name": "Dancer",
        "species": "Dwarf",
        "background": "Farmer",
        "class": "Bard",
        "subclass": subclass,
        "level": 3,
    })
    character["background_options"] = {
        "primary_ability": "Charisma",
        "secondary_ability": "Dexterity",
    }
    character["class_options"] = {
        "class_skills": ["Performance", "Persuasion", "Stealth"],
        "bard_expertise": ["Performance", "Persuasion"],
    }
    character["spells"] = {
        "cantrips": ["Mage Hand", "Vicious Mockery"],
        "prepared": ["Charm Person", "Cure Wounds", "Detect Magic", "Faerie Fire", "Healing Word", "Invisibility"],
        "known": [],
    }
    character["base_ability_scores"]["Dexterity"] = 13
    character["base_ability_scores"]["Charisma"] = 14
    return character


def level_three_monk(subclass):
    character = new_character()
    character.update({
        "name": "Mercy",
        "species": "Dwarf",
        "background": "Farmer",
        "class": "Monk",
        "subclass": subclass,
        "level": 3,
    })
    character["background_options"] = {
        "primary_ability": "Dexterity",
        "secondary_ability": "Wisdom",
    }
    character["class_options"] = {
        "class_skills": ["Acrobatics", "Stealth"],
    }
    return character


def level_six_draconic_sorcerer():
    character = new_character()
    character.update({
        "name": "Ember",
        "species": "Dwarf",
        "background": "Soldier",
        "class": "Sorcerer",
        "subclass": "Draconic Sorcery",
        "level": 6,
    })
    character["background_options"] = {
        "primary_ability": "Charisma",
        "secondary_ability": "Dexterity",
    }
    character["class_options"] = {
        "class_skills": ["Arcana", "Persuasion"],
        "metamagic": ["Careful Spell", "Subtle Spell"],
        "elemental_affinity": "Fire",
    }
    character["base_ability_scores"]["Dexterity"] = 13
    character["base_ability_scores"]["Charisma"] = 14
    character["base_ability_scores"]["Constitution"] = 14
    return character
