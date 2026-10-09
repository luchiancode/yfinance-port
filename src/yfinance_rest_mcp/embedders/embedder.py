import os
from typing import Self

import httpx

from .protocol import Embedder

OPENROUTER_EMBEDDINGS_URL = "https://openrouter.ai/api/v1/embeddings"


class OpenRouterEmbedder(Embedder):
    _instance: "OpenRouterEmbedder | None" = None

    def __init__(self) -> None:
        self.model = os.getenv("EMBEDDING_MODEL") or ""

        self._api_key = os.getenv("OPENROUTER_API_KEY") or ""

        if bool(self.model) != bool(self._api_key):
            raise ValueError("EMBEDDING_MODEL and OPENROUTER_API_KEY must be set together.")

        self._headers = {"Authorization": f"Bearer {self._api_key}"}

        #Optional
        if site_url := os.getenv("YOUR_SITE_URL"):
            self._headers["HTTP-Referer"] = site_url
        #Optional
        if site_name := os.getenv("YOUR_SITE_NAME"):
            self._headers["X-OpenRouter-Title"] = site_name

    @classmethod
    def get(cls) -> Self:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def enabled(self) -> bool:
        return bool(self.model and self._api_key)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.enabled:
            return []

        response = httpx.post(
            OPENROUTER_EMBEDDINGS_URL,
            json={"model": self.model, "input": texts, "encoding_format": "float"},
            headers=self._headers,
            timeout=30,
        )
        
        response.raise_for_status()
        data = response.json()["data"]
        
        return [item["embedding"] for item in sorted(data, key=lambda item: item["index"])]
