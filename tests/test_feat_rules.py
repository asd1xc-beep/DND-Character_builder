from models.character import new_character
from rules.choice_validation import (
    ability_adjustment_from_asi,
    ability_adjustment_from_feat,
    build_asi_or_feat_choice,
    validate_asi_selection,
    validate_feat_selection,
)
from rules.feat_rules import (
    eligible_feats,
    feat_by_id,
    feat_choice_schema,
    feat_is_eligible,
    feat_is_supported_for_selection,
    feat_support_status,
    general_feat_names,
)
from services.character_engine import recalculate_character
from services.character_sheet import build_character_sheet
from tests.test_level_one_builds import app_data


def feat_by_name(feats, name):
    return next(feat for feat in feats if feat["name"] == name)


def level_four_character(class_name="Fighter"):
    character = new_character()
    character.update({
        "name": "Level Four",
        "species": "Human",
        "background": "Soldier",
        "class": class_name,
        "level": 4,
    })
    character["base_ability_scores"].update({
        "Strength": 13,
        "Dexterity": 12,
        "Constitution": 14,
        "Intelligence": 10,
        "Wisdom": 10,
        "Charisma": 13,
    })
    character["background_options"] = {
        "primary_ability": "Constitution",
        "secondary_ability": "Wisdom",
    }
    return character


def test_imported_general_feats_are_normalized_for_level_four_choices():
    data = app_data()
    feats = data["feats"]

    assert len(feats) >= 40
    actor = feat_by_name(feats, "Actor")
    assert actor["category"] == "general"
    assert actor["prerequisites"]["minimum_level"] == 4
    assert actor["prerequisites"]["any"][0]["ability_scores"] == [{"Charisma": 13}]
    assert actor["ability_increase"]["mode"] == "fixed"
    assert actor["ability_increase"]["from"] == ["Charisma"]

    ability_score_improvement = feat_by_name(feats, "Ability Score Improvement")
    assert ability_score_improvement["repeatable"]
    assert ability_score_improvement["ability_increase"]["mode"] == "multi_mode"

    fey_touched = feat_by_name(feats, "Fey-Touched")
    assert fey_touched["required_choices"]
    assert fey_touched["unsupported_choices"]


def test_imported_epic_boons_are_normalized_for_level_nineteen_choices():
    data = app_data()
    feats = data["feats"]
    epic_boons = [feat for feat in feats if feat.get("category") == "epic_boon"]

    assert len(epic_boons) == 12
    boon_of_speed = feat_by_name(feats, "Boon of Speed")
    assert boon_of_speed["prerequisites"]["minimum_level"] == 19
    assert boon_of_speed["ability_increase"]["maximum"] == 30
    assert set(boon_of_speed["ability_increase"]["from"]) == {
        "Strength",
        "Dexterity",
        "Constitution",
        "Intelligence",
        "Wisdom",
        "Charisma",
    }
    boon_of_skill = feat_by_name(feats, "Boon of Skill")
    schema = feat_choice_schema(boon_of_skill, {"expertise": []}, data)
    assert schema == [{
        "id": "expertise",
        "type": "single",
        "label": "Expertise",
        "options": list(data["rules"]["skills"].keys()),
    }]


def test_general_feat_eligibility_checks_level_abilities_spellcasting_and_proficiencies():
    data = app_data()
    feats = data["feats"]
    fighter_data = data["classes_by_name"]["Fighter"]
    wizard_data = data["classes_by_name"]["Wizard"]

    character = level_four_character("Fighter")
    recalculate_character(character, data)

    assert feat_is_eligible(feat_by_name(feats, "Actor"), character, fighter_data)
    character["ability_scores"]["Charisma"] = 12
    assert not feat_is_eligible(feat_by_name(feats, "Actor"), character, fighter_data)

    character = level_four_character("Fighter")
    character["level"] = 3
    recalculate_character(character, data)
    assert not feat_is_eligible(feat_by_name(feats, "Athlete"), character, fighter_data)

    character["level"] = 4
    recalculate_character(character, data)
    assert feat_is_eligible(feat_by_name(feats, "Athlete"), character, fighter_data)
    assert not feat_is_eligible(feat_by_name(feats, "Spell Sniper"), character, fighter_data)

    wizard = level_four_character("Wizard")
    recalculate_character(wizard, data)
    assert feat_is_eligible(feat_by_name(feats, "Spell Sniper"), wizard, wizard_data)

    character = level_four_character("Fighter")
    recalculate_character(character, data)
    assert feat_is_eligible(feat_by_name(feats, "Heavily Armored"), character, fighter_data)


