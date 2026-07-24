from models.character import new_character
from presentation.option_catalog import (
    SpellSelectionGroupSpec,
    add_option_to_group_selection,
    build_grouped_spell_option_catalog,
)
from rules.hit_points import calculate_hit_points
from rules.level_up import (
    classify_level_features,
    commit_level_up_draft,
    create_level_up_draft,
    finalize_level_up,
    get_level_up_plan,
    refresh_level_up_draft_choices,
    resolve_pending_choice,
    validate_level_up_plan,
)
from rules.leveling import (
    class_progression_at_level,
    effective_spellcasting,
    get_active_subclass_grants,
    selected_subclass_options,
    subclass_features_up_to_level,
)
from rules.proficiencies import proficiency_bonus_for_level
from tests.test_level_one_builds import app_data, feature_details_by_name, finalized


def level_one_fighter():
    character = new_character()
    character.update({
        "name": "Astra",
        "species": "Human",
        "background": "Soldier",
        "class": "Fighter",
        "weapon_masteries": ["Longsword", "Longbow", "Dagger"],
    })
    character["species_options"] = {
        "skill_proficiencies": ["Perception"],
        "origin_feats": ["Tough"],
    }
    character["background_options"] = {
        "primary_ability": "Strength",
        "secondary_ability": "Constitution",
        "tool_proficiencies": ["Any gaming set"],
    }
    character["class_options"] = {
        "class_skills": ["Acrobatics", "Survival"],
        "fighting_style": "Defense",
    }
    character["base_ability_scores"]["Constitution"] = 14
    return character


def level_three_character(character, subclass, data):
    finalized(character, data)
    finalize_level_up(character, get_level_up_plan(character, 2, data))
    finalized(character, data)
    draft = create_level_up_draft(character, 3, data)
    resolve_pending_choice(draft, draft["pending_choices"][0]["id"], subclass)
    commit_level_up_draft(character, draft)
    return character


def level_three_cleric(subclass):
    character = new_character()
    character.update({
        "name": "Seren",
        "species": "Dwarf",
        "background": "Acolyte",
        "class": "Cleric",
        "subclass": subclass,
        "level": 3,
    })
    character["background_options"] = {
        "primary_ability": "Wisdom",
        "secondary_ability": "Constitution",
    }
    character["class_options"] = {
        "class_skills": ["Insight", "Religion"],
        "divine_order": "Protector",
    }
    character["origin_feat_choices"] = {
        "skills": [],
        "tools": [],
        "cantrips": ["Light", "Mage Hand"],
        "spell": "Shield",
        "spellcasting_ability": "Wisdom",
    }
    character["spells"] = {
        "cantrips": ["Guidance", "Sacred Flame", "Thaumaturgy"],
        "prepared": ["Command", "Detect Magic", "Healing Word", "Hold Person", "Shield of Faith", "Spiritual Weapon"],
        "known": [],
    }
    character["base_ability_scores"]["Wisdom"] = 16
    return character


def level_three_rogue(subclass):
    character = new_character()
    character.update({
        "name": "Shade",
        "species": "Halfling",
        "background": "Criminal",
        "class": "Rogue",
        "subclass": subclass,
        "level": 3,
        "weapon_masteries": ["Dagger", "Shortsword"],
    })
    character["background_options"] = {
        "primary_ability": "Dexterity",
        "secondary_ability": "Intelligence",
    }
    character["class_options"] = {
        "class_skills": ["Acrobatics", "Insight", "Investigation", "Perception"],
        "rogue_thieves_cant_language": "Elvish",
    }
    character["expertise"] = ["Stealth", "Sleight of Hand"]
    character["base_ability_scores"]["Dexterity"] = 16
    return character


def level_three_wizard(subclass):
    character = new_character()
    character.update({
        "name": "Ilyra",
        "species": "Elf",
        "background": "Sage",
        "class": "Wizard",
        "subclass": subclass,
        "level": 3,
    })
    character["species_options"] = {
        "lineage": "High Elf",
        "lineage_spells": ["Prestidigitation"],
        "lineage_spellcasting_ability": "Intelligence",
        "skill_proficiencies": ["Perception"],
    }
    character["background_options"] = {
        "primary_ability": "Intelligence",
        "secondary_ability": "Dexterity",
    }
    character["class_options"] = {
        "class_skills": ["Arcana", "Investigation"],
        "wizard_scholar_skill": "Arcana",
    }
    character["origin_feat_choices"] = {
        "skills": [],
        "tools": [],
        "cantrips": ["Guidance", "Sacred Flame"],
        "spell": "Healing Word",
        "spellcasting_ability": "Intelligence",
    }
    character["spells"] = {
        "cantrips": ["Fire Bolt", "Mage Hand", "Ray of Frost"],
        "spellbook": [
            "Burning Hands",
            "Detect Magic",
            "Feather Fall",
            "Find Familiar",
            "Mage Armor",
            "Magic Missile",
            "Misty Step",
            "Scorching Ray",
            "Shield",
            "Web",
        ],
        "known": [],
        "prepared": [],
    }
    character["base_ability_scores"]["Intelligence"] = 16
    return character


def level_one_wizard():
    character = new_character()
    character.update({
        "name": "Ilyra",
        "species": "Dwarf",
        "background": "Farmer",
        "class": "Wizard",
    })
    character["background_options"] = {
        "primary_ability": "Intelligence",
        "secondary_ability": "Constitution",
    }
    character["class_options"] = {"class_skills": ["Arcana", "Investigation"]}
    character["spells"] = {
        "cantrips": ["Fire Bolt", "Mage Hand", "Ray of Frost"],
        "spellbook": ["Burning Hands", "Detect Magic", "Feather Fall", "Find Familiar", "Mage Armor", "Shield"],
        "known": [],
        "prepared": [],
    }
    character["base_ability_scores"]["Intelligence"] = 16
    return character


def level_one_rogue():
    character = new_character()
    character.update({
        "name": "Shade",
        "species": "Halfling",
        "background": "Criminal",
        "class": "Rogue",
        "weapon_masteries": ["Dagger", "Shortsword"],
    })
    character["background_options"] = {
        "primary_ability": "Dexterity",
        "secondary_ability": "Intelligence",
    }
    character["class_options"] = {
        "class_skills": ["Acrobatics", "Insight", "Investigation", "Perception"],
        "rogue_thieves_cant_language": "Elvish",
    }
    character["expertise"] = ["Stealth", "Sleight of Hand"]
    character["base_ability_scores"]["Dexterity"] = 16
    return character


def resolve_spell_level_up_choices(draft):
    for choice in draft["pending_choices"]:
        if choice.get("type") == "spell_selection":
            resolve_pending_choice(draft, choice["id"], choice["options"][:choice["choose"]])


def test_fixed_hit_points_grow_after_level_one():
    assert calculate_hit_points(10, 2, 1) == 12
    assert calculate_hit_points(10, 2, 2) == 20


