# yfinance-port

A self-hosted REST service built on yfinance, so projects in any language can access Yahoo Finance data and optionally persist what they retrieve.

## Run

```bash
uv sync
uv run yfinance-port
```

Settings are read from `.env` on startup. API documentation is available at `http://127.0.0.1:8000/docs`.

## PostgreSQL persistence

Persistence is disabled by default. To enable it, set `PERSIST_DATA=true` and add a strong `POSTGRES_PASSWORD` to your existing `.env`. See `.env.example` for connection settings; the default database and user are both `yfinance_port`.

```bash
docker compose up -d --wait db
uv run yfinance-port
```

Tables are created automatically on startup. Catalogue entries are updated by symbol, while each ticker-info fetch adds a price snapshot with its source time and recording time. Only requested data is stored; responses still come from yfinance, not from the database.

`PERSIST_DATA=false` runs without a database. The local PostgreSQL container is bound to localhost and uses a persistent Docker volume. Do not commit `.env` or remove the database volume unless you intend to lose its data. Restart the service after changing settings.

## Disclaimer

This is an independent, self-hosted service. It is not affiliated with or endorsed by Yahoo, yfinance's maintainers, or any data provider. The service and its data are provided as-is, without guarantees of accuracy, availability, or suitability. You are responsible for how you use the service and for complying with the terms that apply to the underlying data.
