import pytest

from app.rag.extractor import (
    extract_text_from_file,
    normalize_text,
    validate_file_magic_bytes,
)


def test_normalize_text():
    """Verify text normalization cleans whitespace and standardizes newlines."""
    raw = "Line 1   \r\n\r\n\r\nLine 2 with\xa0non-breaking space.   \r\n"
    normalized = normalize_text(raw)
    assert "\r" not in normalized
    assert "\xa0" not in normalized
    assert "\n\n\n" not in normalized
    assert normalized == "Line 1\n\nLine 2 with non-breaking space."


def test_magic_bytes_validation_txt():
    """Verify plain text validation accepts valid UTF-8 and rejects binary nulls."""
    valid_bytes = b"This is a valid clinical trial report."
    assert validate_file_magic_bytes(valid_bytes, "report.txt") == "text/plain"

    binary_bytes = b"\x00\x01\x02Malicious Binary"
    with pytest.raises(ValueError, match="Binary or executable content detected"):
        validate_file_magic_bytes(binary_bytes, "report.txt")


def test_magic_bytes_validation_pdf():
    """Verify PDF validation requires %PDF- signature."""
    valid_pdf = b"%PDF-1.4\n1 0 obj\n<<\n>>\nendobj"
    assert validate_file_magic_bytes(valid_pdf, "paper.pdf") == "application/pdf"

    fake_pdf = b"NOT A PDF BUT RENAMED"
    with pytest.raises(ValueError, match="Missing %PDF header signature"):
        validate_file_magic_bytes(fake_pdf, "paper.pdf")


def test_extract_text_from_txt():
    """Verify text extraction from valid plain text."""
    txt_content = (
        "HYPERTENSION MANAGEMENT CLINICAL PROTOCOL\n\n"
        "Patients presenting with blood pressure > 140/90 mmHg "
        "should be evaluated for ACE inhibitors."
    )
    pages = extract_text_from_file(txt_content.encode("utf-8"), "protocol.txt")
    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert "HYPERTENSION" in pages[0].text


def test_extract_empty_document_rejected():
    """Verify that documents with insufficient text are rejected."""
    empty_content = b"Short"
    with pytest.raises(ValueError, match="No extractable text found"):
        extract_text_from_file(empty_content, "empty.txt")
