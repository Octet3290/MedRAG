import re
from typing import Protocol

import httpx

from app.core.config import settings


class LLMProvider(Protocol):
    """Protocol defining the interface for LLM response generation."""

    async def generate_answer(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> str:
        """Generate a grounded completion given system instructions and user context prompt."""
        ...


class MockLLMProvider:
    """
    Deterministic Mock LLM provider for unit testing, offline development, and CI/CD.
    Examines context chunks and generates realistic grounded answers with citations,
    or triggers honest refusals if the context is empty or unrelated.
    """

    async def generate_answer(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> str:
        # 1. Handle Query Reformulation Request
        if "reformulation" in system_prompt.lower():
            fq_match = re.search(
                r"Follow-up Question:\s*(.+?)(?:\nStandalone Query:|$)",
                user_prompt,
                re.DOTALL,
            )
            follow_up = fq_match.group(1).strip() if fq_match else user_prompt.strip()

            # Check if follow-up contains anaphoric pronouns (it, its, this medication)
            words = follow_up.lower().split()
            if any(term in words for term in ["it", "its", "this", "these", "the medication"]):
                hist_match = re.search(
                    r"Chat History:\s*(.+?)(?:\nFollow-up Question:|$)",
                    user_prompt,
                    re.DOTALL,
                )
                if hist_match:
                    hist_text = hist_match.group(1)
                    # Extract prominent medical subject (metformin, diabetes, etc.)
                    candidates = [
                        w
                        for w in re.findall(r"\b[A-Za-z]{5,}\b", hist_text)
                        if w.lower()
                        not in {
                            "assistant",
                            "question",
                            "answer",
                            "about",
                            "could",
                            "would",
                            "should",
                            "first",
                            "protocol",
                            "please",
                        }
                    ]
                    if candidates:
                        subj = candidates[0]
                        return f"{follow_up} regarding {subj}"
            return follow_up

        # 2. Extract question (supports both single-turn Question: and multi-turn Current Question:)
        q_match = re.search(
            r"(?:Current Question|Question):\s*(.+?)(?:\nAnswer:|$)",
            user_prompt,
            re.DOTALL,
        )
        question = q_match.group(1).strip() if q_match else ""

        # Extract context block
        ctx_match = re.search(r"<context>(.*?)</context>", user_prompt, re.DOTALL)
        context_content = ctx_match.group(1).strip() if ctx_match else ""

        if not context_content or "No relevant context found." in context_content:
            return "I cannot answer this question based on the provided documents."

        # Parse available chunks: [Chunk X] (Document: doc, Page: page, ChunkId: id)\n<text>
        chunk_pattern = re.compile(
            r"\[Chunk\s*\d+\]\s*\(Document:\s*(.+?),\s*Page:\s*(\d+|N/A).*?\)\n(.*?)(?=\[Chunk|\Z)",
            re.DOTALL,
        )
        parsed_chunks = chunk_pattern.findall(context_content)

        if not parsed_chunks:
            return "I cannot answer this question based on the provided documents."

        # Compute keyword overlap between question and chunks
        q_words = {w.lower() for w in re.findall(r"\w+", question) if len(w) > 3}

        # If question is brief and chat history is present, borrow key subject from history
        chat_hist_match = re.search(r"<chat_history>(.*?)</chat_history>", user_prompt, re.DOTALL)
        if chat_hist_match and len(q_words) <= 2:
            hist_words = {
                w.lower() for w in re.findall(r"\w+", chat_hist_match.group(1)) if len(w) > 4
            }
            q_words = q_words.union(hist_words)
        matched_chunks = []
        for doc_title, page_num, text in parsed_chunks:
            text_words = {w.lower() for w in re.findall(r"\w+", text)}
            overlap = q_words.intersection(text_words)
            if overlap:
                matched_chunks.append(
                    (doc_title.strip(), page_num.strip(), text.strip(), len(overlap))
                )

        # If zero keywords match, trigger refusal rule
        if not matched_chunks:
            return "I cannot answer this question based on the provided documents."

        # Sort by highest overlap
        matched_chunks.sort(key=lambda x: x[3], reverse=True)
        top_doc, top_page, top_text, _ = matched_chunks[0]

        # Extract the sentence of the chunk that best addresses the question
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n\n+", top_text) if s.strip()]
        best_sentence = sentences[0]
        best_score = -1
        for s in sentences:
            s_words = {w.lower() for w in re.findall(r"\w+", s)}
            score = len(q_words.intersection(s_words))
            if score > best_score:
                best_score = score
                best_sentence = s

        if not best_sentence.endswith("."):
            best_sentence += "."

        return (
            f"Based on the provided documentation, {best_sentence} "
            f"[Source: {top_doc}, Page: {top_page}]"
        )


class OpenAILLMProvider:
    """Production LLM provider using OpenAI's Chat Completions API."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or settings.LLM_API_KEY
        self.model = model or settings.LLM_MODEL
        self.api_url = "https://api.openai.com/v1/chat/completions"

    async def generate_answer(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> str:
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY is not configured. "
                "Set LLM_API_KEY in .env or switch LLM_PROVIDER to 'mock'."
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(self.api_url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"OpenAI LLM API error ({resp.status_code}): {resp.text}")

            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()


def get_llm_provider() -> LLMProvider:
    """Factory resolving the active LLM provider from settings."""
    provider_name = settings.LLM_PROVIDER.lower().strip()
    if provider_name == "openai":
        return OpenAILLMProvider()
    return MockLLMProvider()


llm_service = get_llm_provider()
