from models.character import new_character
from services.character_engine import recalculate_character
from services.character_sheet import build_character_sheet
from tests.test_level_one_builds import app_data, finalized


def test_contact_patron_grants_contact_other_plane_with_casting_metadata():
    data = app_data()
    character = new_character()
    character.update({
        "name": "Morrow",
        "species": "Dwarf",
        "background": "Sage",
        "class": "Warlock",
        "level": 9,
    })
    character["background_options"] = {"primary_ability": "Charisma", "secondary_ability": "Dexterity"}
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
    character["spells"] = {
        "cantrips": ["Blade Ward", "Chill Touch", "Eldritch Blast"],
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

    sheet, report = finalized(character, data)
    grant = next(grant for grant in sheet["spells"]["grant_details"] if grant["name"] == "Contact Other Plane")

    assert "Contact Other Plane" in sheet["spells"]["granted"]
    assert grant["source"]["source_name"] == "Contact Patron"
    assert grant["counts_against_limit"] is False
    assert grant["casting_rules"]["free_casts"] == 1
    assert grant["casting_rules"]["recharge"] == "long_rest"
    assert grant["casting_rules"]["auto_success"] is True


def test_nature_speaker_grants_commune_with_nature_as_wisdom_ritual():
    data = app_data()
    character = new_character()
    character.update({
        "name": "Tal",
        "species": "Human",
        "background": "Soldier",
        "class": "Barbarian",
        "subclass": "Path of the Wild Heart",
        "level": 10,
    })
    character["background_options"] = {"primary_ability": "Strength", "secondary_ability": "Constitution"}
    character["class_options"] = {
        "class_skills": ["Athletics", "Survival"],
        "primal_knowledge_skill": ["Nature"],
        "aspect_of_the_wilds": "Owl",
    }
    character["weapon_masteries"] = ["Greataxe", "Handaxe"]

    recalculate_character(character, data)
    sheet = build_character_sheet(character)
    grant = next(grant for grant in sheet["spells"]["grant_details"] if grant["name"] == "Commune with Nature")

    assert "Commune with Nature" in sheet["spells"]["granted"]
    assert grant["source"]["source_name"] == "Nature Speaker"
    assert grant["spellcasting_ability"] == "Wisdom"
    assert grant["casting_rules"]["ritual_only"] is True
    assert grant["counts_against_limit"] is False
