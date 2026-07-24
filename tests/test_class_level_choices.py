from models.character import new_character
from rules.class_choice_rules import fighting_style_options, wild_shape_form_options
from rules.invocations import eligible_invocation_names
from rules.level_up import commit_level_up_draft, create_level_up_draft, finalize_level_up, resolve_pending_choice
from tests.test_level_one_builds import app_data, finalized


def base_character(class_name, background="Sage"):
    character = new_character()
    character.update({
        "name": "Test",
        "species": "Human",
        "background": background,
        "class": class_name,
    })
    character["species_options"] = {
        "skill_proficiencies": ["Perception"],
        "origin_feats": ["Tough"],
    }
    character["background_options"] = {
        "primary_ability": "Wisdom",
        "secondary_ability": "Dexterity",
    }
    character["origin_feat_choices"] = {
        "skills": [],
        "tools": [],
        "cantrips": ["Guidance", "Sacred Flame"],
        "spell": "Healing Word",
        "spellcasting_ability": "Wisdom",
    }
    return character


def resolve_first_option(draft, choice):
    value = choice["options"][0]
    if choice["type"] in {"class_option_selection", "spell_selection", "spellbook_spells", "weapon_mastery_selection"}:
        value = choice["options"][:choice["choose"]]
    assert resolve_pending_choice(draft, choice["id"], value)
    return value


def choice_named(draft, text):
    return next(choice for choice in draft["pending_choices"] if text in choice["name"])


def level_one_bard():
    character = base_character("Bard")
    character["class_options"] = {"class_skills": ["Arcana", "Performance", "Persuasion"]}
    character["spells"] = {
        "cantrips": ["Mage Hand", "Vicious Mockery"],
        "prepared": ["Cure Wounds", "Dissonant Whispers", "Faerie Fire", "Thunderwave"],
        "known": [],
    }
    return character


def level_one_ranger():
    character = base_character("Ranger", "Guide")
    character["class_options"] = {"class_skills": ["Animal Handling", "Nature", "Survival"]}
    character["weapon_masteries"] = ["Longbow", "Shortsword"]
    character["spells"] = {
        "cantrips": [],
        "prepared": ["Cure Wounds", "Hunter's Mark"],
        "known": [],
    }
    return character


def level_one_sorcerer():
    character = base_character("Sorcerer")
    character["class_options"] = {"class_skills": ["Arcana", "Persuasion"]}
    character["spells"] = {
        "cantrips": ["Fire Bolt", "Light", "Mage Hand", "Prestidigitation"],
        "prepared": ["Burning Hands", "Shield"],
        "known": [],
    }
    return character


def level_one_wizard():
    character = base_character("Wizard")
    character["class_options"] = {"class_skills": ["Arcana", "Investigation"]}
    character["spells"] = {
        "cantrips": ["Fire Bolt", "Mage Hand", "Ray of Frost"],
        "spellbook": ["Burning Hands", "Detect Magic", "Feather Fall", "Find Familiar", "Mage Armor", "Shield"],
        "known": [],
        "prepared": [],
    }
    return character


def level_one_warlock():
    character = base_character("Warlock", "Charlatan")
    character["background_options"] = {
        "primary_ability": "Charisma",
        "secondary_ability": "Dexterity",
    }
    character["class_options"] = {
        "class_skills": ["Arcana", "Investigation"],
        "eldritch_invocations": ["Eldritch Mind"],
    }
    character["origin_feat_choices"] = {
        "skills": ["Deception", "Performance", "Persuasion"],
        "tools": [],
        "cantrips": [],
        "spell": "",
        "spellcasting_ability": "",
    }
    character["spells"] = {
        "cantrips": ["Eldritch Blast", "Mage Hand"],
        "prepared": ["Armor of Agathys", "Hex"],
        "known": [],
    }
    return character


def level_one_druid():
    character = base_character("Druid", "Guide")
    character["class_options"] = {
        "class_skills": ["Animal Handling", "Nature"],
        "primal_order": "Warden",
    }
    character["spells"] = {
        "cantrips": ["Guidance", "Produce Flame"],
        "prepared": ["Cure Wounds", "Entangle", "Faerie Fire", "Thunderwave"],
        "known": [],
    }
    return character


def level_one_barbarian():
    character = base_character("Barbarian", "Soldier")
    character["class_options"] = {"class_skills": ["Athletics", "Survival"]}
    character["weapon_masteries"] = ["Greataxe", "Handaxe"]
    return character


