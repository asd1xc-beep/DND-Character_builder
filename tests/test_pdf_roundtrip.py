import json
from copy import deepcopy
from io import BytesIO

from pypdf import PdfReader, PdfWriter

from rules.level_up import commit_level_up_draft, create_level_up_draft
from services import pdf_export, save_load
from services.character_sheet import build_character_sheet
from services.pdf_export import export_character_pdf
from services.pdf_import import parse_pdf_import
from services.pdf_roundtrip import (
    ATTACHMENT_NAME,
    FORMAT_ID,
    PAYLOAD_VERSION,
    character_checksum,
)
from services.save_load import CURRENT_SCHEMA_VERSION, canonical_character, save_character
from tests.test_level_one_builds import app_data, finalized
from tests.test_level_up import level_one_fighter


def exported_fighter(tmp_path, monkeypatch, *, name="Round Trip"):
    monkeypatch.setattr(pdf_export, "PDF_DIR", tmp_path / "pdf")
    character = level_one_fighter()
    character["name"] = name
    sheet, report = finalized(character, app_data())
    assert report["complete"]
    path = export_character_pdf(sheet, character=character)
    return character, path


def pdf_with_envelope(envelope):
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_attachment(
        ATTACHMENT_NAME,
        json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8"),
    )
    writer.write(output)
    return output.getvalue()


