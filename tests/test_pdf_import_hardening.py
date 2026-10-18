from io import BytesIO

from pypdf import PdfWriter

from services.pdf_import import MAX_PDF_BYTES, parse_pdf_import


def encrypted_pdf_bytes():
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.encrypt("secret-password")
    writer.write(output)
    return output.getvalue()


def test_corrupted_pdf_fails_safely_without_candidate():
    result = parse_pdf_import(b"%PDF-1.7\nthis is not a complete PDF")

    assert result.status == "error"
    assert result.candidate_character == {}
    assert result.issues[0].code == "pdf_unreadable"


def test_encrypted_pdf_fails_with_specific_guidance():
    result = parse_pdf_import(encrypted_pdf_bytes())

    assert result.status == "error"
    assert result.candidate_character == {}
    assert result.issues[0].code == "pdf_encrypted"


def test_oversized_pdf_is_rejected_before_parsing():
    result = parse_pdf_import(b"x" * (MAX_PDF_BYTES + 1))

    assert result.status == "error"
    assert result.candidate_character == {}
    assert result.issues[0].code == "pdf_too_large"
