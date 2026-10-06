from datetime import UTC, datetime, timedelta

import yfinance as yf

from .models import Instrument, InstrumentClass, InstrumentPage, TickerInfo
from .db.repository import instruments_page, latest_price, save_instruments, save_price
from .storage import PostgresStore

PRICE_TTL = timedelta(minutes=2)


class TickerNotFoundError(LookupError):
    pass


def get_instruments(
    asset_class: InstrumentClass, offset: int = 0, limit: int = 250,
    store: PostgresStore | None = None,
) -> InstrumentPage:
    if store is not None:
        rows, total = instruments_page(store, asset_class.value, offset, limit)
        if len(rows) == limit or (rows and offset + len(rows) >= total):
            next_offset = offset + len(rows)
            return InstrumentPage(
                items=[Instrument(**row.model_dump(exclude={"updated_at"})) for row in rows],
                total=total,
                offset=offset,
                next_offset=next_offset if next_offset < total else None,
            )

    sort_field = "intradaymarketcap" if asset_class == InstrumentClass.EQUITY else "fundnetassets"

    query_type = {
        InstrumentClass.EQUITY: yf.EquityQuery,
        InstrumentClass.ETF: yf.ETFQuery,
        InstrumentClass.MUTUALFUND: yf.FundQuery,
    }[asset_class]
    template = query_type("gte", ["intradayprice", 0])
    exchanges = sorted({
        exchange
        for group in template.valid_values["exchange"].values()
        for exchange in group if exchange
    })
    query = query_type("is-in", ["exchange", *exchanges])
    response = yf.screen(
        query, offset=offset, size=limit, sortField=sort_field, sortAsc=False,
    )

    quotes = response["quotes"]
    total = response["total"]
    if not quotes and offset < total:
        raise ValueError("Yahoo returned an empty page before the end of the results.")

    items = []
    for quote in quotes:
        if not quote.get("symbol"):
            continue
        name = quote.get("longName") or quote.get("shortName")
        aliases = list(dict.fromkeys(
            alias for alias in (quote.get("longName"), quote.get("shortName"))
            if alias and alias != name and alias != quote["symbol"]
        ))
        items.append(Instrument(
            symbol=quote["symbol"],
            name=name,
            asset_class=(quote.get("quoteType") or asset_class.value).upper(),
            aliases=aliases,
            exchange=quote.get("exchange"),
            currency=quote.get("currency"),
            size=quote.get("marketCap") or quote.get("netAssets"),
        ))

    next_offset = offset + len(quotes)
    page = InstrumentPage(
        items=items,
        total=total,
        offset=offset,
        next_offset=next_offset if next_offset < total else None,
    )
    if store is not None:
        save_instruments(store, page.items)
    return page


def get_ticker_info(
    symbol: str, store: PostgresStore | None = None,
) -> TickerInfo:
    now = datetime.now(UTC)
    if store is not None:
        row = latest_price(store, symbol, since=now - PRICE_TTL)
        if row is not None:
            return TickerInfo(**row.model_dump(exclude={"id", "recorded_at"}))

    info = yf.Ticker(symbol).info
    if not info or not info.get("symbol"):
        raise TickerNotFoundError(symbol)

    price = info.get("regularMarketPrice")
    price_timestamp = info.get("regularMarketTime") if price is not None else None
    if price is None:
        price = info.get("currentPrice")
    result = TickerInfo(
        symbol=symbol,
        name=info.get("longName") or info.get("shortName"),
        exchange=info.get("fullExchangeName") or info.get("exchange"),
        currency=info.get("currency"),
        price=price,
        price_time=datetime.fromtimestamp(price_timestamp, UTC) if price_timestamp is not None else None,
    )
    if store is not None:
        save_price(store, result)
    return result


def get_tickers_info(
    symbols: list[str], store: PostgresStore | None = None,
) -> dict[str, TickerInfo]:
    return {symbol: get_ticker_info(symbol, store) for symbol in symbols}
