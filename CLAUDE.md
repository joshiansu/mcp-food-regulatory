# mcp-food-regulatory

MCP server for food regulatory data. FastMCP + Python 3.10+.

## Commands
- `uv run pytest tests/ -v` — run tests
- `uv run mcp-food-regulatory` — start server (stdio)
- `uv run ruff check src/` — lint

## Architecture
- `src/mcp_food_regulatory/server.py` — tool registration
- `src/mcp_food_regulatory/sources/` — one file per market
- Add markets by copying `sources/template.py` and registering in `SOURCES` dict in server.py

## Current status
All Excel markets implemented: codex, eu, ph, jp, us, ca, au (batch 1) +
in, cn, kr, br, co, cl, mx, ae, sa, za (batch 2+3).
17 markets total.