def test_repeatable_feats_remain_available_but_other_taken_feats_are_excluded():
    data = app_data()
    feats = data["feats"]
    character = level_four_character("Fighter")
    character["general_feats"] = ["Actor", "Ability Score Improvement"]
    recalculate_character(character, data)

    available = {feat["name"] for feat in eligible_feats(feats, character, data["classes_by_name"]["Fighter"])}

    assert "Actor" not in available
    assert "Ability Score Improvement" in available


def test_non_repeatable_feat_instances_are_excluded_from_eligibility():
    data = app_data()
    feats = data["feats"]
    character = level_four_character("Fighter")
    character["general_feats"] = [{
        "instance_id": "actor-instance",
        "feat_id": "actor_xphb",
        "name": "Actor",
        "source": {"type": "class_level", "class_name": "Fighter", "level": 4},
        "choices": {},
    }]
    recalculate_character(character, data)

    available = {feat["name"] for feat in eligible_feats(feats, character, data["classes_by_name"]["Fighter"])}

    assert "Actor" not in available


def test_general_feat_names_handles_legacy_names_and_instances():
    character = {
        "general_feats": [
            "Actor",
            {"instance_id": "abc", "feat_id": "athlete_xphb", "name": "Athlete", "choices": {}},
        ]
    }

    assert general_feat_names(character) == ["Actor", "Athlete"]


def test_unsupported_or_partial_general_feats_are_not_selectable():
    data = app_data()
    feats = data["feats"]

    assert feat_is_supported_for_selection(feat_by_name(feats, "Actor"))
    assert feat_is_supported_for_selection(feat_by_name(feats, "Chef"))
    assert feat_is_supported_for_selection(feat_by_name(feats, "Heavily Armored"))
    assert feat_is_supported_for_selection(feat_by_name(feats, "Lightly Armored"))
    assert feat_is_supported_for_selection(feat_by_name(feats, "Martial Weapon Training"))
    assert feat_is_supported_for_selection(feat_by_name(feats, "Moderately Armored"))
    assert feat_is_supported_for_selection(feat_by_name(feats, "Poisoner"))
    assert feat_is_supported_for_selection(feat_by_name(feats, "Keen Mind"))
    assert feat_is_supported_for_selection(feat_by_name(feats, "Observant"))
    assert feat_is_supported_for_selection(feat_by_name(feats, "Resilient"))
    assert feat_is_supported_for_selection(feat_by_name(feats, "Skill Expert"))
    assert feat_is_supported_for_selection(feat_by_name(feats, "Weapon Master"))
    assert feat_is_supported_for_selection(feat_by_name(feats, "Elemental Adept"))
    assert feat_is_supported_for_selection(feat_by_name(feats, "Telekinetic"))
    assert feat_is_supported_for_selection(feat_by_name(feats, "Telepathic"))
    assert feat_is_supported_for_selection(feat_by_name(feats, "Fey-Touched"))
    assert feat_is_supported_for_selection(feat_by_name(feats, "Ritual Caster"))
    assert feat_is_supported_for_selection(feat_by_name(feats, "Shadow-Touched"))
    assert not feat_support_status(feat_by_name(feats, "Skill Expert"))["notes"]
    assert feat_support_status(feat_by_name(feats, "Heavy Armor Master"))["active_play"] == "description_only"
    assert feat_support_status(feat_by_name(feats, "Medium Armor Master"))["sheet_calculation"] == "supported"