def test_json_save_and_pdf_attachment_share_lossless_canonical_character(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(pdf_export, "PDF_DIR", tmp_path / "pdf")
    monkeypatch.setattr(save_load, "SAVE_DIR", tmp_path / "saves")
    character = level_one_fighter()
    character["name"] = "Choice Bearing"
    finalized(character, app_data())
    character["subclass"] = "Champion"
    character["class_options"]["nested_choice"] = {
        "mode": "careful",
        "selections": ["A", "B"],
    }
    character["general_feats"] = [{
        "instance_id": "feat-instance",
        "feat_id": "actor_xphb",
        "name": "Actor",
        "source": {"type": "class_level", "class_name": "Fighter", "level": 4},
        "choices": {"ability": "Charisma"},
    }]
    character["spells"]["known"] = ["Magic Missile"]
    character["presentation_preferences"] = {
        "primary_weapon": "Longsword",
        "featured_cantrip": "",
        "weapon_wielding_modes": {"Longsword": "one_handed"},
    }
    character["level_up_draft"] = {"transaction_id": "must-not-export"}
    character["local_path"] = r"C:\private\character.json"
    character["class_options"]["temporary_upload_path"] = r"C:\private\upload.pdf"

    sheet = build_character_sheet(character, app_data())
    save_path = save_character(character)
    pdf_path = export_character_pdf(sheet, character=character)
    saved_character = json.loads(save_path.read_text(encoding="utf-8"))
    result = parse_pdf_import(pdf_path.read_bytes())

    assert result.status == "ready"
    assert result.source_kind == "embedded_state"
    assert result.candidate_character == saved_character
    assert result.candidate_character == canonical_character(character)
    assert "level_up_draft" not in result.candidate_character
    assert "local_path" not in result.candidate_character
    assert "temporary_upload_path" not in result.candidate_character["class_options"]

    reader = PdfReader(str(pdf_path))
    assert list(reader.attachments) == [ATTACHMENT_NAME]
    envelope = json.loads(reader.attachments[ATTACHMENT_NAME][0].decode("utf-8"))
    assert envelope["format_id"] == FORMAT_ID
    assert envelope["payload_version"] == PAYLOAD_VERSION
    assert envelope["character_schema_version"] == CURRENT_SCHEMA_VERSION
    assert envelope["character_sha256"] == character_checksum(envelope["character"])
    assert envelope["owned_pdf_field_snapshot"]["CharacterName"] == "Choice Bearing"

    fields = reader.get_fields()
    assert fields["CharacterName"].get("/V") == "Choice Bearing"
    assert fields["ClassLevel"].get("/V") == "Fighter 1"


def test_older_embedded_character_schema_is_migrated_into_candidate():
    legacy_character = {
        "schema_version": 3,
        "name": "Legacy Embedded",
        "level": 1,
        "class": "Fighter",
        "hit_points": {"max": 12, "current": 7, "hit_die": "d10"},
    }
    envelope = {
        "format_id": FORMAT_ID,
        "payload_version": PAYLOAD_VERSION,
        "character_schema_version": 3,
        "ruleset": "dnd-5e-2024",
        "builder_version": "1.1",
        "exported_at": "2026-07-17T00:00:00Z",
        "character_sha256": character_checksum(legacy_character),
        "character": legacy_character,
        "owned_pdf_field_snapshot": {},
    }

    result = parse_pdf_import(pdf_with_envelope(envelope))

    assert result.status == "ready"
    assert result.candidate_character["schema_version"] == CURRENT_SCHEMA_VERSION
    assert result.candidate_character["name"] == "Legacy Embedded"
    assert result.candidate_character["hit_points"]["max"] == 12
    assert result.candidate_character["hit_points"]["maximum"] == 12
    assert any(issue.code == "character_schema_migrated" for issue in result.issues)


def test_checksum_failure_returns_error_without_candidate():
    character = {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "name": "Checksum Test",
        "level": 1,
    }
    envelope = {
        "format_id": FORMAT_ID,
        "payload_version": PAYLOAD_VERSION,
        "character_schema_version": CURRENT_SCHEMA_VERSION,
        "ruleset": "dnd-5e-2024",
        "builder_version": "1.2",
        "exported_at": "2026-07-17T00:00:00Z",
        "character_sha256": character_checksum(character),
        "character": {**character, "name": "Tampered"},
        "owned_pdf_field_snapshot": {},
    }

    result = parse_pdf_import(pdf_with_envelope(envelope))

    assert result.status == "error"
    assert result.source_kind == "embedded_state"
    assert result.candidate_character == {}
    assert result.issues[0].code == "payload_checksum_mismatch"


def test_visible_builder_field_edit_requires_review_without_rewriting_candidate(
    tmp_path,
    monkeypatch,
):
    character, pdf_path = exported_fighter(
        tmp_path,
        monkeypatch,
        name="Embedded Name",
    )
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    writer.update_page_form_field_values(
        None,
        {"CharacterName": "Visible PDF Edit"},
        auto_regenerate=False,
    )
    edited_pdf = BytesIO()
    writer.write(edited_pdf)

    result = parse_pdf_import(edited_pdf.getvalue())

    assert result.status == "review_required"
    assert result.candidate_character["name"] == character["name"]
    assert result.observed_fields["CharacterName"] == "Visible PDF Edit"
    assert result.payload_info["changed_fields"]["CharacterName"] == {
        "exported": "Embedded Name",
        "observed": "Visible PDF Edit",
    }
    assert any(issue.code == "builder_owned_fields_changed" for issue in result.issues)


def test_parsing_then_cancelling_leaves_active_character_unchanged(
    tmp_path,
    monkeypatch,
):
    imported_character, pdf_path = exported_fighter(
        tmp_path,
        monkeypatch,
        name="Imported Candidate",
    )
    active_character = level_one_fighter()
    active_character["name"] = "Active Character"
    active_before = deepcopy(active_character)

    result = parse_pdf_import(pdf_path.read_bytes())

    assert result.status == "ready"
    assert active_character == active_before
    assert result.candidate_character is not imported_character
    result.candidate_character["name"] = "Candidate Edited During Review"
    assert active_character == active_before


def test_imported_character_can_finalize_the_next_normal_level_up_draft(
    tmp_path,
    monkeypatch,
):
    data = app_data()
    character, pdf_path = exported_fighter(
        tmp_path,
        monkeypatch,
        name="Next Level",
    )
    result = parse_pdf_import(pdf_path.read_bytes())
    imported = result.candidate_character

    draft = create_level_up_draft(imported, 2, data)
    outcome = commit_level_up_draft(imported, draft, data)

    assert result.status == "ready"
    assert draft["character_id"] == character["character_id"]
    assert draft["target_level"] == 2
    assert outcome["ok"]
    assert imported["level"] == 2
