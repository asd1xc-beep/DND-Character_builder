from copy import deepcopy
from io import BytesIO

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, NameObject
from reportlab.pdfgen import canvas

from services import pdf_export
from services.pdf_export import export_character_pdf
from services.pdf_import import (
    REQUIRED_CORE_FIELDS,
    extract_safe_passthrough_fields,
    normalize_form_value,
    parse_pdf_import,
)
from tests.test_level_one_builds import app_data, finalized
from tests.test_level_up import level_one_fighter


def legacy_fighter_pdf(tmp_path, monkeypatch):
    monkeypatch.setattr(pdf_export, "PDF_DIR", tmp_path / "pdf")
    character = level_one_fighter()
    character["name"] = "Legacy Fighter"
    sheet, report = finalized(character, app_data())
    assert report["complete"]
    path = export_character_pdf(sheet)
    return character, path.read_bytes()


def update_form_values(pdf_bytes, values):
    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    writer.update_page_form_field_values(None, values, auto_regenerate=False)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def remove_form_field(pdf_bytes, field_name):
    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    acroform = writer.root_object["/AcroForm"].get_object()
    acroform[NameObject("/Fields")] = ArrayObject([
        field_ref
        for field_ref in acroform["/Fields"]
        if str(field_ref.get_object().get("/T", "")) != field_name
    ])
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def flattened_copy(pdf_bytes):
    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    writer.remove_annotations(subtypes="/Widget")
    writer.root_object.pop(NameObject("/AcroForm"), None)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def unrelated_fillable_pdf():
    output = BytesIO()
    pdf = canvas.Canvas(output)
    pdf.drawString(72, 720, "Unrelated fillable form")
    pdf.acroForm.textfield(name="Email", x=72, y=680, width=240, height=18)
    pdf.save()
    return output.getvalue()


def test_exact_legacy_template_extracts_normalized_phase3_evidence(
    tmp_path,
    monkeypatch,
):
    active_character, pdf_bytes = legacy_fighter_pdf(tmp_path, monkeypatch)
    active_before = deepcopy(active_character)
    pdf_bytes = update_form_values(pdf_bytes, {
        "HPTemp": "3",
        "Spells 1014": "Fire Bolt",
        "Spells 1023": "Shield",
        "SlotsTotal 19": "4",
        "SlotsRemaining 19": "2",
        "Wpn Name": "Longsword",
        "Wpn1 AtkBonus": "+4",
        "Wpn1 Damage": "1d8+2 Slashing",
        "Equipment": "Chain Mail, Longsword",
        "Alignment": "  Chaotic Good  ",
        "Backstory": "  First line\rSecond line  ",
        "GP": "17",
    })

    result = parse_pdf_import(pdf_bytes, data=app_data())

    assert result.status == "review_required"
    assert result.source_kind == "compatible_form"
    assert result.candidate_character == {}
    assert result.payload_info["match"] == "exact"
    assert result.payload_info["missing_core_fields"] == []
    assert result.extracted_data["identity"] == {
        "name": "Legacy Fighter",
        "alternate_name": "Legacy Fighter",
        "class_level": "Fighter 1",
        "class_name": "Fighter",
        "level": 1,
        "species": "Human",
        "background": "Soldier",
    }
    assert result.extracted_data["abilities"]["Strength"] == 12
    assert result.extracted_data["abilities"]["Constitution"] == 15
    assert result.extracted_data["hit_points"]["maximum"] == 14
    assert result.extracted_data["hit_points"]["temporary"] == 3
    assert result.extracted_data["spells"]["by_level"][0] == ["Fire Bolt"]
    assert result.extracted_data["spells"]["by_level"][1] == ["Shield"]
    assert result.extracted_data["spells"]["slot_totals"][1] == 4
    assert result.extracted_data["spells"]["slot_remaining"][1] == 2
    assert result.extracted_data["presentation"]["attacks"][0] == {
        "name": "Longsword",
        "attack_bonus": "+4",
        "damage": "1d8+2 Slashing",
    }
    assert result.extracted_data["equipment"]["raw"] == "Chain Mail, Longsword"
    assert result.extracted_data["comparison"]["armor_class"] == 10
    assert result.observed_fields["Alignment"] == "Chaotic Good"
    assert result.passthrough_fields["Alignment"] == "Chaotic Good"
    assert result.passthrough_fields["Backstory"] == "First line\nSecond line"
    assert result.passthrough_fields["GP"] == "17"
    assert "Equipment" not in result.passthrough_fields
    assert "Spells 1014" not in result.passthrough_fields
    assert active_character == active_before


