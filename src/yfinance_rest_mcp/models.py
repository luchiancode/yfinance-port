from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

class InstrumentClass(StrEnum):
    EQUITY = "EQUITY"
    ETF = "ETF"
    MUTUALFUND = "MUTUALFUND"

class TickerInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    symbol: str
    name: str | None = None
    exchange: str | None = None
    currency: str | None = None
    price: float | None = None
    price_time: datetime | None = Field(
        default=None,
        alias="priceTime",
        description="UTC source timestamp for the regular-market price; null if unavailable.",
    )

class Instrument(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    symbol: str
    name: str | None = None
    asset_class: str = Field(alias="assetClass")
    aliases: list[str] = Field(default_factory=list)
    exchange: str | None = Field(default=None, description="Exchange identifier, not a MIC code.")
    currency: str | None = Field(default=None, description="Currency or price-unit code.")
    size: float | None = Field(default=None, exclude=True)


class InstrumentPage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[Instrument]
    total: int
    offset: int
    next_offset: int | None = Field(alias="nextOffset")


class Article(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    external_id: str | None = Field(default=None, alias="externalId")
    title: str | None = None
    description: str | None = None
    content: str | None = None
    url: str | None = None
    image: str | None = None
    published_at: datetime | None = Field(default=None, alias="publishedAt")
    source: str | None = None
