import io
import re
from dataclasses import dataclass

from pypdf import PdfReader


@dataclass
class ExtractedPage:
    """Represents text extracted from a specific page or section of a document."""

    page_number: int
    text: str


def normalize_text(text: str) -> str:
    """
    Normalize extracted document text:
    - Normalizes line endings to \n.
    - Replaces non-breaking spaces (\xa0) with standard spaces.
    - Strips trailing whitespace per line.
    - Collapses 3 or more consecutive newlines into 2 (preserves paragraph boundaries).
    """
    if not text:
        return ""

    # Replace carriage returns and non-breaking spaces
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")

    # Strip whitespace at the end of each line
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Collapse 3+ newlines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def validate_file_magic_bytes(file_bytes: bytes, filename: str) -> str:
    """
    Verify magic bytes (file signature) to prevent malicious files disguised
    with fake extensions.
    Returns detected canonical mime type ('application/pdf' or 'text/plain').
    Raises ValueError on invalid signature.
    """
    if not file_bytes:
        raise ValueError("Uploaded file is empty (0 bytes).")

    lower_name = filename.lower()

    if lower_name.endswith(".pdf"):
        # PDF magic bytes: starts with %PDF-
        if not file_bytes.startswith(b"%PDF"):
            raise ValueError(
                "Invalid PDF file: Missing %PDF header signature. "
                "The file may be corrupted or renamed."
            )
        return "application/pdf"

    elif lower_name.endswith(".txt"):
        # Text file validation: reject binary files with null bytes
        if b"\x00" in file_bytes[:1024]:
            raise ValueError("Invalid TXT file: Binary or executable content detected.")
        return "text/plain"

    else:
        raise ValueError(
            f"Unsupported file format '{filename}'. Currently supported formats: PDF, TXT."
        )


def extract_text_from_file(file_bytes: bytes, filename: str) -> list[ExtractedPage]:
    """
    Extract text from uploaded document bytes while preserving 1-indexed page numbers.
    Raises ValueError if extraction fails or if the document contains no extractable text.
    """
    mime_type = validate_file_magic_bytes(file_bytes, filename)
    pages: list[ExtractedPage] = []

    if mime_type == "application/pdf":
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            if len(reader.pages) == 0:
                raise ValueError("PDF file contains 0 pages.")

            for idx, page in enumerate(reader.pages, start=1):
                raw_text = page.extract_text() or ""
                cleaned = normalize_text(raw_text)
                if cleaned:
                    pages.append(ExtractedPage(page_number=idx, text=cleaned))

        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Failed to parse PDF document: {str(e)}") from e

    elif mime_type == "text/plain":
        # Attempt UTF-8 decoding with fallback to latin-1
        try:
            raw_text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raw_text = file_bytes.decode("latin-1", errors="replace")

        cleaned = normalize_text(raw_text)
        if cleaned:
            pages.append(ExtractedPage(page_number=1, text=cleaned))

    # Validate that we actually extracted meaningful textual content
    total_text_length = sum(len(p.text) for p in pages)
    if total_text_length < 10:
        raise ValueError(
            "No extractable text found in document. "
            "If this is a scanned document or image-only PDF, an OCR step is required."
        )

    return pages
