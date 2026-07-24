from models.character import new_character
from rules.level_up import commit_level_up_draft, create_level_up_draft, resolve_pending_choice
from tests.test_level_one_builds import app_data, finalized


def resolve_basic_level_up_choices(draft, asi_ability="Constitution", preferred_spells=None):
    preferred_spells = preferred_spells or {}
    for choice in list(draft.get("pending_choices", [])):
        choice_id = choice["id"]
        choice_type = choice["type"]
        if choice.get("status") == "resolved":
            continue
        if choice_type == "asi_or_feat":
            assert resolve_pending_choice(
                draft,
                choice_id,
                {"mode": "asi", "ability_increases": {asi_ability: 2}},
            )
        elif choice_type in {"spell_selection", "spellbook_spells", "weapon_mastery_selection", "feat_spell_selection"}:
            preferred = preferred_spells.get(choice.get("spell_field", ""))
            value = preferred if preferred else choice["options"][:choice["choose"]]
            assert resolve_pending_choice(draft, choice_id, value)
        elif choice_type == "class_option_selection":
            preferred = preferred_spells.get(choice.get("class_option_key", ""))
            value = preferred if preferred else choice["options"][:choice["choose"]]
            assert resolve_pending_choice(draft, choice_id, value)
        elif choice_type == "class_option_single":
            assert resolve_pending_choice(draft, choice_id, choice["options"][0])


def human_options(primary="Constitution", secondary="Dexterity"):
    return {
        "species_options": {
            "skill_proficiencies": ["Perception"],
            "origin_feats": ["Tough"],
        },
        "background_options": {
            "primary_ability": primary,
            "secondary_ability": secondary,
        },
    }


def level_eight_champion_fighter():
    character = new_character()
    character.update({
        "name": "Astra",
        "species": "Human",
        "background": "Soldier",
        "class": "Fighter",
        "subclass": "Champion",
        "level": 8,
        "weapon_masteries": ["Longsword", "Longbow", "Dagger", "Shortsword"],
    })
    character.update(human_options("Strength", "Constitution"))
    character["class_options"] = {
        "class_skills": ["Acrobatics", "Survival"],
        "fighting_style": "Defense",
        "champion_additional_fighting_styles": ["Dueling"],
    }
    character["base_ability_scores"]["Strength"] = 16
    character["base_ability_scores"]["Constitution"] = 14
    return character


def test_fighter_can_level_from_eight_to_twelve():
    data = app_data()
    character = level_eight_champion_fighter()

    for target_level in range(9, 13):
        finalized(character, data)
        draft = create_level_up_draft(character, target_level, data)
        resolve_basic_level_up_choices(draft, asi_ability="Strength")
        result = commit_level_up_draft(character, draft, data)
        assert result["ok"], result

    sheet, report = finalized(character, data)

    assert report["complete"]
    assert character["level"] == 12
    assert "Heroic Warrior" in sheet["features"]
    assert "Two Extra Attacks" in sheet["features"]
    assert len(sheet["weapon_masteries"]) == 5
    assert sheet["resources"]["second_wind"] == 4


def level_eight_lore_bard():
    character = new_character()
    character.update({
        "name": "Lyra",
        "species": "Human",
        "background": "Soldier",
        "class": "Bard",
        "subclass": "College of Lore",
        "level": 8,
    })
    character.update(human_options("Charisma", "Dexterity"))
    character["class_options"] = {
        "class_skills": ["Performance", "Persuasion", "Deception"],
        "bard_expertise": ["Performance", "Persuasion"],
        "lore_skills": ["Arcana", "History", "Insight"],
        "magical_discoveries": ["Fireball", "Revivify"],
    }
    character["expertise"] = ["Performance", "Persuasion"]
    character["base_ability_scores"]["Charisma"] = 16
    character["spells"] = {
        "cantrips": ["Blade Ward", "Dancing Lights", "Mage Hand"],
        "prepared": [
            "Animal Friendship",
            "Bane",
            "Charm Person",
            "Color Spray",
            "Command",
            "Comprehend Languages",
            "Cure Wounds",
            "Detect Magic",
            "Disguise Self",
            "Dissonant Whispers",
            "Faerie Fire",
            "Feather Fall",
        ],
        "known": [],
    }
    return character


