from datetime import UTC, datetime, timedelta

from .models import InstrumentClass, InstrumentPage, TickerInfo
from .db.repository import save_instruments, save_price
from .sources.instrument_source import InstrumentSource
from .sources.source import Source
from .sources.ticker_info_source import TickerInfoSource, TickerNotFoundError
from .db.storage import PostgresStore

__all__ = [
    "PRICE_TTL",
    "TickerNotFoundError",
    "get_instruments",
    "get_ticker_info",
    "get_tickers_info",
]

PRICE_TTL = timedelta(minutes=2)


def get_instruments(
    asset_class: InstrumentClass, offset: int = 0, limit: int = 250,
    store: PostgresStore | None = None,
) -> InstrumentPage:
    source: Source[InstrumentPage] = InstrumentSource(asset_class, offset, limit, store)
    page = source.get_from_db()
    if page is not None:
        return page
    page = source.get_from_yfinance()
    if store is not None:
        save_instruments(store, page.items)
    return page


def get_ticker_info(
    symbol: str, store: PostgresStore | None = None,
) -> TickerInfo:
    now = datetime.now(UTC)
    source: Source[TickerInfo] = TickerInfoSource(symbol, store, since=now - PRICE_TTL)
    result = source.get_from_db()
    if result is not None:
        return result
    result = source.get_from_yfinance()
    if store is not None:
        save_price(store, result)
    return result


def get_tickers_info(
    symbols: list[str], store: PostgresStore | None = None,
) -> dict[str, TickerInfo]:
    return {symbol: get_ticker_info(symbol, store) for symbol in symbols}
