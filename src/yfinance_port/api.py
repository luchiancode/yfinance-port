from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

import uvicorn
from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import StringConstraints
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool
from yfinance.exceptions import YFRateLimitError

from .models import CatalogueAssetClass, CataloguePage, TickerInfo
from .service import TickerNotFoundError, get_ticker_catalogue, get_tickers_info
from .storage import PostgresStore, create_store


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
    title="yfinance-port",
    description="An HTTP API for accessing Yahoo Finance data through yfinance.",
    lifespan=lifespan,
)


def get_store(request: Request) -> PostgresStore | None:
    return request.app.state.store


StoreDep = Annotated[PostgresStore | None, Depends(get_store)]


@app.exception_handler(SQLAlchemyError)
def persistence_error_handler(_request: Request, _exc: SQLAlchemyError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": "Unable to persist data in PostgreSQL."})


@app.post(
    "/tickers",
    summary="Get basic information for multiple tickers",
    description=(
        "Accepts a JSON array of ticker symbols. Returns the latest available regular-market "
        "price with priceTime as an ISO 8601 UTC source timestamp. priceTime is null if Yahoo "
        "provides no matching timestamp, including when price falls back to currentPrice."
    ),
)
def get_tickers(
    symbols: Annotated[
        list[Annotated[str, StringConstraints(
            strip_whitespace=True, min_length=1, max_length=500, pattern=r"^[^\s,]+$",
        )]],
        Body(min_length=1, max_length=20, description="Ticker symbols", examples=[["MSFT", "AAPL", "GOOG"]]),
    ],
    store: StoreDep,
) -> dict[str, TickerInfo]:
    symbol_list = list(dict.fromkeys(symbol.upper() for symbol in symbols))

    try:
        return get_tickers_info(symbol_list, store)
    except TickerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"No data found for ticker {exc}.") from exc
    except YFRateLimitError as exc:
        raise HTTPException(
            status_code=503, detail="Yahoo Finance rate limit reached. Try again later."
        ) from exc
    except SQLAlchemyError:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to fetch data from Yahoo Finance.") from exc


@app.get(
    "/tickers/catalogue",
    summary="List ticker catalogue entries for database seeding",
    description=(
        "Paginate stocks, ETFs and mutual funds across yfinance-supported exchanges. "
        "Ordered by size descending: market cap for stocks and crypto, net assets for funds. "
        "Records include Yahoo-native exchange and currency codes when available. "
        "Crypto uses Yahoo's predefined USD screener; only its first page is available, "
        "with truncated=true when more results exist. Futures, commodities, currencies "
        "and indices are not enumerated."
    ),
)
def get_catalogue(
    store: StoreDep,
    asset_class: Annotated[
        CatalogueAssetClass, Query(alias="assetClass", description="Yahoo instrument type"),
    ] = CatalogueAssetClass.EQUITY,
    offset: Annotated[int, Query(ge=0, description="Result offset; follow nextOffset")] = 0,
    limit: Annotated[int, Query(ge=1, le=250, description="Maximum number of results")] = 250,
) -> CataloguePage:
    if asset_class == CatalogueAssetClass.CRYPTOCURRENCY and offset != 0:
        raise HTTPException(
            status_code=422, detail="yfinance only supports offset 0 for the crypto screener."
        )
    try:
        return get_ticker_catalogue(asset_class, offset=offset, limit=limit, store=store)
    except YFRateLimitError as exc:
        raise HTTPException(
            status_code=503, detail="Yahoo Finance rate limit reached. Try again later."
        ) from exc
    except SQLAlchemyError:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to fetch the Yahoo Finance catalogue.") from exc


def main() -> None:
    uvicorn.run("yfinance_port.api:app", host="127.0.0.1", port=8000)