def test_bard_level_nine_and_ten_choices_are_available_during_level_up():
    data = app_data()
    character = level_eight_lore_bard()

    finalized(character, data)
    level_nine = create_level_up_draft(character, 9, data)
    assert any(choice.get("class_option_key") == "bard_level_9_expertise" for choice in level_nine["pending_choices"])
    resolve_basic_level_up_choices(level_nine)
    assert commit_level_up_draft(character, level_nine, data)["ok"]

    finalized(character, data)
    level_ten = create_level_up_draft(character, 10, data)
    prepared_choice = next(choice for choice in level_ten["pending_choices"] if choice.get("spell_field") == "prepared")
    selected = ["Cone of Cold"]

    assert "Cone of Cold" in prepared_choice["options"]
    assert "Mass Cure Wounds" in prepared_choice["options"]
    assert not any(choice.get("class_option_key") == "magical_secrets" for choice in level_ten["pending_choices"])
    resolve_basic_level_up_choices(level_ten, preferred_spells={"prepared": selected})
    assert commit_level_up_draft(character, level_ten, data)["ok"]
    sheet, report = finalized(character, data)

    assert report["complete"]
    assert character["level"] == 10
    assert set(selected).issubset(set(sheet["spells"]["prepared"]))
    assert "Cone of Cold" not in sheet["spells"]["granted"]
    assert len(character["class_options"]["bard_level_9_expertise"]) == 2


def level_ten_fiend_warlock():
    character = new_character()
    character.update({
        "name": "Morrow",
        "species": "Human",
        "background": "Soldier",
        "class": "Warlock",
        "subclass": "Fiend Patron",
        "level": 10,
    })
    character.update(human_options("Charisma", "Dexterity"))
    character["class_options"] = {
        "class_skills": ["Arcana", "Investigation"],
        "eldritch_invocations": [
            "Agonizing Blast",
            "Armor of Shadows",
            "Devil's Sight",
            "Eldritch Mind",
            "Fiendish Vigor",
            "Mask of Many Faces",
            "One with Shadows",
        ],
    }
    character["base_ability_scores"]["Charisma"] = 16
    character["spells"] = {
        "cantrips": ["Blade Ward", "Chill Touch", "Eldritch Blast", "Mage Hand"],
        "prepared": [
            "Armor of Agathys",
            "Arms of Hadar",
            "Bane",
            "Charm Person",
            "Comprehend Languages",
            "Detect Magic",
            "Expeditious Retreat",
            "Hellish Rebuke",
            "Hex",
            "Illusory Script",
        ],
        "known": [],
    }
    return character


def test_warlock_level_eleven_mystic_arcanum_is_available_during_level_up():
    data = app_data()
    character = level_ten_fiend_warlock()

    finalized(character, data)
    draft = create_level_up_draft(character, 11, data)
    arcanum = next(choice for choice in draft["pending_choices"] if choice.get("class_option_key") == "mystic_arcanum_6")

    assert "Arcane Gate" in arcanum["options"]
    resolve_basic_level_up_choices(draft, preferred_spells={"mystic_arcanum_6": ["Arcane Gate"]})
    assert commit_level_up_draft(character, draft, data)["ok"]
    sheet, report = finalized(character, data)

    assert report["complete"]
    assert character["level"] == 11
    assert "Arcane Gate" in sheet["spells"]["granted"]
    assert character["mystic_arcanum"][0]["spell_level"] == 6
    assert character["mystic_arcanum"][0]["source_level"] == 11
    assert any(detail["name"] == "Arcane Gate" and "Mystic Arcanum" in detail["sources"] for detail in sheet["spell_details"])