def test_proficiency_bonus_progression_uses_standard_tiers():
    assert proficiency_bonus_for_level(1) == 2
    assert proficiency_bonus_for_level(5) == 3
    assert proficiency_bonus_for_level(9) == 4
    assert proficiency_bonus_for_level(13) == 5
    assert proficiency_bonus_for_level(17) == 6


def test_level_two_fighter_adds_hp_and_level_two_features():
    data = app_data()
    character = level_one_fighter()
    character["level"] = 2

    sheet, report = finalized(character, data)

    assert report["complete"]
    assert sheet["identity"]["level"] == 2
    assert sheet["core_stats"]["hit_points"]["max"] == 24
    assert sheet["core_stats"]["proficiency_bonus"] == 2
    assert "Action Surge" in sheet["features"]
    assert "Tactical Mind" in sheet["features"]


def test_level_up_plan_previews_level_two_fighter_changes():
    data = app_data()
    character = level_one_fighter()
    finalized(character, data)

    plan = get_level_up_plan(character, 2, data)

    assert plan["current_level"] == 1
    assert plan["target_level"] == 2
    assert plan["class_name"] == "Fighter"
    assert plan["hp_increase"] == 10
    assert plan["can_finalize"]
    assert plan["pending_choices"] == []
    assert [feature["name"] for feature in plan["automatic_features"]] == [
        "Action Surge",
        "Tactical Mind",
    ]


def test_finalize_level_up_records_transaction_fields():
    data = app_data()
    character = level_one_fighter()
    finalized(character, data)
    plan = get_level_up_plan(character, 2, data)

    result = finalize_level_up(character, plan)
    sheet, report = finalized(character, data)

    assert result["ok"]
    assert report["complete"]
    assert character["level"] == 2
    assert plan["transaction_id"] in character["completed_level_up_transactions"]
    assert character["class_levels"] == {"Fighter": 2}
    assert character["hit_dice"] == {"Fighter": 2}
    assert character["hp_rolls"][-1] == {
        "class": "Fighter",
        "level": 2,
        "mode": "fixed",
        "value": 10,
    }
    assert character["level_history"][-1]["automatic_features"] == [
        "Action Surge",
        "Tactical Mind",
    ]
    assert sheet["core_stats"]["hit_points"]["max"] == 24


def test_level_three_subclass_choice_must_be_resolved_before_finalizing():
    data = app_data()
    character = level_one_fighter()
    finalized(character, data)
    finalize_level_up(character, get_level_up_plan(character, 2, data))
    finalized(character, data)

    plan = create_level_up_draft(character, 3, data)

    assert plan["target_level"] == 3
    assert not plan["can_finalize"]
    assert plan["status"] == "draft"
    assert [feature["name"] for feature in plan["automatic_features"]] == []
    assert plan["pending_choices"][0]["type"] == "subclass_choice"
    assert plan["pending_choices"][0]["status"] == "unresolved"
    assert "value" not in plan["pending_choices"][0]
    assert "Champion" in plan["pending_choices"][0]["options"]

    result = finalize_level_up(character, plan)

    assert not result["ok"]
    assert result["message"] == "Resolve all required choices before finalizing."
    assert character["level"] == 2
    assert character["subclass"] == ""
    assert character["pending_choices"] == []


def test_level_three_subclass_choice_finalizes_after_resolution():
    data = app_data()
    character = level_one_fighter()
    finalized(character, data)
    finalize_level_up(character, get_level_up_plan(character, 2, data))
    finalized(character, data)

    plan = create_level_up_draft(character, 3, data)
    choice_id = plan["pending_choices"][0]["id"]

    assert not resolve_pending_choice(plan, choice_id, "Purple Knight")
    assert resolve_pending_choice(plan, choice_id, "Champion")

    resolved_plan = plan
    assert resolved_plan["can_finalize"]
    assert character["subclass"] == ""

    result = commit_level_up_draft(character, resolved_plan)
    sheet, report = finalized(character, data)

    assert result["ok"]
    assert report["complete"]
    assert character["level"] == 3
    assert character["class_levels"] == {"Fighter": 3}
    assert character["hit_dice"] == {"Fighter": 3}
    assert character["subclass"] == "Champion"
    assert character["pending_choices"] == []
    assert character["level_history"][-1]["resolved_choices"][0]["value"] == "Champion"
    assert sheet["identity"]["subclass"] == "Champion"
    assert "Champion" in sheet["features"]
    assert "Improved Critical" in sheet["features"]
    assert "Remarkable Athlete" in sheet["features"]
    details = feature_details_by_name(sheet)
    assert "19 or 20" in details["Improved Critical"]["description"]
    assert "{@" not in details["Improved Critical"]["description"]
    assert sheet["core_stats"]["hit_points"]["max"] == 34


def test_same_level_up_plan_cannot_be_finalized_twice():
    data = app_data()
    character = level_one_fighter()
    finalized(character, data)
    plan = get_level_up_plan(character, 2, data)

    first = finalize_level_up(character, plan)
    hp_history_count = len(character["hp_history"])
    level_history_count = len(character["level_history"])
    second = finalize_level_up(character, plan)

    assert first["ok"]
    assert not second["ok"]
    assert second["message"] in {
        "This level-up transaction has already been completed.",
        "This level-up plan is stale. Start a new level-up draft.",
    }
    assert character["level"] == 2
    assert len(character["hp_history"]) == hp_history_count
    assert len(character["level_history"]) == level_history_count
    assert character["completed_level_up_transactions"].count(plan["transaction_id"]) == 1


def test_stale_wrong_class_and_skipped_level_plans_are_rejected():
    data = app_data()
    character = level_one_fighter()
    finalized(character, data)

    stale_plan = get_level_up_plan(character, 2, data)
    character["level"] = 2
    stale_result = finalize_level_up(character, stale_plan)
    assert not stale_result["ok"]
    assert stale_result["message"] == "This level-up plan is stale. Start a new level-up draft."

    character = level_one_fighter()
    finalized(character, data)
    wrong_class_plan = get_level_up_plan(character, 2, data)
    character["class"] = "Wizard"
    wrong_class_result = finalize_level_up(character, wrong_class_plan)
    assert not wrong_class_result["ok"]
    assert wrong_class_result["message"] == "This level-up plan is for a different class."

    character = level_one_fighter()
    finalized(character, data)
    skipped_level_plan = get_level_up_plan(character, 2, data)
    skipped_level_plan["target_level"] = 3
    skipped_level_result = finalize_level_up(character, skipped_level_plan)
    assert not skipped_level_result["ok"]
    assert skipped_level_result["message"] == "Only one level at a time can be finalized."


def test_completed_transaction_id_cannot_be_reused():
    data = app_data()
    character = level_one_fighter()
    finalized(character, data)
    plan = get_level_up_plan(character, 2, data)
    transaction_id = plan["transaction_id"]

    assert finalize_level_up(character, plan)["ok"]

    reused_plan = get_level_up_plan(character, 3, data)
    reused_plan["transaction_id"] = transaction_id
    result = finalize_level_up(character, reused_plan)

    assert not result["ok"]
    assert result["message"] == "This level-up transaction has already been completed."


