from datetime import UTC, datetime
from enum import StrEnum

import yfinance as yf
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


class TickerNotFoundError(LookupError):
    pass


def get_ticker_catalogue(
    asset_class: CatalogueAssetClass, offset: int = 0, limit: int = 250,
) -> CataloguePage:
    sort_field = "intradaymarketcap" if asset_class in (
        CatalogueAssetClass.EQUITY, CatalogueAssetClass.CRYPTOCURRENCY,
    ) else "fundnetassets"

    if asset_class == CatalogueAssetClass.CRYPTOCURRENCY:
        if offset != 0:
            raise ValueError("yfinance cannot paginate the predefined crypto screener.")
        response = yf.screen(
            "all_cryptocurrencies_us", count=limit, sortField=sort_field, sortAsc=False,
        )
    else:
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
    has_more = next_offset < total
    truncated = asset_class == CatalogueAssetClass.CRYPTOCURRENCY and has_more
    return CataloguePage(
        items=items,
        total=total,
        offset=offset,
        next_offset=next_offset if has_more and not truncated else None,
        truncated=truncated,
    )


def get_tickers_info(symbols: list[str]) -> dict[str, TickerInfo]:
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
    return result
