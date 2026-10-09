from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

import uvicorn
from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool
from yfinance.exceptions import YFRateLimitError

from .models import Article, InstrumentClass, InstrumentPage, TickerInfo
from .service import (
    TickerNotFoundError,
    get_instruments as _get_instruments,
    get_ticker_news as _get_ticker_news,
    get_tickers_info,
    search_news as _search_news,
    search_news_by_keywords as _search_news_by_keywords,
)
from .db.storage import PostgresStore, create_store
from .validation import TickerSymbol, int_range, list_of, string


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    store = await run_in_threadpool(create_store)
    app.state.store = store
    try:
        yield
    finally:
        if store is not None:
            await run_in_threadpool(store.close)


app = FastAPI(
    title="yfinance-rest-mcp",
    description="An HTTP API for accessing yfinance data.",
    lifespan=lifespan,
)


def get_store(request: Request) -> PostgresStore | None:
    return request.app.state.store


StoreDep = Annotated[PostgresStore | None, Depends(get_store)]


@app.exception_handler(YFRateLimitError)
def rate_limit_handler(_request: Request, _exc: YFRateLimitError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": "Upstream rate limit reached. Try again later."})


@app.exception_handler(SQLAlchemyError)
def persistence_error_handler(_request: Request, _exc: SQLAlchemyError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": "Unable to persist data in PostgreSQL."})


@app.exception_handler(Exception)
def upstream_error_handler(_request: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": "Unable to fetch data."})


@app.post(
    "/tickers",
    summary="Get basic information for multiple tickers",
    description=(
        "Accepts a JSON array of ticker symbols. Returns the latest available regular-market "
    ),
)
def get_tickers(
    symbols: Annotated[
        list_of(TickerSymbol, max_length=20),
        Body(description="Ticker symbols", examples=[["MSFT", "AAPL", "GOOG"]]),
    ],
    store: StoreDep,
) -> dict[str, TickerInfo]:
    symbol_list = list(dict.fromkeys(symbol.upper() for symbol in symbols))
    try:
        return get_tickers_info(symbol_list, store)
    except TickerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"No data found for ticker {exc}.") from exc


@app.get(
    "/instruments",
    summary="List instruments for database seeding",
    description=(
        "Paginate stocks, ETFs and mutual funds across yfinance-supported exchanges. "
        "Ordered by size descending: market cap for stocks, net assets for funds. "
    ),
)
def get_instruments(
    store: StoreDep,
    asset_class: Annotated[
        InstrumentClass, Query(alias="assetClass", description="Instrument type"),
    ] = InstrumentClass.EQUITY,
    offset: Annotated[int_range(ge=0, le=None), Query(description="Result offset; follow nextOffset")] = 0,
    limit: Annotated[int_range(le=250), Query(description="Maximum number of results")] = 250,
) -> InstrumentPage:
    return _get_instruments(asset_class, offset=offset, limit=limit, store=store)


@app.get(
    "/news",
    summary="Search news articles by query",
    description="Searches news articles.",
)
def search_news_by_query(
    store: StoreDep,
    query: Annotated[string(max_length=500), Query(description="News search query")] = "business",
    limit: Annotated[int_range(), Query(description="Maximum number of articles")] = 25,
) -> list[Article]:
    return _search_news(query, limit=limit, store=store)


@app.get(
    "/news/keywords",
    summary="Search news articles by keywords",
    description="Searches news articles for each keyword.",
)
def search_news_by_keywords(
    store: StoreDep,
    keywords: Annotated[list_of(string(), max_length=20), Query(description="News search keywords")],
    limit: Annotated[int_range(), Query(description="Maximum number of articles")] = 25,
) -> list[Article]:
    return _search_news_by_keywords(keywords, limit=limit, store=store)


@app.get(
    "/tickers/{symbol}/news",
    summary="Get news articles for a ticker",
    description="Returns the latest news articles for a ticker symbol.",
)
def get_ticker_news(
    symbol: TickerSymbol,
    store: StoreDep,
    limit: Annotated[int_range(), Query(description="Maximum number of articles")] = 10,
) -> list[Article]:
    return _get_ticker_news(symbol.upper(), limit=limit, store=store)


def main() -> None:
    uvicorn.run("yfinance_rest_mcp.api:app", host="127.0.0.1", port=8000)
