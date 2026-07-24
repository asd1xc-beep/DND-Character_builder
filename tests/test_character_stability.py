import json

from models.character import DEFAULT_CHARACTER, new_character
from rules.level_up import commit_level_up_draft, create_level_up_draft, resolve_pending_choice
from services.character_engine import recalculate_character
from services.character_state import change_background, change_character_class, change_species
from services.save_load import CURRENT_SCHEMA_VERSION, load_character, migrate_character
from tests.test_level_one_builds import app_data, finalized
from tests.test_level_up import level_one_fighter


def test_migrate_character_adds_new_defaults_without_losing_choices():
    migrated = migrate_character({
        "name": "Old Save",
        "class": "Fighter",
        "hit_points": {
            "max": 12,
            "current": 7,
            "hit_die": "d10",
        },
    })

    assert migrated["schema_version"] == CURRENT_SCHEMA_VERSION
    assert migrated["character_id"]
    assert migrated["name"] == "Old Save"
    assert migrated["class"] == "Fighter"
    assert migrated["pending_choices"] == []
    assert migrated["completed_level_up_transactions"] == []
    assert migrated["hp_history"] == []
    assert migrated["general_feats"] == []
    assert migrated["ability_score_adjustments"] == []
    assert migrated["hit_points"]["max"] == 12
    assert migrated["hit_points"]["maximum"] == 12
    assert migrated["hit_points"]["current"] == 7
    assert migrated["hit_points"]["temporary"] == 0


def test_load_character_migrates_old_json_file(tmp_path):
    path = tmp_path / "old.json"
    path.write_text(json.dumps({"name": "Loaded Old Save"}), encoding="utf-8")

    character = load_character(path)

    assert character["schema_version"] == CURRENT_SCHEMA_VERSION
    assert character["character_id"]
    assert character["name"] == "Loaded Old Save"
    assert character["base_ability_scores"] == DEFAULT_CHARACTER["base_ability_scores"]


def test_migration_converts_legacy_general_feat_names_to_instances():
    character = migrate_character({
        "name": "Legacy Feat",
        "general_feats": ["Actor"],
    })

    assert character["schema_version"] == CURRENT_SCHEMA_VERSION
    assert character["general_feats"][0]["name"] == "Actor"
    assert character["general_feats"][0]["feat_id"] is None
    assert character["general_feats"][0]["source"] == {"type": "legacy"}
    assert character["general_feats"][0]["instance_id"]


def test_migration_moves_legacy_magical_secrets_into_prepared_spells_without_deleting():
    character = migrate_character({
        "name": "Legacy Bard",
        "class": "Bard",
        "level": 10,
        "class_options": {"magical_secrets": ["Cone of Cold", "Mass Cure Wounds"]},
        "spells": {"prepared": ["Cure Wounds"], "known": [], "cantrips": []},
    })

    assert character["class_options"]["legacy_magical_secrets"] == ["Cone of Cold", "Mass Cure Wounds"]
    assert "magical_secrets" not in character["class_options"]
    assert "Cone of Cold" in character["spells"]["prepared"]
    assert "Mass Cure Wounds" in character["spells"]["prepared"]
    assert character["migration_warnings"]


def test_migration_converts_legacy_mystic_arcanum_into_structured_record():
    character = migrate_character({
        "name": "Legacy Warlock",
        "class": "Warlock",
        "level": 11,
        "class_options": {"mystic_arcanum": ["Arcane Gate"]},
    })

    assert character["class_options"]["mystic_arcanum_6"] == ["Arcane Gate"]
    assert "mystic_arcanum" not in character["class_options"]
    assert character["mystic_arcanum"][0]["spell_name"] == "Arcane Gate"
    assert character["mystic_arcanum"][0]["spell_level"] == 6
    assert character["mystic_arcanum"][0]["source_level"] == 11
    assert character["mystic_arcanum"][0]["casting_rules"]["recharge"] == "long_rest"


def test_load_character_preserves_structured_general_feat_instances(tmp_path):
    feat_instance = {
        "instance_id": "actor-instance",
        "feat_id": "actor_xphb",
        "name": "Actor",
        "source": {"type": "class_level", "class_name": "Fighter", "level": 4},
        "choices": {},
    }
    path = tmp_path / "structured_feat.json"
    path.write_text(json.dumps({
        "name": "Structured Feat",
        "general_feats": [feat_instance],
    }), encoding="utf-8")

    character = load_character(path)

    assert character["general_feats"] == [feat_instance]


