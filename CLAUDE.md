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
Batch 1 complete: Codex, EU, PH, JP, US, CA, AU implemented.
Next batch (Batch 2): br_anvisa.py, kr_mfds.py, sa_sfda.py