def test_signature_variant_with_core_fields_is_compatible(
    tmp_path,
    monkeypatch,
):
    _, pdf_bytes = legacy_fighter_pdf(tmp_path, monkeypatch)
    compatible_pdf = remove_form_field(pdf_bytes, "Age")

    result = parse_pdf_import(compatible_pdf)

    assert result.status == "review_required"
    assert result.source_kind == "compatible_form"
    assert result.payload_info["match"] == "compatible"
    assert result.payload_info["field_count"] == 333
    assert result.payload_info["known_field_ratio"] > 0.99
    assert set(REQUIRED_CORE_FIELDS).isdisjoint(result.payload_info["missing_core_fields"])
    assert any(issue.code == "compatible_template_signature" for issue in result.issues)


def test_missing_and_conflicting_values_return_stable_review_issues(
    tmp_path,
    monkeypatch,
):
    _, pdf_bytes = legacy_fighter_pdf(tmp_path, monkeypatch)
    edited = update_form_values(pdf_bytes, {
        "CharacterName 2": "Different Name",
        "ClassLevel": "",
        "DEX": "not a score",
        "HPMax": "",
    })

    result = parse_pdf_import(edited)
    issue_codes = [issue.code for issue in result.issues]

    assert result.status == "review_required"
    assert result.source_kind == "compatible_form"
    assert "character_name_conflict" in issue_codes
    assert "class_level_missing" in issue_codes
    assert "ability_score_missing_or_invalid" in issue_codes
    assert "maximum_hp_missing_or_invalid" in issue_codes
    assert result.extracted_data["abilities"]["Dexterity"] is None
    assert result.extracted_data["hit_points"]["maximum"] is None


def test_flattened_builder_sheet_is_rejected_clearly(
    tmp_path,
    monkeypatch,
):
    _, pdf_bytes = legacy_fighter_pdf(tmp_path, monkeypatch)

    result = parse_pdf_import(flattened_copy(pdf_bytes))

    assert result.status == "unsupported"
    assert result.source_kind == "flattened"
    assert result.candidate_character == {}
    assert result.observed_fields == {}
    assert result.issues[0].code == "flattened_pdf"


def test_unrelated_fillable_pdf_is_rejected_with_missing_core_fields():
    result = parse_pdf_import(unrelated_fillable_pdf())

    assert result.status == "unsupported"
    assert result.source_kind == "other"
    assert result.issues[0].code == "unsupported_template"
    assert set(result.payload_info["missing_core_fields"]) == REQUIRED_CORE_FIELDS
    assert result.payload_info["known_field_ratio"] == 0.0


def test_unknown_catalog_values_return_actionable_blockers(
    tmp_path,
    monkeypatch,
):
    _, pdf_bytes = legacy_fighter_pdf(tmp_path, monkeypatch)
    edited = update_form_values(pdf_bytes, {
        "ClassLevel": "Chronomancer 3",
        "Race ": "Moon Person",
        "Background": "Unknown Trade",
        "Spells 1023": "Mystery Beam",
    })

    result = parse_pdf_import(edited, data=app_data())
    issue_codes = {issue.code for issue in result.issues}

    assert result.status == "review_required"
    assert result.extracted_data["identity"]["class_name"] == "Chronomancer"
    assert result.extracted_data["identity"]["level"] == 3
    assert {"class_unknown", "species_unknown", "background_unknown", "spell_unknown"} <= issue_codes


def test_scalar_form_normalization_handles_text_and_checkbox_states():
    assert normalize_form_value("  line one\r\nline two  ", "/Tx") == "line one\nline two"
    assert normalize_form_value("/Yes", "/Btn") is True
    assert normalize_form_value("/Off", "/Btn") is False
    assert extract_safe_passthrough_fields({
        "Check Box 11": True,
        "Check Box 12": False,
        "CHARACTER IMAGE": True,
    }) == {"Check Box 11": True}
