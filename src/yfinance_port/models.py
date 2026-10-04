from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class TickerInfo(BaseModel):
    symbol: str
    name: str | None = None
    exchange: str | None = None
    currency: str | None = None
    price: float | None = None
    price_time: datetime | None = Field(
        default=None,
        serialization_alias="priceTime",
        description="UTC source timestamp for the regular-market price; null if unavailable.",
    )


class CatalogueAssetClass(StrEnum):
    EQUITY = "EQUITY"
    ETF = "ETF"
    MUTUALFUND = "MUTUALFUND"
    CRYPTOCURRENCY = "CRYPTOCURRENCY"


class CatalogueTicker(BaseModel):
    symbol: str
    name: str | None = None
    asset_class: str = Field(serialization_alias="assetClass")
    aliases: list[str] = Field(default_factory=list)
    exchange: str | None = Field(default=None, description="Yahoo's exchange identifier, not a MIC code.")
    currency: str | None = Field(default=None, description="Yahoo's currency or price-unit code.")


class CataloguePage(BaseModel):
    items: list[CatalogueTicker]
    total: int
    offset: int
    next_offset: int | None = Field(serialization_alias="nextOffset")
    truncated: bool = False
