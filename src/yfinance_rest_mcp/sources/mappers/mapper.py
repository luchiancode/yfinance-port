from collections.abc import Iterable
from typing import Protocol


class Mapper[T, R](Protocol):
    def map(self, item: T) -> R | None: ...

    def map_all(self, items: Iterable[T]) -> list[R]: ...
