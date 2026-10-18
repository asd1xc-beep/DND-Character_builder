from copy import deepcopy

from models.character import ABILITIES
from rules.import_reconciliation import (
    build_reconciliation_draft,
    initial_reconciliation_selections,
    recover_equipment,
)
from rules.level_up import commit_level_up_draft, create_level_up_draft
from services.character_engine import recalculate_character
from services.pdf_import import PdfImportResult
from tests.test_level_one_builds import app_data


def compatible_result(
    *,
    class_name="Fighter",
    level=1,
    species="Dwarf",
    background="Soldier",
    abilities=None,
    maximum_hp=17,
    current_hp=12,
    equipment="",
    spells=None,
    features="",
    comparison=None,
):
    return PdfImportResult(
        status="review_required",
        source_kind="compatible_form",
        extracted_data={
            "identity": {
                "name": "Recovered Hero",
                "alternate_name": "Recovered Hero",
                "class_level": f"{class_name} {level}",
                "class_name": class_name,
                "level": level,
                "species": species,
                "background": background,
            },
            "abilities": abilities or {
                "Strength": 15,
                "Dexterity": 14,
                "Constitution": 13,
                "Intelligence": 12,
                "Wisdom": 10,
                "Charisma": 8,
            },
            "hit_points": {
                "maximum": maximum_hp,
                "current": current_hp,
                "temporary": 2,
            },
            "spells": {"by_level": spells or {}},
            "equipment": {"raw": equipment},
            "presentation": {
                "features": features,
                "additional_features": "",
            },
            "comparison": comparison or {},
        },
    )


def complete_fighter_selections(result, data):
    selections = initial_reconciliation_selections(result, data)
    selections.update({
        "background_primary_ability": "Strength",
        "background_secondary_ability": "Constitution",
        "ability_scores_confirmed": True,
        "class_skills": ["Athletics", "Intimidation"],
        "class_options": {"fighting_style": "Defense"},
        "weapon_masteries": ["Greatsword", "Longbow", "Dagger"],
        "spells_confirmed": True,
        "feats_confirmed": True,
        "masteries_confirmed": True,
        "equipment_confirmed": True,
    })
    return selections


def test_reconciliation_builds_detached_candidate_without_mutating_inputs():
    data = app_data()
    result = compatible_result()
    selections = complete_fighter_selections(result, data)
    result_before = deepcopy(result.to_dict())
    selections_before = deepcopy(selections)
    active_character = {"name": "Active Hero", "notes": "must survive"}
    active_before = deepcopy(active_character)

    draft = build_reconciliation_draft(result, selections, data)

    assert draft.can_confirm
    assert draft.status == "ready"
    assert draft.candidate_character["name"] == "Recovered Hero"
    assert active_character == active_before
    assert result.to_dict() == result_before
    assert selections == selections_before
    assert "level_up_draft" not in draft.candidate_character
    assert not any(
        "path" in key.casefold()
        for key in draft.candidate_character
    )


def test_imported_ability_baseline_reproduces_level_twenty_automatic_adjustments():
    data = app_data()
    observed = {
        "Strength": 24,
        "Dexterity": 14,
        "Constitution": 25,
        "Intelligence": 10,
        "Wisdom": 12,
        "Charisma": 8,
    }
    result = compatible_result(
        class_name="Barbarian",
        level=20,
        abilities=observed,
        maximum_hp=240,
    )
    selections = initial_reconciliation_selections(result, data)
    selections.update({
        "background_primary_ability": "Strength",
        "background_secondary_ability": "Constitution",
        "ability_scores_confirmed": True,
    })

    draft = build_reconciliation_draft(result, selections, data)

    assert draft.candidate_character["ability_scores"] == observed
    assert draft.candidate_character["base_ability_scores"]["Strength"] == 18
    assert draft.candidate_character["base_ability_scores"]["Constitution"] == 20
    assert draft.candidate_character["ability_score_adjustments"] == []
    assert not any(
        issue.code.endswith("cannot_reproduce") for issue in draft.issues
    )


def test_maximum_hp_adjustment_is_explicit_and_stable_through_recalculation():
    data = app_data()
    result = compatible_result(maximum_hp=27, current_hp=19)
    selections = complete_fighter_selections(result, data)
    draft = build_reconciliation_draft(result, selections, data)
    candidate = deepcopy(draft.candidate_character)
    initial_details = deepcopy(candidate["hit_point_details"])

    recalculate_character(candidate, data)

    assert initial_details["import_adjustment"] != 0
    assert initial_details["maximum"] == 27
    assert candidate["hit_points"]["maximum"] == 27
    assert candidate["hit_points"]["current"] == 19
    assert candidate["hit_point_details"] == initial_details