def test_feat_granted_proficiencies_are_applied_during_recalculation():
    data = app_data()
    character = level_four_character("Rogue")
    character["general_feats"] = [
        {"instance_id": "lightly", "feat_id": "lightly_armored_xphb", "name": "Lightly Armored", "source": {}, "choices": {}},
        {"instance_id": "martial", "feat_id": "martial_weapon_training_xphb", "name": "Martial Weapon Training", "source": {}, "choices": {}},
        {"instance_id": "chef", "feat_id": "chef_xphb", "name": "Chef", "source": {}, "choices": {}},
        {"instance_id": "poisoner", "feat_id": "poisoner_xphb", "name": "Poisoner", "source": {}, "choices": {}},
    ]

    recalculate_character(character, data)

    assert "Shields" in character["armor_proficiencies"]
    assert "Martial Weapons" in character["weapon_proficiencies"]
    assert "Cook's Utensils" in character["tool_proficiencies"]
    assert "Poisoner's Kit" in character["tool_proficiencies"]


def test_sheet_value_feat_choices_are_applied_during_recalculation():
    data = app_data()
    character = level_four_character("Fighter")
    character["skill_proficiencies"] = ["Athletics"]
    character["general_feats"] = [
        {
            "instance_id": "skill_expert",
            "feat_id": "skill_expert_xphb",
            "name": "Skill Expert",
            "source": {},
            "choices": {"skill_proficiency": "Arcana", "expertise": "Arcana"},
        },
        {
            "instance_id": "telepathic",
            "feat_id": "telepathic_xphb",
            "name": "Telepathic",
            "source": {},
            "choices": {"ability": "Wisdom"},
        },
        {
            "instance_id": "keen_mind",
            "feat_id": "keen_mind_xphb",
            "name": "Keen Mind",
            "source": {},
            "choices": {"ability": "Intelligence", "skill": "Athletics"},
        },
        {
            "instance_id": "observant",
            "feat_id": "observant_xphb",
            "name": "Observant",
            "source": {},
            "choices": {"ability": "Wisdom", "skill": "Perception"},
        },
        {
            "instance_id": "resilient",
            "feat_id": "resilient_xphb",
            "name": "Resilient",
            "source": {},
            "choices": {"ability": "Wisdom"},
        },
        {
            "instance_id": "fey_touched",
            "feat_id": "fey_touched_xphb",
            "name": "Fey-Touched",
            "source": {},
            "choices": {"ability": "Wisdom", "spell": "Detect Magic"},
        },
        {
            "instance_id": "shadow_touched",
            "feat_id": "shadow_touched_xphb",
            "name": "Shadow-Touched",
            "source": {},
            "choices": {"ability": "Charisma", "spell": "Silent Image"},
        },
        {
            "instance_id": "ritual_caster",
            "feat_id": "ritual_caster_xphb",
            "name": "Ritual Caster",
            "source": {},
            "choices": {"ability": "Intelligence", "spells": ["Alarm", "Find Familiar"]},
        },
    ]

    recalculate_character(character, data)

    assert "Arcana" in character["skill_proficiencies"]
    assert "Arcana" in character["expertise"]
    assert "Athletics" in character["expertise"]
    assert "Perception" in character["skill_proficiencies"]
    assert "Wisdom" in character["saving_throw_proficiencies"]
    assert "Detect Thoughts" in character["features"]
    assert "Misty Step" in character["features"]
    assert "Detect Magic" in character["features"]
    assert "Invisibility" in character["features"]
    assert "Silent Image" in character["features"]
    assert "Alarm" in character["features"]
    assert "Find Familiar" in character["features"]


def test_speedy_medium_armor_master_and_ac_restrictions_are_applied():
    data = app_data()
    character = level_four_character("Fighter")
    character["base_ability_scores"]["Dexterity"] = 16
    character["equipment"] = ["Scale Mail"]
    character["general_feats"] = [
        {
            "instance_id": "speedy",
            "feat_id": "speedy_xphb",
            "name": "Speedy",
            "source": {},
            "choices": {"ability": "Dexterity"},
        },
        {
            "instance_id": "medium",
            "feat_id": "medium_armor_master_xphb",
            "name": "Medium Armor Master",
            "source": {},
            "choices": {"ability": "Dexterity"},
        },
    ]

    recalculate_character(character, data)

    assert character["speed"] == 40
    assert character["armor_class"] == 17
    assert character["armor_class_details"]["medium_armor_dexterity_cap"] == 3

    monk = level_four_character("Monk")
    monk["base_ability_scores"]["Dexterity"] = 16
    monk["base_ability_scores"]["Wisdom"] = 16
    monk["equipment"] = ["Shield"]
    recalculate_character(monk, data)

    assert monk["armor_class"] == 16
    assert monk["armor_class_details"]["formula_id"] == "monk_unarmored_defense"
    assert not monk["armor_class_details"]["shield_applied"]


