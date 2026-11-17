import hashlib
import math
import random
from typing import Protocol

import httpx

from app.core.config import settings


class EmbeddingProvider(Protocol):
    """Abstract protocol for embedding providers."""

    async def embed_query(self, text: str) -> list[float]:
        """Generate embedding vector for a single search question."""
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple chunks in a single batched call."""
        ...


class MockEmbeddingProvider:
    """
    Deterministic mock embedding provider.
    Generates reproducible unit-normalized vectors derived from text hash.
    Enables offline testing, CI pipelines, and local development with zero cost.
    """

    def __init__(self, dimensions: int = settings.EMBEDDING_DIMENSIONS):
        self.dimensions = dimensions

    def _generate_vector(self, text: str) -> list[float]:
        # Hash text to seed random generator for determinism
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)

        # Generate Gaussian random components
        raw_vector = [rng.gauss(0, 1) for _ in range(self.dimensions)]

        # Normalize to unit length (L2 norm = 1.0)
        norm = math.sqrt(sum(x * x for x in raw_vector))
        return [x / norm for x in raw_vector]

    async def embed_query(self, text: str) -> list[float]:
        return self._generate_vector(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._generate_vector(t) for t in texts]


class OpenAIEmbeddingProvider:
    """OpenAI Embedding Provider using text-embedding-3-small or configured model."""

    def __init__(
        self,
        api_key: str = settings.EMBEDDING_API_KEY,
        model: str = settings.EMBEDDING_MODEL,
        dimensions: int = settings.EMBEDDING_DIMENSIONS,
    ):
        self.api_key = api_key
        self.model = model
        self.dimensions = dimensions

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured in environment.")

        url = "https://api.openai.com/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": texts,
            "model": self.model,
            "dimensions": self.dimensions,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                raise RuntimeError(
                    f"OpenAI Embedding API error {response.status_code}: {response.text}"
                )
            data = response.json()
            # Sort data items by index to guarantee input ordering
            sorted_data = sorted(data["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in sorted_data]

    async def embed_query(self, text: str) -> list[float]:
        embeddings = await self.embed_batch([text])
        return embeddings[0]


def get_embedding_provider() -> EmbeddingProvider:
    """Factory creating the configured embedding provider."""
    provider_name = settings.EMBEDDING_PROVIDER.lower().strip()
    if provider_name == "openai":
        return OpenAIEmbeddingProvider()
    # Default to MockEmbeddingProvider for development and CI
    return MockEmbeddingProvider()


embedding_service = get_embedding_provider()