def test_canceling_level_up_draft_leaves_character_unchanged():
    data = app_data()
    character = level_one_fighter()
    finalized(character, data)
    finalize_level_up(character, get_level_up_plan(character, 2, data))
    finalized(character, data)
    before = {
        "level": character["level"],
        "subclass": character["subclass"],
        "pending_choices": list(character["pending_choices"]),
        "level_history": list(character["level_history"]),
    }

    draft = create_level_up_draft(character, 3, data)
    resolve_pending_choice(draft, draft["pending_choices"][0]["id"], "Champion")
    draft = None

    assert draft is None
    assert character["level"] == before["level"]
    assert character["subclass"] == before["subclass"]
    assert character["pending_choices"] == before["pending_choices"]
    assert character["level_history"] == before["level_history"]


def test_validate_level_up_plan_reports_ready_without_mutation():
    data = app_data()
    character = level_one_fighter()
    finalized(character, data)
    plan = get_level_up_plan(character, 2, data)

    result = validate_level_up_plan(character, plan)

    assert result["ok"]
    assert character["level"] == 1
    assert character["level_history"] == []


def test_level_up_plan_records_character_id_and_source_hash():
    data = app_data()
    character = level_one_fighter()
    finalized(character, data)

    plan = get_level_up_plan(character, 2, data)

    assert plan["character_id"] == character["character_id"]
    assert plan["source_state_hash"]


def test_stale_level_up_plan_cannot_finalize_after_character_change():
    data = app_data()
    character = level_three_character(level_one_fighter(), "Champion", data)
    finalized(character, data)
    draft = create_level_up_draft(character, 4, data)
    asi_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "asi_or_feat")
    mastery_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "weapon_mastery_selection")
    resolve_pending_choice(draft, asi_choice["id"], {"mode": "asi", "ability_increases": {"Strength": 2}})
    resolve_pending_choice(draft, mastery_choice["id"], ["Shortsword"])
    character["base_ability_scores"]["Strength"] = 18

    result = commit_level_up_draft(character, draft, data)

    assert not result["ok"]
    assert "stale" in result["message"]
    assert character["level"] == 3
    assert character["ability_score_adjustments"] == []


def test_level_up_plan_cannot_apply_to_a_different_character():
    data = app_data()
    character = level_one_fighter()
    finalized(character, data)
    other_character = level_one_fighter()
    finalized(other_character, data)
    plan = get_level_up_plan(character, 2, data)

    result = finalize_level_up(other_character, plan, data)

    assert not result["ok"]
    assert "different character" in result["message"]
    assert other_character["level"] == 1


def test_wizard_level_up_spellbook_additions_are_draft_choices():
    data = app_data()
    character = level_one_wizard()
    finalized(character, data)

    draft = create_level_up_draft(character, 2, data)
    spellbook_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "spellbook_spells")
    scholar_choice = next(choice for choice in draft["pending_choices"] if choice.get("class_option_key") == "wizard_scholar_skill")

    assert spellbook_choice["choose"] == 2
    assert not draft["can_finalize"]
    assert "Magic Missile" in spellbook_choice["options"]
    assert "Burning Hands" not in spellbook_choice["options"]

    assert not resolve_pending_choice(draft, spellbook_choice["id"], ["Magic Missile"])
    assert not draft["can_finalize"]
    assert "Magic Missile" not in character["spells"]["spellbook"]

    assert resolve_pending_choice(draft, spellbook_choice["id"], ["Magic Missile", "Sleep"])
    assert resolve_pending_choice(draft, scholar_choice["id"], "Arcana")
    assert draft["can_finalize"]
    assert "Magic Missile" not in character["spells"]["spellbook"]

    result = commit_level_up_draft(character, draft)

    assert result["ok"]
    assert character["level"] == 2
    assert "Magic Missile" in character["spells"]["spellbook"]
    assert "Sleep" in character["spells"]["spellbook"]


def test_wizard_subclass_spells_are_resolved_in_level_up_draft():
    data = app_data()
    character = level_one_wizard()
    finalized(character, data)
    level_two = create_level_up_draft(character, 2, data)
    spellbook_choice = next(choice for choice in level_two["pending_choices"] if choice["type"] == "spellbook_spells")
    scholar_choice = next(choice for choice in level_two["pending_choices"] if choice.get("class_option_key") == "wizard_scholar_skill")
    resolve_pending_choice(level_two, spellbook_choice["id"], ["Magic Missile", "Sleep"])
    resolve_pending_choice(level_two, scholar_choice["id"], "Arcana")
    commit_level_up_draft(character, level_two)
    finalized(character, data)

    draft = create_level_up_draft(character, 3, data)
    subclass_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "subclass_choice")

    assert resolve_pending_choice(draft, subclass_choice["id"], "Diviner")
    refresh_level_up_draft_choices(character, draft, data)
    savant_choice = next(
        choice
        for choice in draft["pending_choices"]
        if choice.get("class_option_key") == "savant_spells"
    )

    assert savant_choice["choose"] == 2
    assert "Detect Magic" not in savant_choice["options"]
    assert "Comprehend Languages" in savant_choice["options"]
    assert not draft["can_finalize"]

    spellbook_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "spellbook_spells")
    assert resolve_pending_choice(draft, spellbook_choice["id"], ["Augury", "Detect Thoughts"])
    selected_savant_spells = savant_choice["options"][:2]
    assert resolve_pending_choice(draft, savant_choice["id"], selected_savant_spells)
    assert draft["can_finalize"]

    result = commit_level_up_draft(character, draft)
    sheet, report = finalized(character, data)

    assert result["ok"]
    assert character["subclass"] == "Diviner"
    assert character["class_options"]["savant_spells"] == selected_savant_spells
    for spell in selected_savant_spells:
        assert spell in sheet["spells"]["spellbook"]
    assert report["complete"]