def test_general_feat_details_and_spell_sources_are_sheet_ready():
    data = app_data()
    character = level_four_character("Wizard")
    character["base_ability_scores"]["Wisdom"] = 14
    character["general_feats"] = [
        {
            "instance_id": "elemental_fire",
            "feat_id": "elemental_adept_xphb",
            "name": "Elemental Adept",
            "source": {"type": "class_level", "level": 4},
            "choices": {"ability": "Intelligence", "damage_type": "Fire"},
        },
        {
            "instance_id": "telepathic",
            "feat_id": "telepathic_xphb",
            "name": "Telepathic",
            "source": {"type": "class_level", "level": 4},
            "choices": {"ability": "Wisdom"},
        },
    ]
    recalculate_character(character, data)
    from services.character_sheet import build_character_sheet

    sheet = build_character_sheet(character)
    feat_details = {detail["instance_id"]: detail for detail in sheet["general_feat_details"]}
    detect_thoughts = next(detail for detail in sheet["spell_details"] if detail["name"] == "Detect Thoughts")
    telepathic_source = next(source for source in sheet["spells"]["spellcasting_sources"] if source["source_name"] == "Telepathic")

    assert feat_details["elemental_fire"]["choices"]["damage_type"] == "Fire"
    assert detect_thoughts["sources"] == ["Telepathic"]
    assert telepathic_source["ability"] == "Wisdom"
    assert telepathic_source["spell_save_dc"] == 12


def test_spell_choice_feat_schemas_filter_spell_options():
    data = app_data()
    character = level_four_character("Fighter")
    recalculate_character(character, data)

    fey_schema = feat_choice_schema(feat_by_name(data["feats"], "Fey-Touched"), character, data)
    shadow_schema = feat_choice_schema(feat_by_name(data["feats"], "Shadow-Touched"), character, data)
    ritual_schema = feat_choice_schema(feat_by_name(data["feats"], "Ritual Caster"), character, data)

    assert fey_schema[0]["options"]
    assert "Detect Magic" in fey_schema[0]["options"]
    assert "Charm Person" in fey_schema[0]["options"]
    assert "Disguise Self" not in fey_schema[0]["options"]

    assert shadow_schema[0]["options"]
    assert "Disguise Self" in shadow_schema[0]["options"]
    assert "Silent Image" in shadow_schema[0]["options"]
    assert "Charm Person" not in shadow_schema[0]["options"]

    assert ritual_schema[0]["type"] == "multi"
    assert ritual_schema[0]["choose"] == 2
    assert "Alarm" in ritual_schema[0]["options"]
    assert "Find Familiar" in ritual_schema[0]["options"]


def test_elemental_adept_repeat_choices_exclude_existing_damage_types():
    data = app_data()
    character = level_four_character("Wizard")
    character["general_feats"] = [
        {
            "instance_id": "elemental_adept",
            "feat_id": "elemental_adept_xphb",
            "name": "Elemental Adept",
            "source": {},
            "choices": {"ability": "Intelligence", "damage_type": "Fire"},
        },
    ]
    elemental_adept = feat_by_name(data["feats"], "Elemental Adept")

    schema = feat_choice_schema(elemental_adept, character, data)

    assert "Fire" not in schema[0]["options"]
    assert "Cold" in schema[0]["options"]


