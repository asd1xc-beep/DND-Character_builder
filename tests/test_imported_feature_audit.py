import json
from pathlib import Path

from models.character import new_character
from rules.class_choice_rules import metamagic_total_for_level
from services.character_engine import recalculate_character
from services.character_sheet import build_character_sheet
from tests.test_level_one_builds import app_data


AUDIT_PATH = Path("data/coverage/imported_feature_audit.json")
IMPORTED_DIR = Path("data/imported/5etools")


def load_audit():
    return json.loads(AUDIT_PATH.read_text(encoding="utf-8"))


def load_imported(filename):
    return json.loads((IMPORTED_DIR / filename).read_text(encoding="utf-8"))


def slug(value):
    return "".join(char.lower() if char.isalnum() else "_" for char in str(value)).strip("_")


def test_imported_feature_audit_has_required_shape():
    audit = load_audit()
    allowed_classifications = {
        "automatic_sheet_value",
        "required_permanent_choice",
        "rest_changeable_configuration",
        "spell_grant",
        "spell_progression",
        "resource_progression",
        "feature_reference",
        "feature_upgrade",
        "proficiency_grant",
        "movement_modifier",
        "active_play_description_only",
        "unsupported",
    }

    assert audit["generated_from"] == "data/imported/5etools"
    assert audit["record_count"] == len(audit["records"])
    assert audit["records"]
    assert audit["summary"]["required_permanent_choice"] > 0
    assert audit["summary"].get("unsupported", 0) == 0
    assert "needs_manual_review" not in audit["summary"]
    assert isinstance(audit["import_warnings"], list)
    assert audit["expected_value_checkpoints"]
    for checkpoint in audit["expected_value_checkpoints"]:
        assert {"id", "feature_id", "owner", "level", "handler", "expected_values", "handler_verified"}.issubset(checkpoint)
        assert checkpoint["handler_verified"] is True, checkpoint
        assert checkpoint["expected_values"], checkpoint

    required_fields = {
        "source_type",
        "source_id",
        "owner",
        "name",
        "level",
        "classification",
        "handler",
        "handler_verified",
        "support_status",
        "reviewed",
        "description_available",
        "effects",
        "expected_output_fields",
        "output_verified",
        "related_feature_names",
        "raw_rule_indicators",
        "notes",
    }
    for record in audit["records"]:
        assert required_fields.issubset(record), record
        assert record["source_id"], record
        assert record["classification"] in allowed_classifications, record
        assert isinstance(record["effects"], list), record
        assert isinstance(record["expected_output_fields"], list), record
        assert isinstance(record["output_verified"], bool), record
        assert isinstance(record["related_feature_names"], list), record
        assert isinstance(record["raw_rule_indicators"], list), record
        assert isinstance(record["notes"], list), record
        assert record["support_status"] in {"supported", "description_only", "unsupported"}, record
        if record["handler"]:
            assert record["handler_verified"] is True, record


def test_imported_feature_audit_lists_every_imported_feature_source():
    audit_records = {record["source_id"] for record in load_audit()["records"]}
    expected = set()

    for class_data in load_imported("classes.json"):
        for level, names in class_data.get("level_features", {}).items():
            for name in names:
                expected.add(f"{slug(class_data['name'])}_{level}_{slug(name)}")
        for subclass in class_data.get("subclasses", []):
            for level, names in subclass.get("level_features", {}).items():
                for name in names:
                    expected.add(f"{slug(class_data['name'])}_{slug(subclass['short_name'])}_{level}_{slug(name)}")

    for species in load_imported("species.json"):
        for trait in species.get("traits", []):
            expected.add(f"{slug(species['name'])}_{slug(trait)}")

    for background in load_imported("backgrounds.json"):
        feature = background.get("feature")
        if feature:
            expected.add(f"{slug(background['name'])}_{slug(feature)}")

    for feat in load_imported("feats.json"):
        expected.add(feat.get("id") or slug(feat.get("name", "feat")))

    assert expected.issubset(audit_records)


def test_required_choices_spell_grants_and_unknowns_are_explicit():
    for record in load_audit()["records"]:
        if record["classification"] == "required_permanent_choice":
            assert record["handler"], record
            assert record["handler_verified"] is True, record
            assert record["reviewed"] is True, record
        if record["classification"] == "spell_grant":
            assert record["handler"], record
            if record["source_type"] == "subclass_spell_grant":
                assert record["handler"] == "rules.leveling.get_active_subclass_grants", record
                assert record["grant_count"] > 0, record
        if record["classification"] == "unsupported":
            assert record["support_status"] == "unsupported", record
            assert record["notes"], record