def test_wizard_savant_partial_selection_survives_level_up_refresh():
    data = app_data()
    character = level_one_wizard()
    finalized(character, data)
    level_two = create_level_up_draft(character, 2, data)
    spellbook_choice = next(choice for choice in level_two["pending_choices"] if choice["type"] == "spellbook_spells")
    scholar_choice = next(choice for choice in level_two["pending_choices"] if choice.get("class_option_key") == "wizard_scholar_skill")
    resolve_pending_choice(level_two, spellbook_choice["id"], ["Magic Missile", "Sleep"])
    resolve_pending_choice(level_two, scholar_choice["id"], "Arcana")
    commit_level_up_draft(character, level_two)
    finalized(character, data)

    draft = create_level_up_draft(character, 3, data)
    subclass_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "subclass_choice")
    assert resolve_pending_choice(draft, subclass_choice["id"], "Diviner")
    refresh_level_up_draft_choices(character, draft, data)
    spellbook_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "spellbook_spells")
    savant_choice = next(choice for choice in draft["pending_choices"] if choice.get("class_option_key") == "savant_spells")
    assert resolve_pending_choice(draft, spellbook_choice["id"], spellbook_choice["options"][:2], spellbook_choice)
    refresh_level_up_draft_choices(character, draft, data)
    savant_choice = next(choice for choice in draft["pending_choices"] if choice.get("class_option_key") == "savant_spells")
    partial_savant = [savant_choice["options"][0]]

    assert not resolve_pending_choice(draft, savant_choice["id"], partial_savant, savant_choice)
    refresh_level_up_draft_choices(character, draft, data)
    refreshed_savant = next(choice for choice in draft["pending_choices"] if choice.get("class_option_key") == "savant_spells")

    assert refreshed_savant["status"] == "unresolved"
    assert refreshed_savant["value"] == partial_savant
    assert refreshed_savant["choose"] == 2


def test_level_four_asi_choice_applies_ability_score_adjustment():
    data = app_data()
    character = level_three_character(level_one_fighter(), "Champion", data)
    finalized(character, data)

    draft = create_level_up_draft(character, 4, data)
    asi_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "asi_or_feat")
    mastery_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "weapon_mastery_selection")

    assert asi_choice["feat_options"]
    assert not draft["can_finalize"]
    assert resolve_pending_choice(
        draft,
        asi_choice["id"],
        {"mode": "asi", "ability_increases": {"Strength": 2}},
    )
    assert resolve_pending_choice(draft, mastery_choice["id"], ["Shortsword"])
    assert draft["can_finalize"]

    result = commit_level_up_draft(character, draft)
    sheet, report = finalized(character, data)

    assert result["ok"]
    assert character["level"] == 4
    assert character["ability_score_adjustments"][-1]["adjustments"] == {"Strength": 2}
    assert character["ability_scores"]["Strength"] == 14
    assert sheet["identity"]["level"] == 4
    assert "Shortsword" in character["weapon_masteries"]
    assert report["complete"]
    assert character["level_history"][-1]["resolved_choices"][0]["value"]["mode"] == "asi"


def test_level_four_general_feat_choice_adds_feat_and_description():
    data = app_data()
    character = level_three_character(level_one_fighter(), "Champion", data)
    character["base_ability_scores"]["Charisma"] = 13
    finalized(character, data)

    draft = create_level_up_draft(character, 4, data)
    asi_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "asi_or_feat")
    mastery_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "weapon_mastery_selection")
    actor = next(feat for feat in asi_choice["feat_options"] if feat["name"] == "Actor")
    feat_names = {feat["name"] for feat in asi_choice["feat_options"]}

    assert "Actor" in feat_names
    assert "Skill Expert" in feat_names
    assert "Weapon Master" in feat_names
    assert "Elemental Adept" not in feat_names

    assert resolve_pending_choice(
        draft,
        asi_choice["id"],
        {
            "mode": "feat",
            "feat_id": actor["id"],
            "feat_name": actor["name"],
            "feat_ability_choice": "",
        },
    )
    assert resolve_pending_choice(draft, mastery_choice["id"], ["Shortsword"])

    result = commit_level_up_draft(character, draft)
    sheet, report = finalized(character, data)
    details = feature_details_by_name(sheet)

    assert result["ok"]
    assert character["level"] == 4
    assert character["general_feats"][-1]["name"] == "Actor"
    assert character["general_feats"][-1]["feat_id"] == actor["id"]
    assert character["general_feats"][-1]["source"]["transaction_id"] == result["transaction_id"]
    assert "Actor" in sheet["features"]
    assert "Actor" in sheet["general_feats"]
    assert details["Actor"]["description"]
    assert character["ability_scores"]["Charisma"] == 14
    assert report["complete"]


def test_level_history_stores_compact_resolved_choices():
    data = app_data()
    character = level_three_character(level_one_fighter(), "Champion", data)
    character["base_ability_scores"]["Charisma"] = 13
    finalized(character, data)

    draft = create_level_up_draft(character, 4, data)
    asi_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "asi_or_feat")
    mastery_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "weapon_mastery_selection")
    actor = next(feat for feat in asi_choice["feat_options"] if feat["name"] == "Actor")
    resolve_pending_choice(
        draft,
        asi_choice["id"],
        {"mode": "feat", "feat_id": actor["id"], "feat_name": actor["name"], "feat_ability_choice": ""},
    )
    resolve_pending_choice(draft, mastery_choice["id"], ["Shortsword"])

    result = commit_level_up_draft(character, draft, data)
    history_choice = character["level_history"][-1]["resolved_choices"][0]

    assert result["ok"]
    assert "options" not in history_choice
    assert "feat_options" not in history_choice
    assert "description" not in str(history_choice)
    assert history_choice == {
        "choice_id": asi_choice["id"],
        "type": "asi_or_feat",
        "name": "Ability Score Improvement or general feat",
        "value": {"mode": "feat", "feat_id": actor["id"], "feat_name": "Actor"},
    }


def test_level_four_supported_feat_grants_proficiency():
    data = app_data()
    character = level_three_character(level_one_fighter(), "Champion", data)
    finalized(character, data)

    draft = create_level_up_draft(character, 4, data)
    asi_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "asi_or_feat")
    mastery_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "weapon_mastery_selection")
    chef = next(feat for feat in asi_choice["feat_options"] if feat["name"] == "Chef")

    assert resolve_pending_choice(
        draft,
        asi_choice["id"],
        {
            "mode": "feat",
            "feat_id": chef["id"],
            "feat_name": chef["name"],
            "feat_ability_choice": "Constitution",
        },
    )
    assert resolve_pending_choice(draft, mastery_choice["id"], ["Shortsword"])

    result = commit_level_up_draft(character, draft, data)
    sheet, report = finalized(character, data)

    assert result["ok"]
    assert report["complete"]
    assert "Chef" in sheet["general_feats"]
    assert "Cook's Utensils" in sheet["proficiencies"]["tools"]
    assert character["ability_scores"]["Constitution"] == 16


def test_level_four_skill_expert_choice_grants_skill_and_expertise():
    data = app_data()
    character = level_three_character(level_one_fighter(), "Champion", data)
    finalized(character, data)

    draft = create_level_up_draft(character, 4, data)
    asi_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "asi_or_feat")
    mastery_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "weapon_mastery_selection")
    skill_expert = next(feat for feat in asi_choice["feat_options"] if feat["name"] == "Skill Expert")

    assert resolve_pending_choice(
        draft,
        asi_choice["id"],
        {
            "mode": "feat",
            "feat_id": skill_expert["id"],
            "feat_name": skill_expert["name"],
            "feat_ability_choice": "Intelligence",
            "feat_choices": {"skill_proficiency": "Arcana", "expertise": "Arcana"},
        },
    )
    assert resolve_pending_choice(draft, mastery_choice["id"], ["Shortsword"])

    result = commit_level_up_draft(character, draft, data)
    sheet, report = finalized(character, data)
    arcana = next(skill for skill in sheet["skills"] if skill["name"] == "Arcana")

    assert result["ok"]
    assert report["complete"]
    assert "Arcana" in character["skill_proficiencies"]
    assert "Arcana" in character["expertise"]
    assert arcana["proficient"]
    assert arcana["expertise"]
    assert character["general_feats"][-1]["choices"]["skill_proficiency"] == "Arcana"