def test_asi_selection_validation_and_adjustment_payload():
    character = level_four_character("Fighter")
    character["ability_scores"]["Strength"] = 18
    choice = build_asi_or_feat_choice("fighter", "Fighter", 4)

    assert validate_asi_selection(character, {"ability_increases": {"Strength": 2}})["ok"]
    assert validate_asi_selection(character, {"ability_increases": {"Strength": 1, "Dexterity": 1}})["ok"]
    assert not validate_asi_selection(character, {"ability_increases": {"Strength": 1}})["ok"]
    character["ability_scores"]["Strength"] = 19
    assert not validate_asi_selection(character, {"ability_increases": {"Strength": 2}})["ok"]

    adjustment = ability_adjustment_from_asi(choice, {"ability_increases": {"Dexterity": 1, "Wisdom": 1}})

    assert adjustment["source_type"] == "class_level"
    assert adjustment["source_level"] == 4
    assert adjustment["adjustments"] == {"Dexterity": 1, "Wisdom": 1}


def test_feat_selection_validation_and_ability_adjustment_payloads():
    data = app_data()
    feats = data["feats"]
    character = level_four_character("Fighter")
    recalculate_character(character, data)
    fighter_data = data["classes_by_name"]["Fighter"]
    actor = feat_by_name(feats, "Actor")
    athlete = feat_by_name(feats, "Athlete")
    fey_touched = feat_by_name(feats, "Fey-Touched")
    resilient = feat_by_name(feats, "Resilient")

    assert validate_feat_selection(character, fighter_data, feats, actor["id"])["ok"]
    assert not validate_feat_selection(character, fighter_data, feats, fey_touched["id"])["ok"]
    assert not validate_feat_selection(character, fighter_data, feats, resilient["id"], "Strength")["ok"]
    assert validate_feat_selection(character, fighter_data, feats, resilient["id"], "Wisdom")["ok"]
    assert ability_adjustment_from_feat(actor)["adjustments"] == {"Charisma": 1}
    assert ability_adjustment_from_feat(athlete, "Dexterity")["adjustments"] == {"Dexterity": 1}
    assert ability_adjustment_from_feat(athlete, "Wisdom")["error"]
    assert feat_by_id(feats, actor["id"])["name"] == "Actor"


def test_source_ability_adjustments_are_applied_during_recalculation():
    data = app_data()
    character = level_four_character("Fighter")
    character["base_ability_scores"]["Strength"] = 15
    character["ability_score_adjustments"] = [{
        "type": "ability_score_adjustment",
        "source_type": "class_level",
        "source_class": "Fighter",
        "source_level": 4,
        "adjustments": {"Strength": 2},
        "maximum": 20,
    }]

    recalculate_character(character, data)

    assert character["ability_scores"]["Strength"] == 17
    assert character["ability_score_adjustment_bonuses"]["Strength"] == 2


def test_remaining_combat_feats_have_sheet_values_or_description_support():
    data = app_data()
    character = level_four_character("Fighter")
    character["base_ability_scores"]["Strength"] = 16
    character["general_feats"] = [
        {"instance_id": "gwm", "feat_id": "great_weapon_master_xphb", "name": "Great Weapon Master", "source": {}, "choices": {"ability": "Strength"}},
        {"instance_id": "shield", "feat_id": "shield_master_xphb", "name": "Shield Master", "source": {}, "choices": {"ability": "Strength"}},
        {"instance_id": "skulker", "feat_id": "skulker_xphb", "name": "Skulker", "source": {}, "choices": {"ability": "Dexterity"}},
    ]

    recalculate_character(character, data)
    sheet = build_character_sheet(character)
    resources = sheet["resources"]
    details = {detail["name"]: detail for detail in sheet["feature_details"]}

    assert resources["great_weapon_master_damage_bonus"] == character["proficiency_bonus"]
    assert resources["shield_master_bash_dc"] == 8 + character["proficiency_bonus"] + character["ability_modifiers"]["Strength"]
    assert resources["shield_master_bash_ability"] == "Strength"
    assert resources["blindsight_range"] == 10
    assert resources["blindsight_source"] == "Skulker"
    assert details["Great Weapon Master"]["description"]
    assert details["Shield Master"]["description"]
    assert details["Skulker"]["description"]
