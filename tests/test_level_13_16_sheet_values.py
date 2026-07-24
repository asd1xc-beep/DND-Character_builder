from models.character import new_character
from services.character_engine import recalculate_character
from services.character_sheet import build_character_sheet
from tests.test_level_one_builds import app_data


def high_level_character(class_name, level, subclass=""):
    character = new_character()
    character.update({
        "name": "High Level",
        "species": "Human",
        "background": "Sage",
        "class": class_name,
        "subclass": subclass,
        "level": level,
    })
    character["background_options"] = {
        "primary_ability": "Wisdom",
        "secondary_ability": "Dexterity",
    }
    character["species_options"] = {
        "skill_proficiencies": ["Perception"],
        "origin_feats": ["Tough"],
    }
    character["class_options"] = {"class_skills": ["Arcana", "Insight"]}
    character["base_ability_scores"]["Wisdom"] = 16
    character["base_ability_scores"]["Intelligence"] = 16
    character["base_ability_scores"]["Charisma"] = 14
    return character


def test_monk_and_rogue_high_level_saving_throw_features_are_sheet_values():
    data = app_data()
    monk = high_level_character("Monk", 14)
    rogue = high_level_character("Rogue", 15)
    rogue["class_options"]["rogue_thieves_cant_language"] = "Elvish"
    rogue["class_options"]["rogue_level_6_expertise"] = ["Arcana", "Insight"]

    recalculate_character(monk, data)
    recalculate_character(rogue, data)

    assert set(monk["saving_throw_proficiencies"]) == {
        "Strength",
        "Dexterity",
        "Constitution",
        "Intelligence",
        "Wisdom",
        "Charisma",
    }
    assert "Wisdom" in rogue["saving_throw_proficiencies"]
    assert "Charisma" in rogue["saving_throw_proficiencies"]


def test_diviner_greater_portent_updates_portent_dice_resource():
    data = app_data()
    wizard = high_level_character("Wizard", 14, "Diviner")
    wizard["class_options"]["wizard_scholar_skill"] = "Arcana"

    recalculate_character(wizard, data)

    assert wizard["derived_resources"]["portent_dice"] == 3

    wizard["level"] = 13
    recalculate_character(wizard, data)

    assert wizard["derived_resources"]["portent_dice"] == 2


def test_level_thirteen_to_sixteen_class_resources_add_sheet_counters():
    data = app_data()
    fighter = high_level_character("Fighter", 13, "Champion")
    ranger = high_level_character("Ranger", 14, "Hunter")
    ranger["class_options"].update({
        "class_skills": ["Animal Handling", "Nature", "Survival"],
        "fighting_style": "Archery",
        "ranger_deft_explorer_expertise": ["Perception"],
        "ranger_level_9_expertise": ["Arcana", "Insight"],
        "ranger_languages": ["Elvish", "Sylvan"],
    })

    recalculate_character(fighter, data)
    recalculate_character(ranger, data)

    assert fighter["derived_resources"]["indomitable_uses"] == 2
    assert fighter["derived_resources"]["indomitable_recharge"] == "long_rest"
    assert ranger["derived_resources"]["natures_veil_uses"] == ranger["ability_modifiers"]["Wisdom"]
    assert ranger["derived_resources"]["natures_veil_recharge"] == "long_rest"


def test_level_thirteen_to_sixteen_subclass_resources_add_sheet_counters():
    data = app_data()
    paladin = high_level_character("Paladin", 15, "Glory")
    berserker = high_level_character("Barbarian", 14, "Berserker")
    soulknife = high_level_character("Rogue", 13, "Soulknife")
    psi_warrior = high_level_character("Fighter", 15, "Psi Warrior")
    soulknife["class_options"]["rogue_thieves_cant_language"] = "Elvish"
    soulknife["class_options"]["rogue_level_6_expertise"] = ["Arcana", "Insight"]

    for character in [paladin, berserker, soulknife, psi_warrior]:
        recalculate_character(character, data)

    assert paladin["derived_resources"]["glorious_defense_uses"] == paladin["ability_modifiers"]["Charisma"]
    assert paladin["derived_resources"]["glorious_defense_recharge"] == "long_rest"
    assert berserker["derived_resources"]["intimidating_presence_free_uses"] == 1
    assert berserker["derived_resources"]["intimidating_presence_alternate_recovery_resource"] == "Rage"
    assert soulknife["derived_resources"]["psychic_veil_free_uses"] == 1
    assert soulknife["derived_resources"]["psychic_veil_alternate_recovery_resource"] == "Psionic Energy Die"
    assert psi_warrior["derived_resources"]["bulwark_of_force_free_uses"] == 1
    assert psi_warrior["derived_resources"]["bulwark_of_force_targets"] == psi_warrior["ability_modifiers"]["Intelligence"]
    assert psi_warrior["derived_resources"]["bulwark_of_force_alternate_recovery_resource"] == "Psionic Energy Die"


def test_rogue_strike_feature_references_are_added_to_final_sheet_details():
    data = app_data()
    rogue = high_level_character("Rogue", 14, "Thief")
    rogue["class_options"]["rogue_thieves_cant_language"] = "Elvish"
    rogue["class_options"]["rogue_level_6_expertise"] = ["Arcana", "Insight"]

    recalculate_character(rogue, data)
    sheet = build_character_sheet(rogue)
    details = {feature["name"]: feature for feature in sheet["feature_details"]}

    assert [option["name"] for option in details["Cunning Strike"]["related_features"]] == [
        "Poison",
        "Trip",
        "Withdraw",
    ]
    assert [option["cost"] for option in details["Cunning Strike"]["related_features"]] == ["1d6", "1d6", "1d6"]
    assert [option["name"] for option in details["Devious Strikes"]["related_features"]] == [
        "Daze",
        "Knock Out",
        "Obscure",
    ]


def test_fey_wanderer_misty_wanderer_adds_misty_step_casting_metadata():
    data = app_data()
    ranger = high_level_character("Ranger", 15, "Fey Wanderer")
    ranger["class_options"].update({
        "fighting_style": "Archery",
        "ranger_deft_explorer_expertise": ["Perception"],
        "ranger_level_9_expertise": ["Arcana", "Insight"],
        "ranger_languages": ["Elvish", "Sylvan"],
        "fey_wanderer_skill": "Persuasion",
    })

    recalculate_character(ranger, data)
    sheet = build_character_sheet(ranger)
    grant = next(
        grant
        for grant in sheet["spells"]["grant_details"]
        if grant["name"] == "Misty Step"
        and grant["source"].get("source_name") == "Misty Wanderer"
    )

    assert "Misty Step" in sheet["spells"]["granted"]
    assert grant["spellcasting_ability"] == "Wisdom"
    assert grant["casting_rules"]["free_casts"] == ranger["ability_modifiers"]["Wisdom"]
    assert grant["casting_rules"]["recharge"] == "long_rest"
    assert grant["casting_rules"]["can_bring_willing_creature"] is True
