from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool
from yfinance.exceptions import YFRateLimitError

from .models import TickerInfo
from .service import TickerNotFoundError, get_tickers_info
from .storage import PostgresStore, create_store
from .validation import TickerSymbol


@dataclass
class MCPState:
    store: PostgresStore | None


@asynccontextmanager
async def lifespan(_server: MCPServer) -> AsyncIterator[MCPState]:
    store = await run_in_threadpool(create_store)
    try:
        yield MCPState(store=store)
    finally:
        if store is not None:
            await run_in_threadpool(store.close)


server = MCPServer("yfinance-port", lifespan=lifespan)


@server.tool(
    description=(
        "Get basic information for 1–20 known ticker symbols. Symbols are trimmed, "
        "uppercased, and deduplicated. Returns a symbol-keyed object with name, exchange, "
        "currency, latest available price, and priceTime (UTC source timestamp or null). "
    ),
    structured_output=True,
)
async def get_tickers(
    symbols: Annotated[
        list[TickerSymbol], Field(min_length=1, max_length=20, description="Ticker symbols"),
    ],
    ctx: Context[MCPState, None],
) -> dict[str, TickerInfo]:
    symbol_list = list(dict.fromkeys(symbol.upper() for symbol in symbols))
    store = ctx.request_context.lifespan_context.store
    try:
        return await run_in_threadpool(get_tickers_info, symbol_list, store)
    except TickerNotFoundError as exc:
        raise ToolError(f"No data found for ticker {exc}.") from exc
    except YFRateLimitError as exc:
        raise ToolError("Upstream rate limit reached. Try again later.") from exc
    except SQLAlchemyError as exc:
        raise ToolError("Unable to access data in PostgreSQL.") from exc
    except Exception as exc:
        raise ToolError("Unable to fetch ticker data.") from exc


def main() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