def test_enabled_level_nine_to_twelve_class_features_are_explicitly_classified():
    enabled_records = [
        record
        for record in load_audit()["records"]
        if record["source_type"] in {"class_feature", "subclass_feature"}
        and record["level"]
        and 9 <= int(record["level"]) <= 12
    ]
    unsupported = {record["source_id"] for record in enabled_records if record["classification"] == "unsupported"}

    assert "needs_manual_review" not in {record["classification"] for record in enabled_records}
    assert unsupported == set()

    by_id = {record["source_id"]: record for record in enabled_records}
    assert by_id["warlock_9_contact_patron"]["classification"] == "spell_grant"
    assert by_id["barbarian_wild_heart_10_nature_speaker"]["classification"] == "spell_grant"
    assert by_id["warlock_fiend_10_fiendish_resilience"]["classification"] == "rest_changeable_configuration"
    assert by_id["wizard_diviner_10_the_third_eye"]["classification"] == "rest_changeable_configuration"
    assert by_id["bard_10_magical_secrets"]["classification"] == "feature_upgrade"
    assert by_id["druid_sea_10_stormborn"]["classification"] == "active_play_description_only"
    assert by_id["warlock_11_mystic_arcanum"]["classification"] == "required_permanent_choice"

    for record in enabled_records:
        if record["classification"] == "unsupported":
            continue
        assert record["reviewed"] is True, record
        assert record["handler"], record
        assert record["handler_verified"] is True, record


def test_level_thirteen_to_sixteen_audit_entries_are_classified_for_next_enablement():
    enabled_records = [
        record
        for record in load_audit()["records"]
        if record["source_type"] in {"class_feature", "subclass_feature"}
        and record["level"]
        and 13 <= int(record["level"]) <= 16
    ]
    unsupported = {record["source_id"] for record in enabled_records if record["classification"] == "unsupported"}
    by_id = {record["source_id"]: record for record in enabled_records}

    assert unsupported == set()
    assert by_id["monk_14_disciplined_survivor"]["classification"] == "proficiency_grant"
    assert by_id["rogue_15_slippery_mind"]["classification"] == "proficiency_grant"
    assert by_id["wizard_diviner_14_greater_portent"]["classification"] == "resource_progression"
    assert by_id["wizard_diviner_14_greater_portent"]["expected_output_fields"] == ["portent_dice"]
    assert by_id["fighter_13_indomitable"]["expected_output_fields"] == [
        "indomitable_uses",
        "indomitable_recharge",
    ]
    assert by_id["ranger_14_nature_s_veil"]["expected_output_fields"] == [
        "natures_veil_uses",
        "natures_veil_recharge",
    ]
    assert by_id["rogue_14_devious_strikes"]["classification"] == "feature_reference"
    assert by_id["rogue_14_devious_strikes"]["related_feature_names"] == [
        "Daze",
        "Knock Out",
        "Obscure",
    ]
    assert by_id["ranger_fey_wanderer_15_misty_wanderer"]["classification"] == "spell_grant"
    assert by_id["paladin_glory_15_glorious_defense"]["expected_output_fields"] == [
        "glorious_defense_uses",
        "glorious_defense_recharge",
    ]
    assert by_id["barbarian_berserker_14_intimidating_presence"]["expected_output_fields"] == [
        "intimidating_presence_free_uses",
        "intimidating_presence_alternate_recovery_resource",
    ]
    assert by_id["rogue_soulknife_13_psychic_veil"]["expected_output_fields"] == [
        "psychic_veil_free_uses",
        "psychic_veil_alternate_recovery_resource",
    ]
    assert by_id["fighter_psi_warrior_15_bulwark_of_force"]["expected_output_fields"] == [
        "bulwark_of_force_free_uses",
        "bulwark_of_force_targets",
        "bulwark_of_force_alternate_recovery_resource",
    ]

    for record in enabled_records:
        assert record["reviewed"] is True, record
        assert record["handler"], record
        assert record["handler_verified"] is True, record
        if record["expected_output_fields"] or record["related_feature_names"]:
            assert record["output_verified"] is True, record


def test_all_level_one_to_twenty_class_and_subclass_features_are_classified():
    records = [
        record
        for record in load_audit()["records"]
        if record["source_type"] in {"class_feature", "subclass_feature"}
        and record["level"]
        and 1 <= int(record["level"]) <= 20
    ]
    unsupported = [
        record
        for record in records
        if record["classification"] == "unsupported"
    ]

    assert unsupported == []
    for record in records:
        assert record["reviewed"] is True, record
        assert record["handler"], record
        assert record["handler_verified"] is True, record


