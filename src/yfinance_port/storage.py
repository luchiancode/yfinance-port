import os
from datetime import UTC, datetime

from dotenv import load_dotenv
from sqlalchemy import DateTime, Engine, URL
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Field, SQLModel, create_engine


class CatalogueAsset(SQLModel, table=True):
    __tablename__ = "catalogue_assets"

    symbol: str = Field(primary_key=True)
    name: str | None = None
    asset_class: str
    aliases: list[str] = Field(default_factory=list, sa_type=JSONB)
    exchange: str | None = None
    currency: str | None = None
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


class PostgresStore:
    def __init__(self, engine: Engine):
        self.engine = engine

    def close(self) -> None:
        self.engine.dispose()


def create_store() -> PostgresStore | None:
    load_dotenv(".env")
    persist_data = os.getenv("PERSIST_DATA", "false").strip().lower()
    if persist_data not in {"true", "false"}:
        raise ValueError("PERSIST_DATA must be true or false.")
    if persist_data == "false":
        return None

    password = os.getenv("POSTGRES_PASSWORD")
    if not password:
        raise ValueError("PERSIST_DATA=true requires POSTGRES_PASSWORD in .env.")
    url = URL.create(
        "postgresql+psycopg",
        username=os.getenv("POSTGRES_USER", "yfinance_port"),
        password=password,
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.getenv("POSTGRES_PORT", "1005")),
        database=os.getenv("POSTGRES_DB", "yfinance_port"),
    )
    engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
    try:
        SQLModel.metadata.create_all(engine)
    except SQLAlchemyError:
        engine.dispose()
        raise
    return PostgresStore(engine)
