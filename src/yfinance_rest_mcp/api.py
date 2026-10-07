from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

import uvicorn
from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool
from yfinance.exceptions import YFRateLimitError

from .models import InstrumentClass, InstrumentPage, TickerInfo
from .service import TickerNotFoundError, get_instruments, get_tickers_info
from .storage import PostgresStore, create_store
from .validation import TickerSymbol


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


@app.exception_handler(SQLAlchemyError)
def persistence_error_handler(_request: Request, _exc: SQLAlchemyError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": "Unable to persist data in PostgreSQL."})


@app.post(
    "/tickers",
    summary="Get basic information for multiple tickers",
    description=(
        "Accepts a JSON array of ticker symbols. Returns the latest available regular-market "
    ),
)
def get_tickers(
    symbols: Annotated[
        list[TickerSymbol],
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
            status_code=503, detail="Upstream rate limit reached. Try again later."
        ) from exc
    except SQLAlchemyError:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to fetch ticker data.") from exc


@app.get(
    "/instruments",
    summary="List instruments for database seeding",
    description=(
        "Paginate stocks, ETFs and mutual funds across yfinance-supported exchanges. "
        "Ordered by size descending: market cap for stocks, net assets for funds. "
    ),
)
def list_instruments(
    store: StoreDep,
    asset_class: Annotated[
        InstrumentClass, Query(alias="assetClass", description="Instrument type"),
    ] = InstrumentClass.EQUITY,
    offset: Annotated[int, Query(ge=0, description="Result offset; follow nextOffset")] = 0,
    limit: Annotated[int, Query(ge=1, le=250, description="Maximum number of results")] = 250,
) -> InstrumentPage:
    try:
        return get_instruments(asset_class, offset=offset, limit=limit, store=store)
    except YFRateLimitError as exc:
        raise HTTPException(
            status_code=503, detail="Upstream rate limit reached. Try again later."
        ) from exc
    except SQLAlchemyError:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to fetch instruments.") from exc


def main() -> None:
    uvicorn.run("yfinance_rest_mcp.api:app", host="127.0.0.1", port=8000)
