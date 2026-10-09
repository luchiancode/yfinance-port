from typing import Protocol, Self


class Embedder(Protocol):
    model: str

    @classmethod
    def get(cls) -> Self: ...

    @property
    def enabled(self) -> bool: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...
