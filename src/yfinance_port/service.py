from datetime import UTC, datetime

import yfinance as yf

from .models import CatalogueAssetClass, CataloguePage, CatalogueTicker, TickerInfo
from .persistence import save_catalogue, save_prices
from .storage import PostgresStore


class TickerNotFoundError(LookupError):
    pass


def get_ticker_catalogue(
    asset_class: CatalogueAssetClass, offset: int = 0, limit: int = 250,
    store: PostgresStore | None = None,
) -> CataloguePage:
    sort_field = "intradaymarketcap" if asset_class == CatalogueAssetClass.EQUITY else "fundnetassets"

    query_type = {
        CatalogueAssetClass.EQUITY: yf.EquityQuery,
        CatalogueAssetClass.ETF: yf.ETFQuery,
        CatalogueAssetClass.MUTUALFUND: yf.FundQuery,
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
        raise ValueError("Yahoo returned an empty catalogue page before the end of the results.")

    items = []
    for quote in quotes:
        if not quote.get("symbol"):
            continue
        name = quote.get("longName") or quote.get("shortName")
        aliases = list(dict.fromkeys(
            alias for alias in (quote.get("longName"), quote.get("shortName"))
            if alias and alias != name and alias != quote["symbol"]
        ))
        items.append(CatalogueTicker(
            symbol=quote["symbol"],
            name=name,
            asset_class=(quote.get("quoteType") or asset_class.value).upper(),
            aliases=aliases,
            exchange=quote.get("exchange"),
            currency=quote.get("currency"),
        ))

    next_offset = offset + len(quotes)
    page = CataloguePage(
        items=items,
        total=total,
        offset=offset,
        next_offset=next_offset if next_offset < total else None,
    )
    if store is not None:
        save_catalogue(store, page.items)
    return page


def get_tickers_info(
    symbols: list[str], store: PostgresStore | None = None,
) -> dict[str, TickerInfo]:
    tickers = yf.Tickers(symbols)
    result = {}
    for symbol, ticker in tickers.tickers.items():
        info = ticker.info
        if not info or not info.get("symbol"):
            raise TickerNotFoundError(symbol)

        price = info.get("regularMarketPrice")
        price_timestamp = info.get("regularMarketTime") if price is not None else None
        if price is None:
            price = info.get("currentPrice")
        result[symbol] = TickerInfo(
            symbol=symbol,
            name=info.get("longName") or info.get("shortName"),
            exchange=info.get("fullExchangeName") or info.get("exchange"),
            currency=info.get("currency"),
            price=price,
            price_time=datetime.fromtimestamp(price_timestamp, UTC) if price_timestamp is not None else None,
        )
    if store is not None:
        save_prices(store, result.values())
    return result
