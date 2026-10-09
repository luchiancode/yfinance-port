import yfinance as yf

from ..models import Article
from .mappers.article_mapper import ArticleMapper


class TickerNewsSource(ArticleMapper):
    def __init__(self, symbol: str, limit: int = 10) -> None:
        self.symbol = symbol
        self.limit = limit

    def get_from_yfinance(self) -> list[Article]:
        return self.map_all(yf.Ticker(self.symbol).get_news(count=self.limit) or [])