def test_bard_level_two_expertise_is_resolved_in_level_up_flow():
    data = app_data()
    character = level_one_bard()
    finalized(character, data)

    draft = create_level_up_draft(character, 2, data)
    spell_choice = choice_named(draft, "prepared spell")
    expertise_choice = choice_named(draft, "Bard Expertise")

    assert expertise_choice["choose"] == 2
    assert not resolve_pending_choice(draft, expertise_choice["id"], [expertise_choice["options"][0], expertise_choice["options"][0]])
    selected_expertise = expertise_choice["options"][:2]
    assert resolve_pending_choice(draft, spell_choice["id"], spell_choice["options"][:1])
    assert resolve_pending_choice(draft, expertise_choice["id"], selected_expertise)

    result = commit_level_up_draft(character, draft)
    sheet, report = finalized(character, data)

    assert result["ok"]
    assert report["complete"]
    assert character["class_options"]["bard_expertise"] == selected_expertise
    assert set(selected_expertise).issubset(character["expertise"])
    assert any(skill["expertise"] for skill in sheet["skills"] if skill["name"] in selected_expertise)


def test_ranger_level_two_deft_explorer_and_fighting_style_are_resolved():
    data = app_data()
    character = level_one_ranger()
    finalized(character, data)

    draft = create_level_up_draft(character, 2, data)
    resolve_first_option(draft, choice_named(draft, "prepared spell"))
    expertise = resolve_first_option(draft, choice_named(draft, "Deft Explorer Expertise"))
    languages = resolve_first_option(draft, choice_named(draft, "Deft Explorer languages"))
    fighting_style = resolve_first_option(draft, choice_named(draft, "Ranger Fighting Style"))

    result = commit_level_up_draft(character, draft)
    sheet, report = finalized(character, data)

    assert result["ok"]
    assert report["complete"]
    assert expertise[0] in character["expertise"]
    assert set(languages).issubset(sheet["proficiencies"]["languages"])
    assert fighting_style == character["class_options"]["fighting_style"]


def test_druidic_warrior_follow_up_cantrips_are_resolved_in_level_up_flow():
    data = app_data()
    character = level_one_ranger()
    finalized(character, data)

    draft = create_level_up_draft(character, 2, data)
    resolve_first_option(draft, choice_named(draft, "prepared spell"))
    resolve_first_option(draft, choice_named(draft, "Deft Explorer Expertise"))
    resolve_first_option(draft, choice_named(draft, "Deft Explorer languages"))
    style_choice = choice_named(draft, "Ranger Fighting Style")
    assert resolve_pending_choice(draft, style_choice["id"], "Druidic Warrior")

    result = commit_level_up_draft(character, draft, data)

    assert not result["ok"]
    cantrip_choice = choice_named(draft, "Druidic Warrior cantrips")
    selected_cantrips = cantrip_choice["options"][:2]
    assert resolve_pending_choice(draft, cantrip_choice["id"], selected_cantrips)
    result = commit_level_up_draft(character, draft, data)
    sheet, report = finalized(character, data)

    assert result["ok"]
    assert report["complete"]
    assert character["class_options"]["druidic_warrior_cantrips"] == selected_cantrips
    assert set(selected_cantrips).issubset(sheet["spells"]["granted"])


def test_sorcerer_level_two_metamagic_is_required_and_stored():
    data = app_data()
    character = level_one_sorcerer()
    finalized(character, data)

    draft = create_level_up_draft(character, 2, data)
    resolve_first_option(draft, choice_named(draft, "prepared spells"))
    metamagic = resolve_first_option(draft, choice_named(draft, "Metamagic"))

    result = commit_level_up_draft(character, draft)
    _, report = finalized(character, data)

    assert result["ok"]
    assert report["complete"]
    assert character["class_options"]["metamagic"] == metamagic


def test_wizard_level_two_scholar_expertise_is_resolved_with_spellbook_spells():
    data = app_data()
    character = level_one_wizard()
    finalized(character, data)

    draft = create_level_up_draft(character, 2, data)
    spellbook_spells = resolve_first_option(draft, choice_named(draft, "spellbook"))
    scholar_skill = resolve_first_option(draft, choice_named(draft, "Scholar"))

    result = commit_level_up_draft(character, draft)
    _, report = finalized(character, data)

    assert result["ok"]
    assert report["complete"]
    assert set(spellbook_spells).issubset(character["spells"]["spellbook"])
    assert scholar_skill in character["expertise"]


