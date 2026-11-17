import re

from app.models.chunk import DocumentChunk
from app.schemas.rag import CitationItem

# Regex pattern matching: [Source: filename.pdf, Page: 1] or [Source: filename.pdf, Page: N/A]
CITATION_REGEX = re.compile(
    r"\[Source:\s*([^,\]]+),\s*Page:\s*(\d+|N/A)\]",
    re.IGNORECASE,
)


class CitationValidator:
    """
    Validates that citations referenced in generated answers correspond to actual
    chunks retrieved from pgvector, defending against LLM citation hallucinations.
    """

    def validate(
        self,
        answer: str,
        retrieved_chunks: list[tuple[DocumentChunk, float]],
    ) -> list[CitationItem]:
        """
        Parses citations from answer text, matches them against retrieved chunks,
        and returns structured verified citations.
        """
        if not retrieved_chunks:
            return []

        verified_citations: list[CitationItem] = []
        seen_chunk_ids: set[str] = set()

        # Build lookup table of retrieved chunks
        chunk_map: list[dict] = []
        for chunk, _dist in retrieved_chunks:
            doc_title = (
                chunk.document.original_filename
                if chunk.document and chunk.document.original_filename
                else ""
            )
            chunk_map.append(
                {
                    "chunk": chunk,
                    "doc_title": doc_title.lower().strip(),
                    "page_number": chunk.page_number,
                }
            )

        # 1. Parse explicit citation tags: [Source: <doc>, Page: <page>]
        matches = CITATION_REGEX.findall(answer)
        for cited_doc, cited_page in matches:
            cited_doc_clean = cited_doc.strip().lower()
            cited_page_num = int(cited_page) if cited_page.isdigit() else None

            # Find matching retrieved chunk
            for entry in chunk_map:
                chunk = entry["chunk"]
                if str(chunk.id) in seen_chunk_ids:
                    continue

                title_match = (
                    cited_doc_clean in entry["doc_title"] or entry["doc_title"] in cited_doc_clean
                )
                page_match = (
                    cited_page_num is None
                    or entry["page_number"] is None
                    or entry["page_number"] == cited_page_num
                )

                if title_match and page_match:
                    seen_chunk_ids.add(str(chunk.id))
                    # Produce excerpt (first 160 characters)
                    excerpt = (
                        chunk.text_content[:160] + "..."
                        if len(chunk.text_content) > 160
                        else chunk.text_content
                    )
                    doc_display_title = (
                        chunk.document.original_filename
                        if chunk.document and chunk.document.original_filename
                        else "Document"
                    )
                    verified_citations.append(
                        CitationItem(
                            document_id=chunk.document_id,
                            document_title=doc_display_title,
                            page_number=chunk.page_number,
                            chunk_id=chunk.id,
                            excerpt=excerpt,
                        )
                    )
                    break

        # 2. Fallback: If no explicit brackets were parsed or answer is grounded in top chunks,
        # ensure top retrieved chunk is included if answer contains content and is not a refusal.
        refusal_phrase = "cannot answer this question based on the provided documents"
        if not verified_citations and refusal_phrase.lower() not in answer.lower():
            for chunk, _dist in retrieved_chunks[:2]:
                if str(chunk.id) in seen_chunk_ids:
                    continue
                doc_display_title = (
                    chunk.document.original_filename
                    if chunk.document and chunk.document.original_filename
                    else "Document"
                )
                excerpt = (
                    chunk.text_content[:160] + "..."
                    if len(chunk.text_content) > 160
                    else chunk.text_content
                )
                verified_citations.append(
                    CitationItem(
                        document_id=chunk.document_id,
                        document_title=doc_display_title,
                        page_number=chunk.page_number,
                        chunk_id=chunk.id,
                        excerpt=excerpt,
                    )
                )
                seen_chunk_ids.add(str(chunk.id))

        return verified_citations


citation_validator = CitationValidator()
