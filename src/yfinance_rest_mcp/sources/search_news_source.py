import yfinance as yf

from ..models import Article
from .mappers.article_mapper import ArticleMapper


class SearchNewsSource(ArticleMapper):
    def __init__(self, query: str, limit: int = 8) -> None:
        self.query = query
        self.limit = limit

    def get_from_yfinance(self) -> list[Article]:
        return self.map_all(yf.Search(self.query, news_count=self.limit).news or [])