def test_warlock_level_two_uses_progression_invocation_count():
    data = app_data()
    character = level_one_warlock()
    finalized(character, data)

    draft = create_level_up_draft(character, 2, data)
    resolve_first_option(draft, choice_named(draft, "prepared spell"))
    invocation_choice = choice_named(draft, "Invocations")
    invocations = resolve_first_option(draft, invocation_choice)

    result = commit_level_up_draft(character, draft)
    sheet, report = finalized(character, data)

    assert invocation_choice["choose"] == 2
    assert result["ok"]
    assert report["complete"]
    assert len(character["class_options"]["eldritch_invocations"]) == 3
    assert set(invocations).issubset(sheet["features"])


def test_druid_level_two_wild_shape_forms_are_required():
    data = app_data()
    character = level_one_druid()
    finalized(character, data)

    draft = create_level_up_draft(character, 2, data)
    resolve_first_option(draft, choice_named(draft, "prepared spell"))
    forms = resolve_first_option(draft, choice_named(draft, "Wild Shape forms"))

    result = commit_level_up_draft(character, draft)
    _, report = finalized(character, data)

    assert result["ok"]
    assert report["complete"]
    assert character["class_options"]["wild_shape_forms"] == forms


def test_wild_shape_forms_scale_at_level_four_and_eight():
    data = app_data()
    character = level_one_druid()
    finalized(character, data)

    level_two_forms = wild_shape_form_options(character, 2)
    level_four_forms = wild_shape_form_options(character, 4)
    level_eight_forms = wild_shape_form_options(character, 8)

    assert "Wolf" in level_two_forms
    assert "Black Bear" not in level_two_forms
    assert "Black Bear" in level_four_forms
    assert "Brown Bear" not in level_four_forms
    assert "Brown Bear" in level_eight_forms
    assert "Giant Eagle" in level_eight_forms

    character["class_options"]["wild_shape_forms"] = level_two_forms[:4]
    draft = create_level_up_draft({**character, "level": 3}, 4, data)
    wild_shape_choice = choice_named(draft, "Wild Shape forms")
    assert wild_shape_choice["choose"] == 2
    assert "Black Bear" in wild_shape_choice["options"]


def test_fighting_style_options_are_class_specific():
    data = app_data()

    assert "Blessed Warrior" in fighting_style_options(data, "Paladin")
    assert "Blessed Warrior" not in fighting_style_options(data, "Ranger")
    assert "Druidic Warrior" in fighting_style_options(data, "Ranger")
    assert "Druidic Warrior" not in fighting_style_options(data, "Paladin")


def test_warlock_invocation_options_filter_prerequisites():
    data = app_data()
    character = level_one_warlock()
    character["spells"]["cantrips"] = ["Mage Hand"]
    invocation_rule = data["classes_by_name"]["Warlock"]["class_options"]["eldritch_invocations"]

    level_one_options = eligible_invocation_names(character, invocation_rule, 1)
    level_five_options = eligible_invocation_names(character, invocation_rule, 5)

    assert "Agonizing Blast" not in level_one_options
    assert "Thirsting Blade" not in level_five_options

    character["spells"]["cantrips"].append("Eldritch Blast")
    character["class_options"]["eldritch_invocations"].append("Pact of the Blade")
    level_five_options = eligible_invocation_names(character, invocation_rule, 5)

    assert "Agonizing Blast" in level_five_options
    assert "Thirsting Blade" in level_five_options
    assert "Lifedrinker" not in level_five_options


def test_barbarian_level_three_primal_knowledge_is_resolved_with_subclass():
    data = app_data()
    character = level_one_barbarian()
    finalized(character, data)
    finalize_level_up(character, create_level_up_draft(character, 2, data))
    finalized(character, data)

    draft = create_level_up_draft(character, 3, data)
    subclass_choice = next(choice for choice in draft["pending_choices"] if choice["type"] == "subclass_choice")
    assert resolve_pending_choice(draft, subclass_choice["id"], "Path of the Berserker")
    primal_skill = resolve_first_option(draft, choice_named(draft, "Primal Knowledge"))

    result = commit_level_up_draft(character, draft)
    _, report = finalized(character, data)

    assert result["ok"]
    assert report["complete"]
    assert primal_skill[0] in character["skill_proficiencies"]
