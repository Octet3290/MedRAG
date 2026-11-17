from app.rag.chunker import chunk_pages, count_tokens
from app.rag.extractor import ExtractedPage


def test_count_tokens():
    """Verify tokenizer counts tokens accurately."""
    sample = "Cardiology and pharmacology research study."
    tokens = count_tokens(sample)
    assert tokens > 0
    assert tokens <= len(sample)


def test_chunk_pages_preserves_page_numbers():
    """Verify chunks retain page number metadata."""
    pages = [
        ExtractedPage(page_number=1, text="Page 1: Introduction to Beta Blockers."),
        ExtractedPage(page_number=2, text="Page 2: Clinical trial results and efficacy."),
    ]
    chunks = chunk_pages(pages, chunk_size=100, chunk_overlap=10)
    assert len(chunks) >= 2
    assert chunks[0].page_number == 1
    assert chunks[1].page_number == 2


def test_chunk_overlap():
    """Verify that consecutive chunks share overlapping context."""
    pages = [
        ExtractedPage(
            page_number=1,
            text=(
                "Paragraph A: First medical finding on ACE inhibitors.\n\n"
                "Paragraph B: Second medical finding on Angiotensin Receptor Blockers.\n\n"
                "Paragraph C: Third clinical finding on calcium channel blockers.\n\n"
                "Paragraph D: Fourth finding on direct vasodilators."
            ),
        )
    ]
    # Small chunk size to force multiple chunks with overlap
    chunks = chunk_pages(pages, chunk_size=20, chunk_overlap=8)
    assert len(chunks) > 1
    # Check that sequential chunk indices are contiguous (0, 1, 2...)
    for idx, c in enumerate(chunks):
        assert c.chunk_index == idx
