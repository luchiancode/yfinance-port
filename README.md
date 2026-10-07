# yfinance-rest-and-mcp

A self-hosted REST and MCP service built on yfinance, so projects and AI tools in any language can access Yahoo Finance data and optionally persist what they retrieve.

## Run the REST API

```bash
uv sync
uv run yfinance-rest
```

Settings are read from `.env` on startup. API documentation is available at `http://127.0.0.1:8000/docs`.

## Run the MCP server

```bash
uv run yfinance-mcp
```

A stdio MCP server backed by the same service logic; the REST API does not need to be running.

Example MCP client configuration:

```json
{
  "mcpServers": {
    "yfinance-rest-mcp": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/yfinance-rest-and-mcp", "run", "yfinance-mcp"],
      "env": { "PERSIST_DATA": "false" }
    }
  }
}
```

Replace `/absolute/path/to/yfinance-rest-and-mcp` with the project path, and point `command` at the absolute `uv` executable if the client cannot find `uv` on its `PATH`. Remove the `env` override to use the project `.env` settings instead.

## PostgreSQL persistence

Persistence is disabled by default. To enable it, set `PERSIST_DATA=true` and add a strong `POSTGRES_PASSWORD` to your existing `.env`. See `.env.example` for connection settings; the default database and user are both `yfinance_port`.

```bash
docker compose up -d --wait db
uv run yfinance-rest
```

Tables are created automatically on startup. Instrument records are updated by symbol, while each ticker-info fetch adds a price snapshot with its source time and recording time. Only requested data is stored; responses still come from yfinance, not from the database.

`PERSIST_DATA=false` runs without a database. The local PostgreSQL container is bound to localhost and uses a persistent Docker volume. Do not commit `.env` or remove the database volume unless you intend to lose its data. Restart the service after changing settings.

## Disclaimer

This is an independent, self-hosted service. It is not affiliated with or endorsed by Yahoo, yfinance's maintainers, or any data provider. The service and its data are provided as-is, without guarantees of accuracy, availability, or suitability. You are responsible for how you use the service and for complying with the terms that apply to the underlying data.