def test_level_four_weapon_master_feat_grants_selected_mastery():
    data = app_data()
    character = level_three_character(level_one_fighter(), "Champion", data)
    finalized(character, data)

    draft = create_level_up_draft(character, 4, data)
    asi_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "asi_or_feat")
    mastery_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "weapon_mastery_selection")
    weapon_master = next(feat for feat in asi_choice["feat_options"] if feat["name"] == "Weapon Master")
    feat_mastery = next(option for option in weapon_master["choice_schema"][0]["options"] if option != "Shortsword")

    assert resolve_pending_choice(
        draft,
        asi_choice["id"],
        {
            "mode": "feat",
            "feat_id": weapon_master["id"],
            "feat_name": weapon_master["name"],
            "feat_ability_choice": "Strength",
            "feat_choices": {"weapon_mastery": feat_mastery},
        },
    )
    assert resolve_pending_choice(draft, mastery_choice["id"], ["Shortsword"])

    result = commit_level_up_draft(character, draft, data)
    sheet, report = finalized(character, data)

    assert result["ok"]
    assert report["complete"]
    assert feat_mastery in character["weapon_masteries"]
    assert "Shortsword" in sheet["weapon_masteries"]
    assert weapon_master["name"] in sheet["general_feats"]


def test_level_four_elemental_adept_stores_damage_type_choice():
    data = app_data()
    character = level_three_cleric("Life Domain")
    finalized(character, data)

    draft = create_level_up_draft(character, 4, data)
    asi_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "asi_or_feat")
    elemental_adept = next(feat for feat in asi_choice["feat_options"] if feat["name"] == "Elemental Adept")
    resolve_spell_level_up_choices(draft)

    assert resolve_pending_choice(
        draft,
        asi_choice["id"],
        {
            "mode": "feat",
            "feat_id": elemental_adept["id"],
            "feat_name": elemental_adept["name"],
            "feat_ability_choice": "Wisdom",
            "feat_choices": {"damage_type": "Fire"},
        },
    )

    result = commit_level_up_draft(character, draft, data)
    sheet, report = finalized(character, data)
    history_value = next(
        choice["value"]
        for choice in character["level_history"][-1]["resolved_choices"]
        if choice["choice_id"] == asi_choice["id"]
    )

    assert result["ok"]
    assert report["complete"]
    assert "Elemental Adept" in sheet["general_feats"]
    assert character["general_feats"][-1]["choices"]["damage_type"] == "Fire"
    assert history_value["feat_choices"] == {"damage_type": "Fire"}


def test_level_four_telepathic_and_telekinetic_grant_sheet_spells():
    data = app_data()
    cases = [
        ("Telepathic", "Wisdom", "Detect Thoughts"),
        ("Telekinetic", "Intelligence", "Mage Hand"),
    ]

    for feat_name, ability, spell in cases:
        character = level_three_character(level_one_fighter(), "Champion", data)
        finalized(character, data)
        draft = create_level_up_draft(character, 4, data)
        asi_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "asi_or_feat")
        mastery_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "weapon_mastery_selection")
        feat = next(option for option in asi_choice["feat_options"] if option["name"] == feat_name)

        assert resolve_pending_choice(
            draft,
            asi_choice["id"],
            {
                "mode": "feat",
                "feat_id": feat["id"],
                "feat_name": feat["name"],
                "feat_ability_choice": ability,
            },
        )
        assert resolve_pending_choice(draft, mastery_choice["id"], ["Shortsword"])

        result = commit_level_up_draft(character, draft, data)
        sheet, report = finalized(character, data)

        assert result["ok"]
        assert report["complete"]
        assert spell in sheet["spells"]["granted"]
        assert any(detail["name"] == spell and detail["description"] for detail in sheet["spell_details"])


def test_level_four_spell_choice_feats_grant_selected_spells():
    data = app_data()
    cases = [
        ("Fey-Touched", "Wisdom", {"spell": "Detect Magic"}, ["Misty Step", "Detect Magic"]),
        ("Shadow-Touched", "Charisma", {"spell": "Silent Image"}, ["Invisibility", "Silent Image"]),
        ("Ritual Caster", "Intelligence", {"spells": ["Alarm", "Find Familiar"]}, ["Alarm", "Find Familiar"]),
    ]

    for feat_name, ability, feat_choices, expected_spells in cases:
        starting_character = level_one_fighter()
        starting_character["base_ability_scores"]["Intelligence"] = 13
        character = level_three_character(starting_character, "Champion", data)
        finalized(character, data)

        draft = create_level_up_draft(character, 4, data)
        asi_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "asi_or_feat")
        mastery_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "weapon_mastery_selection")
        feat = next(option for option in asi_choice["feat_options"] if option["name"] == feat_name)

        assert resolve_pending_choice(
            draft,
            asi_choice["id"],
            {
                "mode": "feat",
                "feat_id": feat["id"],
                "feat_name": feat["name"],
                "feat_ability_choice": ability,
                "feat_choices": feat_choices,
            },
        )
        assert resolve_pending_choice(draft, mastery_choice["id"], ["Shortsword"])

        result = commit_level_up_draft(character, draft, data)
        sheet, report = finalized(character, data)

        assert result["ok"]
        assert report["complete"]
        assert feat_name in sheet["general_feats"]
        for spell in expected_spells:
            assert spell in sheet["spells"]["granted"]
            assert any(detail["name"] == spell and detail["description"] for detail in sheet["spell_details"])


