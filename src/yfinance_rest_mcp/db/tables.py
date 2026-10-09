from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime
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


class NewsArticle(SQLModel, table=True):
    __tablename__ = "news_articles"

    external_id: str = Field(primary_key=True)
    title: str | None = None
    description: str | None = None
    url: str | None = None
    image: str | None = None
    published_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    source: str | None = None
    embedding: list[float] | None = Field(default=None, sa_column=Column(Vector()))
    embedding_model: str | None = None
    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), sa_type=DateTime(timezone=True),
    )
