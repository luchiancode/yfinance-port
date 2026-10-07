from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class Instrument(SQLModel, table=True):
    __tablename__ = "instruments"

    symbol: str = Field(primary_key=True)
    name: str | None = None
    asset_class: str
    aliases: list[str] = Field(default_factory=list, sa_type=JSONB)
    exchange: str | None = None
    currency: str | None = None
    size: float | None = None
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), sa_type=DateTime(timezone=True),
    )


class PriceSnapshot(SQLModel, table=True):
    __tablename__ = "price_snapshots"

    id: int | None = Field(default=None, primary_key=True)
    symbol: str = Field(index=True)
    name: str | None = None
    exchange: str | None = None
    currency: str | None = None
    price: float | None = None
    price_time: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), sa_type=DateTime(timezone=True),
    )
