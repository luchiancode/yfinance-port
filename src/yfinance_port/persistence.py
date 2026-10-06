from collections.abc import Iterable
from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session

from .models import CatalogueTicker, TickerInfo
from .storage import CatalogueAsset, PostgresStore, PriceSnapshot


def save_catalogue(store: PostgresStore, items: Iterable[CatalogueTicker]) -> None:
    updated_at = datetime.now(UTC)
    rows = {
        item.symbol: {**item.model_dump(), "updated_at": updated_at}
        for item in items
    }
    if not rows:
        return
    statement = insert(CatalogueAsset).values(list(rows.values()))
    statement = statement.on_conflict_do_update(
        index_elements=[CatalogueAsset.symbol],
        set_={key: statement.excluded[key] for key in next(iter(rows.values())) if key != "symbol"},
    )
    with Session(store.engine) as session:
        session.execute(statement)
        session.commit()


def save_prices(store: PostgresStore, records: Iterable[TickerInfo]) -> None:
    snapshots = [PriceSnapshot(**record.model_dump()) for record in records]
    if not snapshots:
        return
    with Session(store.engine) as session:
        session.add_all(snapshots)
        session.commit()
