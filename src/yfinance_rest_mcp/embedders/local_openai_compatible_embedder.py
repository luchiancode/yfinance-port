import os
from typing import Self

import httpx

from .protocol import Embedder


class LocalOpenAICompatibleEmbedder(Embedder):
    _instance: "LocalOpenAICompatibleEmbedder | None" = None

    def __init__(self) -> None:
        self.model = os.getenv("EMBEDDING_MODEL") or ""
        self._base_url = os.getenv("LOCAL_OPENAI_BASE_URL", "http://localhost:1234/v1").rstrip("/")

        self._headers = {}

        #Optional
        if api_key := os.getenv("LOCAL_OPENAI_API_KEY"):
            self._headers["Authorization"] = f"Bearer {api_key}"

    @classmethod
    def get(cls) -> Self:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def enabled(self) -> bool:
        return bool(self.model)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.enabled:
            return []

        response = httpx.post(
            f"{self._base_url}/embeddings",
            json={"model": self.model, "input": texts, "encoding_format": "float"},
            headers=self._headers,
            timeout=60,
        )

        response.raise_for_status()
        data = response.json()["data"]

        return [item["embedding"] for item in sorted(data, key=lambda item: item["index"])]