def test_ritual_caster_prompts_for_more_spells_when_proficiency_bonus_increases():
    data = app_data()
    starting_character = level_one_fighter()
    starting_character["base_ability_scores"]["Intelligence"] = 13
    character = level_three_character(starting_character, "Champion", data)
    finalized(character, data)

    level_four = create_level_up_draft(character, 4, data)
    asi_choice = next(choice for choice in level_four["pending_choices"] if choice["type"] == "asi_or_feat")
    mastery_choice = next(choice for choice in level_four["pending_choices"] if choice["type"] == "weapon_mastery_selection")
    ritual_caster = next(option for option in asi_choice["feat_options"] if option["name"] == "Ritual Caster")
    assert resolve_pending_choice(
        level_four,
        asi_choice["id"],
        {
            "mode": "feat",
            "feat_id": ritual_caster["id"],
            "feat_name": ritual_caster["name"],
            "feat_ability_choice": "Intelligence",
            "feat_choices": {"spells": ["Alarm", "Find Familiar"]},
        },
    )
    assert resolve_pending_choice(level_four, mastery_choice["id"], ["Shortsword"])
    assert commit_level_up_draft(character, level_four, data)["ok"]
    finalized(character, data)

    level_five = create_level_up_draft(character, 5, data)
    spell_choice = next(choice for choice in level_five["pending_choices"] if choice["type"] == "feat_spell_selection")

    assert spell_choice["choose"] == 1
    assert "Identify" in spell_choice["options"]
    assert "Alarm" not in spell_choice["options"]
    assert resolve_pending_choice(level_five, spell_choice["id"], ["Identify"])

    result = commit_level_up_draft(character, level_five, data)
    sheet, report = finalized(character, data)
    ritual_feat = next(feat for feat in character["general_feats"] if feat["name"] == "Ritual Caster")

    assert result["ok"]
    assert report["complete"]
    assert character["level"] == 5
    assert ritual_feat["choices"]["spells"] == ["Alarm", "Find Familiar", "Identify"]
    assert "Identify" in sheet["spells"]["granted"]


def test_level_four_spellcaster_choices_are_resolved_in_level_up_draft():
    data = app_data()
    character = level_three_cleric("Life Domain")
    finalized(character, data)

    draft = create_level_up_draft(character, 4, data)
    asi_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "asi_or_feat")
    cantrip_choice = next(
        choice
        for choice in draft["pending_choices"]
        if choice["type"] == "spell_selection" and choice["spell_field"] == "cantrips"
    )
    prepared_choice = next(
        choice
        for choice in draft["pending_choices"]
        if choice["type"] == "spell_selection" and choice["spell_field"] == "prepared"
    )

    assert cantrip_choice["choose"] == 1
    assert prepared_choice["choose"] == 1
    assert "Guidance" not in cantrip_choice["options"]

    assert resolve_pending_choice(draft, asi_choice["id"], {"mode": "asi", "ability_increases": {"Wisdom": 2}})
    assert resolve_pending_choice(draft, cantrip_choice["id"], [cantrip_choice["options"][0]])
    assert resolve_pending_choice(draft, prepared_choice["id"], [prepared_choice["options"][0]])
    assert draft["can_finalize"]

    result = commit_level_up_draft(character, draft)
    sheet, report = finalized(character, data)

    assert result["ok"]
    assert character["level"] == 4
    assert cantrip_choice["value"][0] in sheet["spells"]["cantrips"]
    assert prepared_choice["value"][0] in sheet["spells"]["prepared"]
    assert report["complete"]


def test_level_up_spell_picker_selection_resolves_draft_without_character_mutation():
    data = app_data()
    character = level_three_cleric("Life Domain")
    finalized(character, data)
    original_prepared = list(character["spells"]["prepared"])

    draft = create_level_up_draft(character, 4, data)
    prepared_choice = next(
        choice
        for choice in draft["pending_choices"]
        if choice["type"] == "spell_selection" and choice["spell_field"] == "prepared"
    )
    catalog = build_grouped_spell_option_catalog(
        data["spells"],
        (
            SpellSelectionGroupSpec(
                key="prepared",
                label="Prepared spells",
                option_names=tuple(prepared_choice["options"]),
                selected_names=(),
                selection_limit=prepared_choice["choose"],
                add_label="Add prepared spell",
                remove_label="Remove prepared spell",
            ),
        ),
    )
    selected_option = next(option for option in catalog if option.name == prepared_choice["options"][0])

    result = add_option_to_group_selection([], catalog, selected_option.stable_id, group_key="prepared", selection_limit=prepared_choice["choose"])
    assert resolve_pending_choice(draft, prepared_choice["id"], list(result.selection), prepared_choice)

    assert character["spells"]["prepared"] == original_prepared
    assert prepared_choice["value"] == [selected_option.name]
    assert prepared_choice["status"] == "resolved"


def test_level_up_spell_picker_keeps_cantrip_and_prepared_choices_separate():
    data = app_data()
    character = level_three_cleric("Life Domain")
    finalized(character, data)
    draft = create_level_up_draft(character, 4, data)
    cantrip_choice = next(
        choice
        for choice in draft["pending_choices"]
        if choice["type"] == "spell_selection" and choice["spell_field"] == "cantrips"
    )
    prepared_choice = next(
        choice
        for choice in draft["pending_choices"]
        if choice["type"] == "spell_selection" and choice["spell_field"] == "prepared"
    )
    catalog = build_grouped_spell_option_catalog(
        data["spells"],
        (
            SpellSelectionGroupSpec(
                key="cantrips",
                label="Cantrips",
                option_names=tuple(cantrip_choice["options"]),
                selected_names=(),
                selection_limit=cantrip_choice["choose"],
                add_label="Add cantrip",
                remove_label="Remove cantrip",
            ),
            SpellSelectionGroupSpec(
                key="prepared",
                label="Prepared spells",
                option_names=tuple(prepared_choice["options"]),
                selected_names=(),
                selection_limit=prepared_choice["choose"],
                add_label="Add prepared spell",
                remove_label="Remove prepared spell",
            ),
        ),
    )
    cantrip = next(option for option in catalog if option.name == cantrip_choice["options"][0])
    prepared = next(option for option in catalog if option.name == prepared_choice["options"][0])

    wrong_prepared = add_option_to_group_selection([], catalog, cantrip.stable_id, group_key="prepared", selection_limit=prepared_choice["choose"])
    wrong_cantrip = add_option_to_group_selection([], catalog, prepared.stable_id, group_key="cantrips", selection_limit=cantrip_choice["choose"])
    selected_cantrip = add_option_to_group_selection([], catalog, cantrip.stable_id, group_key="cantrips", selection_limit=cantrip_choice["choose"])
    selected_prepared = add_option_to_group_selection([], catalog, prepared.stable_id, group_key="prepared", selection_limit=prepared_choice["choose"])

    assert wrong_prepared.accepted is False
    assert wrong_cantrip.accepted is False
    assert selected_cantrip.accepted is True
    assert selected_prepared.accepted is True
    assert list(selected_cantrip.selection) == [cantrip.name]
    assert list(selected_prepared.selection) == [prepared.name]


def test_level_seventeen_is_still_blocked_until_progression_is_enabled():
    data = app_data()
    character = level_three_character(level_one_fighter(), "Champion", data)
    finalized(character, data)
    draft = create_level_up_draft(character, 4, data)
    resolve_pending_choice(
        draft,
        next(choice for choice in draft["pending_choices"] if choice["type"] == "asi_or_feat")["id"],
        {"mode": "asi", "ability_increases": {"Strength": 2}},
    )
    resolve_pending_choice(
        draft,
        next(choice for choice in draft["pending_choices"] if choice["type"] == "weapon_mastery_selection")["id"],
        ["Shortsword"],
    )
    commit_level_up_draft(character, draft)
    finalized(character, data)

    character["level"] = 20
    blocked = get_level_up_plan(character, 21, data)

    assert blocked["blocked_reason"] == "Only Levels 1-20 are supported right now."


