import re
from dataclasses import dataclass

import tiktoken

from app.core.config import settings
from app.rag.extractor import ExtractedPage

# Use cl100k_base (standard for GPT-4, text-embedding-3-small, etc.)
try:
    _tokenizer = tiktoken.get_encoding("cl100k_base")
except Exception:
    _tokenizer = None


def count_tokens(text: str) -> int:
    """Return the exact token count using tiktoken (fallback to word approximation)."""
    if _tokenizer:
        return len(_tokenizer.encode(text))
    return max(1, len(text.split()) * 4 // 3)


@dataclass
class Chunk:
    """A semantically bounded chunk of text with source page metadata."""

    text: str
    chunk_index: int
    page_number: int | None
    token_count: int


def _split_into_sentences(text: str) -> list[str]:
    """Split text into sentences while keeping punctuation intact."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def _chunk_single_text(
    text: str,
    page_number: int | None,
    chunk_size: int,
    chunk_overlap: int,
    start_index: int,
) -> list[Chunk]:
    """
    Chunk text within a single page boundary:
    1. Splits text by paragraphs, then sentences when paragraphs are large.
    2. Accumulates tokens up to `chunk_size`.
    3. Adds `chunk_overlap` tokens between consecutive chunks on the same page.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: list[Chunk] = []
    chunk_counter = start_index

    current_pieces: list[str] = []
    current_tokens = 0

    for paragraph in paragraphs:
        para_tokens = count_tokens(paragraph)

        # If a single paragraph is larger than chunk_size, split by sentences
        if para_tokens > chunk_size:
            units = _split_into_sentences(paragraph)
        else:
            units = [paragraph]

        for unit in units:
            unit_tokens = count_tokens(unit)

            if current_tokens + unit_tokens <= chunk_size:
                current_pieces.append(unit)
                current_tokens += unit_tokens
            else:
                # Flush current chunk
                if current_pieces:
                    chunk_text = "\n\n".join(current_pieces).strip()
                    chunks.append(
                        Chunk(
                            text=chunk_text,
                            chunk_index=chunk_counter,
                            page_number=page_number,
                            token_count=count_tokens(chunk_text),
                        )
                    )
                    chunk_counter += 1

                    # Calculate overlap from trailing pieces
                    overlap_pieces: list[str] = []
                    overlap_tokens = 0
                    for piece in reversed(current_pieces):
                        p_tokens = count_tokens(piece)
                        if overlap_tokens + p_tokens <= chunk_overlap:
                            overlap_pieces.insert(0, piece)
                            overlap_tokens += p_tokens
                        else:
                            break

                    current_pieces = overlap_pieces
                    current_tokens = overlap_tokens

                current_pieces.append(unit)
                current_tokens += unit_tokens

    # Flush final remaining pieces on this page
    if current_pieces:
        chunk_text = "\n\n".join(current_pieces).strip()
        chunks.append(
            Chunk(
                text=chunk_text,
                chunk_index=chunk_counter,
                page_number=page_number,
                token_count=count_tokens(chunk_text),
            )
        )

    return chunks


def chunk_pages(
    pages: list[ExtractedPage],
    chunk_size: int = settings.CHUNK_SIZE_TOKENS,
    chunk_overlap: int = settings.CHUNK_OVERLAP_TOKENS,
) -> list[Chunk]:
    """
    Structure-aware chunking pipeline preserving exact page numbers:
    Chunks each page independently so citations always point directly
    to the exact source page where the evidence was located.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be strictly less than chunk_size.")

    all_chunks: list[Chunk] = []
    global_index = 0

    for page in pages:
        page_chunks = _chunk_single_text(
            text=page.text,
            page_number=page.page_number,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            start_index=global_index,
        )
        all_chunks.extend(page_chunks)
        global_index += len(page_chunks)

    return all_chunks