def test_migration_preserves_unsupported_saved_level():
    character = migrate_character({
        "name": "High Level",
        "level": 20,
        "class": "Fighter",
    })

    assert character["level"] == 20


def test_changing_class_removes_incompatible_class_state():
    character = level_one_fighter()
    character["level"] = 2
    character["class_levels"] = {"Fighter": 2}
    character["level_history"] = [{"class": "Fighter"}]
    character["weapon_masteries"] = ["Longsword"]
    character["class_options"] = {"fighting_style": "Defense"}
    character["subclass"] = "Champion"
    character["ability_score_adjustments"] = [{"adjustments": {"Strength": 2}, "source_type": "class_level"}]
    character["general_feats"] = ["Actor"]
    character["completed_level_up_transactions"] = ["old-transaction"]

    change_character_class(character, "Wizard")

    assert character["class"] == "Wizard"
    assert character["level"] == 1
    assert character["class_levels"] == {"Wizard": 1}
    assert character["level_history"] == []
    assert character["weapon_masteries"] == []
    assert character["class_options"] == {}
    assert character["subclass"] == ""
    assert character["hp_history"] == []
    assert character["ability_score_adjustments"] == []
    assert character["general_feats"] == []
    assert character["completed_level_up_transactions"] == []


def test_changing_class_after_level_four_removes_asi_and_feat_benefits():
    data = app_data()
    character = level_one_fighter()
    finalized(character, data)
    commit_level_up_draft(character, create_level_up_draft(character, 2, data), data)
    finalized(character, data)
    level_three = create_level_up_draft(character, 3, data)
    resolve_pending_choice(level_three, level_three["pending_choices"][0]["id"], "Champion")
    commit_level_up_draft(character, level_three, data)
    finalized(character, data)
    level_four = create_level_up_draft(character, 4, data)
    asi_choice = next(choice for choice in level_four["pending_choices"] if choice["type"] == "asi_or_feat")
    mastery_choice = next(choice for choice in level_four["pending_choices"] if choice["type"] == "weapon_mastery_selection")
    resolve_pending_choice(level_four, asi_choice["id"], {"mode": "asi", "ability_increases": {"Strength": 2}})
    resolve_pending_choice(level_four, mastery_choice["id"], ["Shortsword"])
    commit_level_up_draft(character, level_four, data)
    finalized(character, data)

    assert character["level"] == 4
    assert character["ability_score_adjustments"]

    change_character_class(character, "Wizard")
    recalculate_character(character, data)

    assert character["class"] == "Wizard"
    assert character["level"] == 1
    assert character["ability_score_adjustments"] == []
    assert character["general_feats"] == []
    assert character["completed_level_up_transactions"] == []
    assert character["level_history"] == []
    assert character["weapon_masteries"] == []
    assert character["background"] == "Soldier"
    assert character["species"] == "Human"


def test_changing_background_and_species_clears_dependent_state():
    character = new_character()
    character["background"] = "Soldier"
    character["species"] = "Human"
    character["background_options"] = {"primary_ability": "Strength"}
    character["species_options"] = {"origin_feats": ["Tough"]}
    character["origin_feat_choices"] = {"skills": ["Stealth"], "tools": [], "cantrips": [], "spell": "", "spellcasting_ability": ""}

    change_background(character, "Sage")
    change_species(character, "Elf")

    assert character["background_options"] == {}
    assert character["origin_feat_choices"] == DEFAULT_CHARACTER["origin_feat_choices"]
    assert character["species_options"] == {}


def test_recalculate_uses_hp_history_and_preserves_current_hp():
    data = app_data()
    character = level_one_fighter()
    recalculate_character(character, data)
    character["hit_points"]["current"] = 5
    character["base_ability_scores"]["Constitution"] = 16

    recalculate_character(character, data)

    assert character["hit_points"]["max"] == 15
    assert character["hit_points"]["current"] == 5
    assert character["hp_history"] == [{
        "character_level": 1,
        "class_name": "Fighter",
        "method": "maximum",
        "base_gain": 10,
    }]
