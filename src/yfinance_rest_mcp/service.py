from datetime import UTC, datetime, timedelta

from .models import Article, InstrumentClass, InstrumentPage, TickerInfo
from .db.repository import save_articles, save_instruments, save_price, stored_articles
from .embedders.embedder import OpenRouterEmbedder
from .sources.instrument_source import InstrumentSource
from .sources.search_news_source import SearchNewsSource
from .sources.source import Source
from .sources.ticker_info_source import TickerInfoSource, TickerNotFoundError
from .sources.ticker_news_source import TickerNewsSource
from .db.storage import PostgresStore

__all__ = [
    "PRICE_TTL",
    "TickerNotFoundError",
    "get_instruments",
    "get_ticker_info",
    "get_ticker_news",
    "get_tickers_info",
    "search_news",
    "search_news_by_keywords",
    "stored_news",
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


def get_ticker_news(
    symbol: str, limit: int = 10,
    store: PostgresStore | None = None,
) -> list[Article]:
    articles = TickerNewsSource(symbol, limit).get_from_yfinance()

    if store is not None:
        save_articles(store, articles, embed_articles)
    return articles


def search_news(
    query: str, limit: int = 8,
    store: PostgresStore | None = None,
) -> list[Article]:
    articles = SearchNewsSource(query, limit).get_from_yfinance()

    if store is not None:
        save_articles(store, articles, embed_articles)
    return articles


def search_news_by_keywords(
    keywords: list[str], limit: int = 25,
    store: PostgresStore | None = None,
) -> list[Article]:
    articles: list[Article] = []
    seen: set[str] = set()

    for keyword in keywords:
        for article in search_news(keyword, limit=limit, store=store):
            key = article.external_id or article.url or article.title
            if key is not None and key not in seen:
                seen.add(key)
                articles.append(article)
    return articles[:limit]


def embed_articles(rows: dict[str, dict]) -> None:
    embedder = OpenRouterEmbedder.get()
    if not embedder.enabled:
        return

    texts = [
        "\n".join(part for part in (row["title"], row["description"]) if part)
        for row in rows.values()
    ]
    try:
        vectors = embedder.embed([text for text in texts if text])
    except Exception:
        return

    vector_iter = iter(vectors)
    
    for row, text in zip(rows.values(), texts, strict=True):
        if not text:
            continue
        row["embedding"] = next(vector_iter)
        row["embedding_model"] = embedder.model


def stored_news(
    store: PostgresStore | None, offset: int = 0, limit: int = 100,
) -> list[Article]:
    if store is None:
        return []
    return [
        Article(**row.model_dump()) for row in stored_articles(store, offset, limit)
    ]
