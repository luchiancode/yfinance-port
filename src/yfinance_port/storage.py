import os

from dotenv import load_dotenv
from sqlalchemy import Engine, URL
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import SQLModel, create_engine

from .db.tables import Instrument, PriceSnapshot


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
        SQLModel.metadata.create_all(engine, tables=[Instrument.__table__, PriceSnapshot.__table__])
    except SQLAlchemyError:
        engine.dispose()
        raise
    return PostgresStore(engine)