def test_use_calculated_hp_discards_import_adjustment():
    data = app_data()
    result = compatible_result(maximum_hp=99)
    selections = complete_fighter_selections(result, data)
    selections["preserve_observed_maximum_hp"] = False

    draft = build_reconciliation_draft(result, selections, data)

    details = draft.candidate_character["hit_point_details"]
    assert draft.candidate_character["import_overrides"]["maximum_hp_adjustment"] == 0
    assert details["import_adjustment"] == 0
    assert details["maximum"] == details["calculated_before_import_adjustment"]
    assert draft.candidate_character["hit_points"]["maximum"] != 99


def test_negative_maximum_hp_adjustment_is_preserved_explicitly():
    data = app_data()
    result = compatible_result(maximum_hp=5, current_hp=5)
    selections = complete_fighter_selections(result, data)

    draft = build_reconciliation_draft(result, selections, data)

    details = draft.candidate_character["hit_point_details"]
    assert details["import_adjustment"] < 0
    assert details["maximum"] == 5
    assert draft.candidate_character["hit_points"]["maximum"] == 5


def test_comparison_conflicts_are_visible_warnings_not_silent_state_rewrites():
    data = app_data()
    result = compatible_result(comparison={
        "armor_class": 99,
        "initiative": "+7",
        "proficiency_bonus": "+2",
        "passive_perception": 10,
        "ability_modifiers": {ability: "" for ability in ABILITIES},
    })
    selections = complete_fighter_selections(result, data)

    draft = build_reconciliation_draft(result, selections, data)

    armor = next(item for item in draft.comparisons if item.key == "armor_class")
    assert armor.status == "conflict"
    assert armor.observed == 99
    assert armor.calculated == draft.candidate_character["armor_class"]
    assert any(issue.code == "comparison_armor_class" for issue in draft.issues)
    assert draft.can_confirm


def test_confirmation_stays_blocked_until_required_review_choices_are_complete():
    data = app_data()
    result = compatible_result(equipment="Rope")
    selections = initial_reconciliation_selections(result, data)

    blocked = build_reconciliation_draft(result, selections, data)
    ready = build_reconciliation_draft(
        result,
        complete_fighter_selections(result, data),
        data,
    )

    assert not blocked.can_confirm
    assert any(issue.severity == "blocker" for issue in blocked.issues)
    assert ready.can_confirm
    assert not any(issue.severity == "blocker" for issue in ready.issues)


def test_reconciled_candidate_can_start_the_normal_next_level_draft():
    data = app_data()
    result = compatible_result()
    reconciliation = build_reconciliation_draft(
        result,
        complete_fighter_selections(result, data),
        data,
    )

    level_up = create_level_up_draft(
        reconciliation.candidate_character,
        2,
        data,
    )

    assert reconciliation.can_confirm
    assert level_up["current_level"] == 1
    assert level_up["target_level"] == 2
    assert not level_up.get("blocked_reason")


def test_imported_hp_adjustment_survives_and_normal_hp_is_added_at_next_level():
    data = app_data()
    result = compatible_result(maximum_hp=27, current_hp=19)
    reconciliation = build_reconciliation_draft(
        result,
        complete_fighter_selections(result, data),
        data,
    )
    candidate = reconciliation.candidate_character
    before = candidate["hit_points"]["maximum"]
    imported_adjustment = candidate["import_overrides"]["maximum_hp_adjustment"]
    level_up = create_level_up_draft(candidate, 2, data)

    committed = commit_level_up_draft(candidate, level_up, data)
    recalculate_character(candidate, data)

    assert committed["ok"]
    assert candidate["level"] == 2
    assert candidate["import_overrides"]["maximum_hp_adjustment"] == imported_adjustment
    assert candidate["hit_points"]["maximum"] == before + level_up["hp_increase"]


def test_equipment_recovery_matches_long_names_before_preserving_residual_text():
    recovered, residual = recover_equipment(
        "Alchemist's Fire, Rope, Moon Key",
        ["Fire", "Alchemist's Fire", "Rope"],
    )

    assert recovered == ["Alchemist's Fire", "Rope"]
    assert residual == ["Moon Key"]
