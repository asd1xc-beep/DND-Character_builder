from copy import deepcopy

import pytest
from pypdf import PdfReader

from models.character import new_character
from rules.import_reconciliation import (
    build_reconciliation_draft,
    level_up_safety_report,
)
from services import pdf_export, save_load
from services.character_engine import recalculate_character
from services.character_sheet import build_character_sheet
from services.pdf_export import export_character_pdf
from services.save_load import migrate_character
from tests.test_import_reconciliation import (
    compatible_result,
    complete_fighter_selections,
)
from tests.test_level_one_builds import app_data, finalized
from tests.test_level_up import level_one_fighter
from ui.pdf_import import (
    PdfImportAdoptionError,
    adopt_pdf_import_candidate,
)


def ready_reconciliation(data, **result_kwargs):
    result = compatible_result(**result_kwargs)
    reconciliation = build_reconciliation_draft(
        result,
        complete_fighter_selections(result, data),
        data,
    )
    assert reconciliation.can_confirm
    return result, reconciliation


def test_schema_four_migration_adds_schema_five_import_defaults():
    migrated = migrate_character({
        "schema_version": 4,
        "name": "Schema Four",
        "pdf_passthrough_fields": {
            "Alignment": "Neutral",
            "CHARACTER IMAGE": "unsafe",
            "CharacterName": "must not override",
            "Backstory": {"complex": True},
        },
        "import_overrides": {"maximum_hp_adjustment": "7"},
        "import_provenance": {
            "source_kind": "compatible_form",
            "status": "reviewed",
            "warnings": ["One warning"],
            "raw_pdf_bytes": "must be removed",
        },
    })

    assert migrated["schema_version"] == 5
    assert migrated["import_overrides"] == {"maximum_hp_adjustment": 7}
    assert migrated["pdf_passthrough_fields"] == {"Alignment": "Neutral"}
    assert migrated["import_provenance"] == {
        "source_kind": "compatible_form",
        "status": "reviewed",
        "warnings": ["One warning"],
    }


def test_confirmed_adoption_is_atomic_and_clears_character_bound_state():
    data = app_data()
    result, reconciliation = ready_reconciliation(
        data,
        equipment="Rope",
    )
    result.passthrough_fields = {
        "Alignment": "Neutral Good",
        "Backstory": "Recovered history",
    }
    active = {"name": "Active Hero", "notes": "preserve on failure"}
    active_before = deepcopy(active)
    session = {
        "data_source": "5etools",
        "character": active,
        "level_up_draft": {"target_level": 12},
        "ability_score_method": "stale",
        "custom_equipment_search": "stale",
        "pdf_import_draft": {"temporary": True},
    }

    adopted = adopt_pdf_import_candidate(
        session,
        reconciliation,
        result,
        data,
        imported_at="2026-07-27T22:00:00Z",
    )

    assert active == active_before
    assert adopted is session["character"]
    assert adopted["name"] == "Recovered Hero"
    assert adopted["schema_version"] == 5
    assert adopted["pdf_passthrough_fields"] == {
        "Alignment": "Neutral Good",
        "Backstory": "Recovered history",
    }
    assert {
        key: value
        for key, value in adopted["import_provenance"].items()
        if key != "warnings"
    } == {
        "source_kind": "compatible_form",
        "payload_version": 0,
        "template_signature": "",
        "imported_at": "2026-07-27T22:00:00Z",
        "status": "reviewed",
        "ability_history_reconstructed": False,
        "hp_history_reconstructed": False,
    }
    assert "Imported maximum HP adjustment: +5" in (
        adopted["import_provenance"]["warnings"]
    )
    assert session["data_source"] == "5etools"
    assert session["level_up_draft"] is None
    assert session["requested_builder_tab"] == "Character Sheet"
    assert session["pdf_import_handoff_summary"]["character_name"] == "Recovered Hero"
    assert "ability_score_method" not in session
    assert "custom_equipment_search" not in session
    assert "pdf_import_draft" not in session


def test_failed_adoption_leaves_active_character_and_session_untouched():
    data = app_data()
    result, reconciliation = ready_reconciliation(data)
    reconciliation.can_confirm = False
    session = {
        "character": {"name": "Active Hero"},
        "level_up_draft": {"target_level": 5},
        "widget": "keep",
    }
    before = deepcopy(session)

    with pytest.raises(PdfImportAdoptionError):
        adopt_pdf_import_candidate(
            session,
            reconciliation,
            result,
            data,
        )

    assert session == before


def test_final_validation_failure_is_atomic_even_if_ui_flag_is_stale():
    data = app_data()

    class StaleReconciliation:
        can_confirm = True
        candidate_character = new_character()
        issues = []
        comparisons = []

    result = compatible_result()
    session = {
        "character": {"name": "Active Hero"},
        "level_up_draft": {"target_level": 5},
    }
    before = deepcopy(session)

    with pytest.raises(PdfImportAdoptionError, match="final validation"):
        adopt_pdf_import_candidate(
            session,
            StaleReconciliation(),
            result,
            data,
        )

    assert session == before


def test_level_up_gate_requires_normal_validation_and_completed_import_status():
    data = app_data()
    incomplete = new_character()
    assert not level_up_safety_report(incomplete, data)["safe"]

    complete = level_one_fighter()
    _, validation = finalized(complete, data)
    assert validation["complete"]
    assert level_up_safety_report(complete, data)["safe"]

    complete["import_provenance"] = {
        "source_kind": "compatible_form",
        "status": "pending",
    }
    gate = level_up_safety_report(complete, data)
    assert not gate["safe"]
    assert gate["blockers"][0] == (
        "Complete PDF import reconciliation before leveling up"
    )


def test_safe_passthrough_fields_survive_reexport_but_builder_fields_win(
    tmp_path,
    monkeypatch,
):
    data = app_data()
    character = level_one_fighter()
    character["name"] = "Builder Owned Name"
    _, validation = finalized(character, data)
    assert validation["complete"]
    character["pdf_passthrough_fields"] = {
        "Alignment": "Lawful Good",
        "Backstory": "Recovered from the legacy PDF",
        "CharacterName": "Untrusted visible name",
        "CHARACTER IMAGE": "not allowed",
    }
    monkeypatch.setattr(pdf_export, "PDF_DIR", tmp_path / "pdf")

    path = export_character_pdf(
        build_character_sheet(character, data),
        character=character,
    )
    fields = PdfReader(str(path)).get_fields()

    assert fields["Alignment"].get("/V") == "Lawful Good"
    assert fields["Backstory"].get("/V") == "Recovered from the legacy PDF"
    assert fields["CharacterName"].get("/V") == "Builder Owned Name"
    assert migrate_character(character)["pdf_passthrough_fields"] == {
        "Alignment": "Lawful Good",
        "Backstory": "Recovered from the legacy PDF",
    }


def test_adoption_does_not_create_a_json_save(tmp_path, monkeypatch):
    data = app_data()
    result, reconciliation = ready_reconciliation(data)
    monkeypatch.setattr(save_load, "SAVE_DIR", tmp_path / "saves")

    adopt_pdf_import_candidate(
        {"character": {"name": "Active"}},
        reconciliation,
        result,
        data,
    )

    assert not save_load.SAVE_DIR.exists()
