import yfinance as yf

from ..models import Article
from ..db.storage import PostgresStore
from .mappers.article_mapper import ArticleMapper
from .source import Source


class SearchNewsSource(Source[list[Article]], ArticleMapper):
    def __init__(
        self,
        query: str, limit: int = 8,
        store: PostgresStore | None = None,
    ) -> None:
        self.query = query
        self.limit = limit
        self.store = store

    def get_from_db(self) -> list[Article] | None:
        return None

    def get_from_yfinance(self) -> list[Article]:
        return self.map_all(yf.Search(self.query, news_count=self.limit).news or [])