def test_selected_subclass_features_come_from_imported_subclass_data():
    data = app_data()
    cleric_data = data["classes_by_name"]["Cleric"]

    assert subclass_features_up_to_level(cleric_data, "Life Domain", 3) == [
        "Life Domain",
        "Disciple of Life",
        "Life Domain Spells",
        "Preserve Life",
    ]
    assert subclass_features_up_to_level(cleric_data, "Life", 3) == [
        "Life Domain",
        "Disciple of Life",
        "Life Domain Spells",
        "Preserve Life",
    ]


def test_later_subclass_progression_does_not_prompt_for_subclass_again():
    data = app_data()
    fighter_data = data["classes_by_name"]["Fighter"]
    character = level_three_character(level_one_fighter(), "Champion", data)
    later_subclass_placeholder = next(
        feature
        for feature in class_progression_at_level(fighter_data, 7)
        if feature.get("type") == "subclass_choice"
    )

    normalized = classify_level_features(later_subclass_placeholder, character, fighter_data, "Fighter", 7)

    assert all(feature["type"] == "automatic_feature" for feature in normalized)
    assert all(feature.get("subtype") == "subclass_feature_gain" for feature in normalized)
    assert [feature["name"] for feature in normalized] == ["Additional Fighting Style"]


def test_weapon_mastery_level_up_options_are_limited_to_proficient_weapons():
    data = app_data()
    character = level_three_rogue("Thief")
    character["weapon_masteries"] = ["Dagger"]
    finalized(character, data)

    draft = create_level_up_draft(character, 4, data)
    mastery_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "weapon_mastery_selection")

    assert "Rapier" in mastery_choice["options"]
    assert "Longsword" not in mastery_choice["options"]
    assert "Greataxe" not in mastery_choice["options"]


def test_battle_master_level_three_options_and_resources_are_automated():
    data = app_data()
    character = level_three_character(level_one_fighter(), "Battle Master", data)

    sheet, report = finalized(character, data)
    assert not report["complete"]
    assert "Choose 3 Battle Master maneuvers" in report["missing"]
    assert "Choose Student of War skill" in report["missing"]
    assert "Choose Student of War artisan tool" in report["missing"]

    character["class_options"].update({
        "maneuvers": ["Ambush", "Parry", "Trip Attack"],
        "battle_master_save_ability": "Strength",
        "student_of_war_skill": "Athletics",
        "student_of_war_tool": "Smith's Tools",
    })
    sheet, report = finalized(character, data)

    assert report["complete"]
    assert "Athletics" in character["skill_proficiencies"]
    assert "Smith's Tools" in sheet["proficiencies"]["tools"]
    assert sheet["resources"]["maneuvers_known"] == 3
    assert sheet["resources"]["superiority_dice"] == 4
    assert sheet["resources"]["superiority_die"] == "d8"
    assert sheet["resources"]["maneuver_save_ability"] == "Strength"
    assert sheet["resources"]["maneuver_save_dc"] == 11
    assert "Maneuver: Ambush" in sheet["features"]
    assert "Maneuver: Parry" in sheet["features"]
    assert "Maneuver: Trip Attack" in sheet["features"]


def test_eldritch_knight_level_three_requires_spell_choices_in_draft():
    data = app_data()
    character = level_one_fighter()
    finalized(character, data)
    assert commit_level_up_draft(character, get_level_up_plan(character, 2, data), data)["ok"]
    finalized(character, data)

    draft = create_level_up_draft(character, 3, data)
    subclass_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "subclass_choice")
    assert resolve_pending_choice(draft, subclass_choice["id"], "Eldritch Knight")

    result = commit_level_up_draft(character, draft, data)
    assert not result["ok"]
    assert character["level"] == 2
    assert any(choice["type"] == "spell_selection" for choice in draft["pending_choices"])

    cantrip_choice = next(choice for choice in draft["pending_choices"] if choice.get("spell_field") == "cantrips")
    prepared_choice = next(choice for choice in draft["pending_choices"] if choice.get("spell_field") == "prepared")
    assert cantrip_choice["choose"] == 2
    assert prepared_choice["choose"] == 3
    assert resolve_pending_choice(draft, cantrip_choice["id"], cantrip_choice["options"][:2])
    assert resolve_pending_choice(draft, prepared_choice["id"], prepared_choice["options"][:3])

    result = commit_level_up_draft(character, draft, data)
    sheet, report = finalized(character, data)

    assert result["ok"]
    assert report["complete"]
    assert character["level"] == 3
    assert sheet["spells"]["spellcasting_ability"] == "Intelligence"
    assert sheet["resources"]["spell_slots"] == {"1": 2}


def test_arcane_trickster_level_three_requires_spell_choices_in_draft():
    data = app_data()
    character = level_one_rogue()
    finalized(character, data)
    assert commit_level_up_draft(character, get_level_up_plan(character, 2, data), data)["ok"]
    finalized(character, data)

    draft = create_level_up_draft(character, 3, data)
    subclass_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "subclass_choice")
    assert resolve_pending_choice(draft, subclass_choice["id"], "Arcane Trickster")

    result = commit_level_up_draft(character, draft, data)
    assert not result["ok"]
    assert character["level"] == 2

    cantrip_choice = next(choice for choice in draft["pending_choices"] if choice.get("spell_field") == "cantrips")
    prepared_choice = next(choice for choice in draft["pending_choices"] if choice.get("spell_field") == "prepared")
    assert cantrip_choice["choose"] == 2
    assert "Mage Hand" not in cantrip_choice["options"]
    assert prepared_choice["choose"] == 3
    assert resolve_pending_choice(draft, cantrip_choice["id"], cantrip_choice["options"][:2])
    assert resolve_pending_choice(draft, prepared_choice["id"], prepared_choice["options"][:3])

    result = commit_level_up_draft(character, draft, data)
    sheet, report = finalized(character, data)

    assert result["ok"]
    assert report["complete"]
    assert "Mage Hand" in sheet["spells"]["granted"]
    assert sheet["resources"]["spell_slots"] == {"1": 2}


def test_eldritch_knight_spellcasting_uses_level_three_subclass_rules():
    data = app_data()
    fighter_data = data["classes_by_name"]["Fighter"]

    spellcasting = effective_spellcasting(fighter_data, "Eldritch Knight")
    assert spellcasting["ability"] == "Intelligence"
    assert spellcasting["spell_list"] == "Wizard"
    assert spellcasting["cantrips_known"] == 2
    assert spellcasting["prepared_spells"] == 3
    assert spellcasting["spell_slots"] == {"1": 2}

    character = level_three_character(level_one_fighter(), "Eldritch Knight", data)
    character["spells"] = {
        "cantrips": ["Ray of Frost", "Shocking Grasp"],
        "prepared": ["Burning Hands", "Jump", "Shield"],
        "known": [],
    }
    sheet, report = finalized(character, data)

    assert report["complete"]
    assert sheet["spells"]["spellcasting_ability"] == "Intelligence"
    assert sheet["resources"]["spell_slots"] == {"1": 2}
    assert sheet["resources"]["spell_save_dc"] == 10
    assert sheet["resources"]["spell_attack_bonus"] == 2


