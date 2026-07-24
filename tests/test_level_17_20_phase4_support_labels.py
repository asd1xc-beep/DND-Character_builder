from models.character import new_character
from rules.feat_rules import feat_support_status
from services.character_engine import recalculate_character
from services.character_sheet import build_character_sheet
from tests.test_level_one_builds import app_data


def high_level_character(class_name, level, subclass=""):
    character = new_character()
    character.update({
        "name": f"Level {level} {class_name}",
        "species": "Human",
        "background": "Sage",
        "class": class_name,
        "subclass": subclass,
        "level": level,
    })
    character["background_options"] = {
        "primary_ability": "Wisdom",
        "secondary_ability": "Constitution",
    }
    character["species_options"] = {
        "skill_proficiencies": ["Perception"],
        "origin_feats": ["Tough"],
    }
    character["class_options"] = {"class_skills": ["Arcana", "Insight"]}
    character["base_ability_scores"].update({
        "Strength": 14,
        "Dexterity": 14,
        "Constitution": 16,
        "Intelligence": 16,
        "Wisdom": 18,
        "Charisma": 18,
    })
    return character


def feat_by_name(data, name):
    return next(feat for feat in data["feats"] if feat["name"] == name)


def test_high_level_subclass_sheet_values_are_supported():
    data = app_data()
    light = high_level_character("Cleric", 17, "Light Domain")
    war = high_level_character("Cleric", 17, "War Domain")
    psi = high_level_character("Fighter", 18, "Psi Warrior")
    draconic = high_level_character("Sorcerer", 18, "Draconic Sorcery")

    for character in (light, war, psi, draconic):
        recalculate_character(character, data)

    assert build_character_sheet(light)["resources"]["corona_of_light_uses"] == light["ability_modifiers"]["Wisdom"]
    assert build_character_sheet(light)["resources"]["corona_of_light_recharge"] == "long_rest"

    war_sheet = build_character_sheet(war)
    assert set(war_sheet["resources"]["damage_resistances"]) == {"Bludgeoning", "Piercing", "Slashing"}
    assert all(
        sources == ["Avatar of Battle"]
        for sources in war_sheet["resources"]["damage_resistance_sources"].values()
    )

    psi_grant = next(
        grant
        for grant in build_character_sheet(psi)["spells"]["grant_details"]
        if grant["source"].get("source_name") == "Telekinetic Master"
    )
    assert psi_grant["name"] == "Telekinesis"
    assert psi_grant["spellcasting_ability"] == "Intelligence"
    assert psi_grant["casting_rules"]["free_casts"] == 1
    assert psi_grant["casting_rules"]["alternate_recovery_resource"] == "Psionic Energy Die"

    dragon_grant = next(
        grant
        for grant in build_character_sheet(draconic)["spells"]["grant_details"]
        if grant["source"].get("source_name") == "Dragon Companion"
    )
    assert dragon_grant["name"] == "Summon Dragon"
    assert dragon_grant["spellcasting_ability"] == "Charisma"
    assert dragon_grant["casting_rules"]["free_casts"] == 1
    assert dragon_grant["casting_rules"]["material_component_required"] is False
    assert dragon_grant["casting_rules"]["can_remove_concentration"] is True


def test_epic_boon_support_labels_and_sheet_values_are_precise():
    data = app_data()
    truesight = feat_by_name(data, "Boon of Truesight")
    energy = feat_by_name(data, "Boon of Energy Resistance")
    recovery = feat_by_name(data, "Boon of Recovery")
    night_spirit = feat_by_name(data, "Boon of the Night Spirit")

    assert feat_support_status(truesight)["sheet_calculation"] == "supported"
    assert feat_support_status(energy)["selection"] == "supported"
    assert feat_support_status(energy)["sheet_calculation"] == "supported"
    assert feat_support_status(recovery)["sheet_calculation"] == "partial"
    assert feat_support_status(night_spirit)["sheet_calculation"] == "description_only"

    character = high_level_character("Fighter", 19, "Champion")
    character["general_feats"] = [
        {
            "instance_id": "truesight",
            "feat_id": "boon_of_truesight_xphb",
            "name": "Boon of Truesight",
            "source": {},
            "choices": {"ability": "Wisdom"},
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

    assert sheet["resources"]["truesight_range"] == 60
    assert sheet["senses"][0]["type"] == "Truesight"
    assert set(sheet["resources"]["damage_resistances"]) == {"Fire", "Cold"}
    assert sheet["resources"]["damage_resistance_sources"] == {
        "Fire": ["Boon of Energy Resistance"],
        "Cold": ["Boon of Energy Resistance"],
    }
