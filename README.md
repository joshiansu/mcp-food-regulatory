# mcp-food-regulatory

> An MCP server that gives AI agents structured access to food regulatory databases across global markets.

Built with [FastMCP](https://github.com/jlowin/fastmcp). Designed to be contributed to [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers).

---

## Why this exists

Food regulatory compliance is manual, painful, and market-specific. Checking whether a health claim is permitted in the EU, Philippines, Vietnam, and Australia currently requires a regulatory affairs specialist to open four different government websites, read PDFs, and synthesise results by hand.

This MCP server turns that into a single tool call any AI agent can make.

---

## Markets covered

| Market | Data source | Status |
|--------|-------------|--------|
| 🌍 **Codex Alimentarius** | FAO/WHO standards database | ✅ Implemented |
| 🇪🇺 **European Union** | EUR-Lex API + EC Health Claims Register | ✅ Implemented |
| 🇦🇺 **Australia / NZ** | FSANZ Food Standards Code | 🔜 Planned |
| 🇵🇭 **Philippines** | FDA Philippines | 🔜 Planned |
| 🇲🇾 **Malaysia** | MOH Malaysia / MySMERT | 🔜 Planned |
| 🇻🇳 **Vietnam** | MOH Vietnam QCVN | 🔜 Planned |
| 🇮🇩 **Indonesia** | BPOM | 🔜 Planned |
| 🇹🇭 **Thailand** | Thai FDA | 🔜 Planned |

---

## Tools exposed

```
search_health_claims(ingredient, markets)        → claim status per market
get_standard(standard_id, market)                → full standard text + metadata
search_standards(query, market)                  → keyword search across standards
get_additive_status(additive, food_category, market) → permitted levels + conditions
compare_markets(ingredient, claim_type, markets) → side-by-side regulatory comparison
get_market_overview(market)                      → summary of regulatory framework
```

---

## Quickstart

### Install

```bash
# Requires Python 3.10+
uv add mcp-food-regulatory

# Or from source
git clone https://github.com/YOUR_USERNAME/mcp-food-regulatory
cd mcp-food-regulatory
uv sync
```

### Run

```bash
# stdio (for Claude Desktop)
uv run mcp-food-regulatory

# HTTP (for agents / remote)
uv run mcp-food-regulatory --transport streamable-http --port 8000
```

### Add to Claude Desktop

```json
{
  "mcpServers": {
    "food-regulatory": {
      "command": "uv",
      "args": ["--directory", "/path/to/mcp-food-regulatory", "run", "mcp-food-regulatory"]
    }
  }
}
```

---

## Example agent interactions

```
Agent: "Is a caffeine + alertness health claim permitted in the EU?"
→ search_health_claims("caffeine", ["EU"])
→ Returns: Article 13.1 permitted claim, conditions, EFSA opinion reference

Agent: "Compare prebiotic claim status for inulin across PH, MY, VN, AU"
→ compare_markets("inulin", "prebiotic", ["PH", "MY", "VN", "AU"])
→ Returns: market-by-market table with status, conditions, regulatory basis

Agent: "What does Codex say about dietary fibre definition?"
→ get_standard("CXG 2-1985", "codex")
→ Returns: full standard metadata, definition text, amendment history
```

---

## Architecture

```
mcp_food_regulatory/
├── server.py           # FastMCP server, tool registration
├── models.py           # Pydantic models for regulatory data
├── cache.py            # TTL cache layer (avoids hammering public APIs)
└── sources/
    ├── codex.py        # FAO/WHO Codex Alimentarius
    ├── eu.py           # EUR-Lex API + EC Health Claims Register
    ├── fsanz.py        # Australia/NZ (planned)
    ├── ph_fda.py       # Philippines FDA (planned)
    └── base.py         # Abstract base class for all sources
```

---

## Contributing

Each new market is a new source file implementing `RegulatorySource`. See `sources/base.py` and `sources/codex.py` for the pattern.

PRs welcome, especially for:
- New market connectors (ASEAN markets particularly needed)
- Improving scraping robustness
- Adding caching strategies
- Test coverage

---

## License

Apache 2.0