def test_arcane_trickster_gets_mage_hand_and_wizard_spellcasting():
    data = app_data()
    rogue_data = data["classes_by_name"]["Rogue"]

    assert selected_subclass_options(rogue_data, "Arcane Trickster") == {}
    assert effective_spellcasting(rogue_data, "Arcane Trickster")["granted_cantrips"] == ["Mage Hand"]

    character = new_character()
    character.update({
        "name": "Shade",
        "species": "Halfling",
        "background": "Criminal",
        "class": "Rogue",
        "subclass": "Arcane Trickster",
        "level": 3,
        "weapon_masteries": ["Dagger", "Shortsword"],
    })
    character["background_options"] = {
        "primary_ability": "Dexterity",
        "secondary_ability": "Intelligence",
    }
    character["class_options"] = {
        "class_skills": ["Acrobatics", "Insight", "Investigation", "Perception"],
        "rogue_thieves_cant_language": "Elvish",
    }
    character["expertise"] = ["Stealth", "Sleight of Hand"]
    character["spells"] = {
        "cantrips": ["Mind Sliver", "Minor Illusion"],
        "prepared": ["Charm Person", "Disguise Self", "Fog Cloud"],
        "known": [],
    }

    sheet, report = finalized(character, data)

    assert report["complete"]
    assert "Mage Hand" in sheet["spells"]["granted"]
    assert sheet["spells"]["spellcasting_ability"] == "Intelligence"
    assert sheet["resources"]["spell_slots"] == {"1": 2}


def test_cleric_domain_spells_and_resources_are_applied():
    data = app_data()
    character = level_three_cleric("Life Domain")

    sheet, report = finalized(character, data)

    assert report["complete"]
    assert sheet["spells"]["spellcasting_ability"] == "Wisdom"
    assert sheet["resources"]["preserve_life_pool"] == 15
    for spell in ["Aid", "Bless", "Cure Wounds", "Lesser Restoration"]:
        assert spell in sheet["spells"]["granted"]


def test_later_subclass_spell_grants_are_combined_by_level():
    data = app_data()

    cleric = level_three_cleric("Life Domain")
    cleric["level"] = 7
    cleric["spells"]["cantrips"] = ["Guidance", "Sacred Flame", "Thaumaturgy", "Light"]
    cleric["spells"]["prepared"] = [
        "Command",
        "Detect Magic",
        "Healing Word",
        "Hold Person",
        "Shield of Faith",
        "Spiritual Weapon",
        "Dispel Magic",
        "Divination",
        "Freedom of Movement",
        "Guardian of Faith",
        "Banishment",
    ]
    cleric["class_options"]["blessed_strikes"] = "Divine Strike"
    cleric_sheet, cleric_report = finalized(cleric, data)

    assert cleric_report["complete"]
    for spell in ["Mass Healing Word", "Revivify", "Aura of Life", "Death Ward"]:
        assert spell in cleric_sheet["spells"]["granted"]
    death_ward = next(detail for detail in cleric_sheet["spells"]["grant_details"] if detail["name"] == "Death Ward")
    assert death_ward["source"]["subclass_name"] == "Life Domain"
    assert death_ward["spellcasting_ability"] == "Wisdom"
    assert death_ward["counts_against_limit"] is False

    devotion = next(subclass for subclass in data["classes_by_name"]["Paladin"]["subclasses"] if subclass["short_name"] == "Devotion")
    fiend = next(subclass for subclass in data["classes_by_name"]["Warlock"]["subclasses"] if subclass["short_name"] == "Fiend")
    moon = next(subclass for subclass in data["classes_by_name"]["Druid"]["subclasses"] if subclass["short_name"] == "Moon")

    assert "Zone of Truth" in get_active_subclass_grants(devotion, 7)["always_prepared_spells"]
    assert "Fireball" in get_active_subclass_grants(fiend, 7)["always_prepared_spells"]
    assert "Fount of Moonlight" in get_active_subclass_grants(moon, 7)["always_prepared_spells"]


def test_psionic_subclasses_get_level_three_energy_dice():
    data = app_data()

    fighter = level_three_character(level_one_fighter(), "Psi Warrior", data)
    fighter_sheet, fighter_report = finalized(fighter, data)
    assert fighter_report["complete"]
    assert fighter_sheet["resources"]["psionic_energy_dice"] == 4
    assert fighter_sheet["resources"]["psionic_energy_die"] == "d6"

    rogue = level_three_rogue("Soulknife")
    rogue_sheet, rogue_report = finalized(rogue, data)
    assert rogue_report["complete"]
    assert rogue_sheet["resources"]["psionic_energy_dice"] == 4
    assert rogue_sheet["resources"]["psionic_energy_die"] == "d6"


def test_assassin_and_thief_level_three_mechanics_are_reflected():
    data = app_data()

    assassin = level_three_rogue("Assassin")
    assassin_sheet, assassin_report = finalized(assassin, data)
    assert assassin_report["complete"]
    assert "Disguise Kit" in assassin_sheet["proficiencies"]["tools"]
    assert "Poisoner's Kit" in assassin_sheet["proficiencies"]["tools"]
    assert assassin_sheet["resources"]["initiative_advantage"] is True
    assert assassin_sheet["resources"]["assassinate_extra_damage"] == 3

    thief = level_three_rogue("Thief")
    thief_sheet, thief_report = finalized(thief, data)
    assert thief_report["complete"]
    assert thief_sheet["resources"]["climb_speed"] == thief_sheet["identity"]["speed"]
    assert thief_sheet["resources"]["jump_ability"] == "Dexterity"


def test_wizard_savant_spell_choices_are_required_and_added_to_sheet():
    data = app_data()
    wizard_data = data["classes_by_name"]["Wizard"]

    savant_options = selected_subclass_options(wizard_data, "Illusionist")["savant_spells"]
    assert savant_options["choose"] == 2
    assert savant_options["from"] == {
        "levels": [1, 2],
        "class": "Wizard",
        "school": "I",
    }

    character = level_three_wizard("Illusionist")
    sheet, report = finalized(character, data)
    assert not report["complete"]
    assert "Choose 2 subclass spells" in report["missing"]

    character["class_options"]["savant_spells"] = ["Color Spray", "Invisibility"]
    sheet, report = finalized(character, data)
    assert report["complete"]
    assert "Minor Illusion" in sheet["spells"]["granted"]
    assert "Color Spray" in sheet["spells"]["spellbook"]
    assert "Invisibility" in sheet["spells"]["spellbook"]
