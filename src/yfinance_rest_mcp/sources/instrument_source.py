import yfinance as yf

from ..models import Instrument, InstrumentClass, InstrumentPage
from ..db.repository import instruments_page
from ..db.storage import PostgresStore
from .source import Source


class InstrumentSource(Source[InstrumentPage]):
    def __init__(
        self,
        asset_class: InstrumentClass, offset: int = 0, limit: int = 250,
        store: PostgresStore | None = None,
    ) -> None:
        self.asset_class = asset_class
        self.offset = offset
        self.limit = limit
        self.store = store

    def get_from_db(self) -> InstrumentPage | None:
        if self.store is None:
            return None
        rows, total = instruments_page(self.store, self.asset_class.value, self.offset, self.limit)
        if len(rows) == self.limit or (rows and self.offset + len(rows) >= total):
            next_offset = self.offset + len(rows)
            return InstrumentPage(
                items=[Instrument(**row.model_dump(exclude={"updated_at"})) for row in rows],
                total=total,
                offset=self.offset,
                next_offset=next_offset if next_offset < total else None,
            )
        return None

    def get_from_yfinance(self) -> InstrumentPage:
        asset_class = self.asset_class
        offset = self.offset
        limit = self.limit

        sort_field = "intradaymarketcap" if asset_class == InstrumentClass.EQUITY else "fundnetassets"

        query_type = {
            InstrumentClass.EQUITY: yf.EquityQuery,
            InstrumentClass.ETF: yf.ETFQuery,
            InstrumentClass.MUTUALFUND: yf.FundQuery,
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
            raise ValueError("Received an empty page before the end of the results.")

        items = []
        for quote in quotes:
            if not quote.get("symbol"):
                continue
            name = quote.get("longName") or quote.get("shortName")
            aliases = list(dict.fromkeys(
                alias for alias in (quote.get("longName"), quote.get("shortName"))
                if alias and alias != name and alias != quote["symbol"]
            ))
            items.append(Instrument(
                symbol=quote["symbol"],
                name=name,
                asset_class=(quote.get("quoteType") or asset_class.value).upper(),
                aliases=aliases,
                exchange=quote.get("exchange"),
                currency=quote.get("currency"),
                size=quote.get("marketCap") or quote.get("netAssets"),
            ))

        next_offset = offset + len(quotes)
        return InstrumentPage(
            items=items,
            total=total,
            offset=offset,
            next_offset=next_offset if next_offset < total else None,
        )
