import yfinance as yf

from ..models import Article
from ..db.storage import PostgresStore
from .mappers.article_mapper import ArticleMapper
from .source import Source


class TickerNewsSource(Source[list[Article]], ArticleMapper):
    def __init__(
        self,
        symbol: str, limit: int = 10,
        store: PostgresStore | None = None,
    ) -> None:
        self.symbol = symbol
        self.limit = limit
        self.store = store

    def get_from_db(self) -> list[Article] | None:
        return None

    def get_from_yfinance(self) -> list[Article]:
        return self.map_all(yf.Ticker(self.symbol).get_news(count=self.limit) or [])