def test_level_five_to_sixteen_feature_references_are_audited_from_imported_data():
    by_id = {record["source_id"]: record for record in load_audit()["records"]}

    assert by_id["rogue_5_cunning_strike"]["classification"] == "feature_reference"
    assert by_id["rogue_5_cunning_strike"]["related_feature_names"] == [
        "Poison",
        "Trip",
        "Withdraw",
    ]
    assert by_id["rogue_5_cunning_strike"]["raw_rule_indicators"] == ["refClassFeature"]
    assert by_id["rogue_5_cunning_strike"]["output_verified"] is True


def test_level_seventeen_to_twenty_support_labels_include_high_level_sheet_values():
    by_id = {record["source_id"]: record for record in load_audit()["records"]}

    assert by_id["cleric_light_17_corona_of_light"]["classification"] == "resource_progression"
    assert by_id["cleric_light_17_corona_of_light"]["expected_output_fields"] == [
        "corona_of_light_uses",
        "corona_of_light_recharge",
    ]
    assert by_id["cleric_war_17_avatar_of_battle"]["classification"] == "automatic_sheet_value"
    assert by_id["cleric_war_17_avatar_of_battle"]["expected_output_fields"] == ["damage_resistances"]
    assert by_id["fighter_psi_warrior_18_telekinetic_master"]["classification"] == "spell_grant"
    assert by_id["sorcerer_draconic_18_dragon_companion"]["classification"] == "spell_grant"
    assert by_id["ranger_18_feral_senses"]["expected_output_fields"] == ["blindsight_range"]
    assert by_id["paladin_18_aura_expansion"]["expected_output_fields"] == ["aura_of_protection_range"]


def test_epic_boon_audit_support_metadata_is_precise():
    by_id = {record["source_id"]: record for record in load_audit()["records"]}

    assert by_id["boon_of_truesight_xphb"]["support"]["sheet_calculation"] == "supported"
    assert by_id["boon_of_truesight_xphb"]["expected_output_fields"] == ["truesight_range"]
    assert by_id["boon_of_energy_resistance_xphb"]["support"]["selection"] == "supported"
    assert by_id["boon_of_energy_resistance_xphb"]["expected_output_fields"] == ["damage_resistances"]
    assert by_id["boon_of_recovery_xphb"]["support"]["sheet_calculation"] == "partial"
    assert by_id["boon_of_the_night_spirit_xphb"]["support"]["sheet_calculation"] == "description_only"


def test_expected_value_checkpoints_match_real_sheet_outputs():
    data = app_data()
    for checkpoint in load_audit()["expected_value_checkpoints"]:
        assert checkpoint_actual_values(checkpoint, data) == checkpoint["expected_values"], checkpoint


def checkpoint_actual_values(checkpoint, data):
    level = int(checkpoint["level"])
    feature_id = checkpoint["feature_id"]
    if feature_id == "sorcerer_metamagic":
        return {"metamagic_options_known": metamagic_total_for_level(level)}

    class_name, subclass_name = checkpoint_owner_parts(checkpoint["owner"])
    character = checkpoint_character(class_name, subclass_name, level)
    recalculate_character(character, data)
    resources = build_character_sheet(character)["resources"]
    return {
        key: resources.get(key)
        for key in checkpoint["expected_values"]
    }


def checkpoint_owner_parts(owner):
    if ":" in owner:
        class_name, subclass_name = owner.split(":", 1)
        return class_name.strip(), subclass_name.strip()
    return owner, ""


def checkpoint_character(class_name, subclass_name, level):
    character = new_character()
    character.update({
        "name": f"Checkpoint {class_name}",
        "species": "Human",
        "background": "Soldier",
        "class": class_name,
        "subclass": subclass_name,
        "level": level,
    })
    character["background_options"] = {
        "primary_ability": "Strength",
        "secondary_ability": "Constitution",
    }
    character["species_options"] = {
        "skill_proficiencies": ["Perception"],
        "origin_feats": ["Tough"],
    }
    character["class_options"] = {
        "class_skills": ["Athletics", "Survival"],
        "battle_master_save_ability": "Strength",
    }
    character["base_ability_scores"].update({
        "Strength": 18,
        "Dexterity": 14,
        "Constitution": 16,
        "Intelligence": 14,
        "Wisdom": 16,
        "Charisma": 16,
    })
    return character
