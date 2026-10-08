from typing import Annotated, TypeVar

from pydantic import Field, StringConstraints

T = TypeVar("T")

TickerSymbol = Annotated[str, StringConstraints(
    strip_whitespace=True, min_length=1, max_length=500, pattern=r"^[A-Za-z0-9.^=_&+-]+$",
)]


def int_range(ge: int | None = 1, le: int | None = 100) -> type[int]:
    return Annotated[int, Field(ge=ge, le=le)]


def string(min_length: int = 1, max_length: int = 100) -> type[str]:
    return Annotated[str, Field(min_length=min_length, max_length=max_length, pattern=r"^[^<>]*$")]


def list_of(item_type: type[T] = string(), min_length: int = 1, max_length: int = 100) -> type[list[T]]:
    return Annotated[list[item_type], Field(min_length=min_length, max_length=max_length)]
