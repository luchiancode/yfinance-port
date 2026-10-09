from datetime import UTC, datetime

import yfinance as yf

from ..models import TickerInfo
from ..db.repository import latest_price
from ..db.storage import PostgresStore
from .source import Source


class TickerNotFoundError(LookupError):
    pass


class TickerInfoSource(Source[TickerInfo]):
    def __init__(
        self,
        symbol: str, store: PostgresStore | None, *,
        since: datetime,
    ) -> None:
        self.symbol = symbol
        self.store = store
        self.since = since

    def get_from_db(self) -> TickerInfo | None:
        if self.store is None:
            return None

        row = latest_price(self.store, self.symbol, since=self.since)

        if row is None:
            return None
        
        return TickerInfo(**row.model_dump(exclude={"id", "recorded_at"}))

    def get_from_yfinance(self) -> TickerInfo:
        info = yf.Ticker(self.symbol).info

        if not info or not info.get("symbol"):
            raise TickerNotFoundError(self.symbol)

        price = info.get("regularMarketPrice")
        price_timestamp = info.get("regularMarketTime") if price is not None else None

        if price is None:
            price = info.get("currentPrice")
            
        return TickerInfo(
            symbol=self.symbol,
            name=info.get("longName") or info.get("shortName"),
            exchange=info.get("fullExchangeName") or info.get("exchange"),
            currency=info.get("currency"),
            price=price,
            price_time=datetime.fromtimestamp(price_timestamp, UTC) if price_timestamp is not None else None,
        )
