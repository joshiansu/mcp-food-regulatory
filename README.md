# mcp-food-regulatory

> An MCP server that gives AI agents structured access to food regulatory databases across global markets.

Built with [FastMCP](https://github.com/jlowin/fastmcp). Designed to be contributed to [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers).

---

## Why this exists

Food regulatory compliance is manual, painful, and market-specific. Checking whether a health claim is permitted in the EU, Philippines, Vietnam, and Australia currently requires a regulatory affairs specialist to open four different government websites, read PDFs, and synthesise results by hand.

This MCP server turns that into a single tool call any AI agent can make.

---

## Markets covered

| Market | Authority | Status |
|--------|-----------|--------|
| 🌍 **Codex Alimentarius** | FAO/WHO | ✅ Live |
| 🇪🇺 **European Union** | EFSA / European Commission | ✅ Live |
| 🇺🇸 **United States** | US FDA | ✅ Live |
| 🇯🇵 **Japan** | Consumer Affairs Agency | ✅ Live |
| 🇨🇦 **Canada** | Health Canada / CFIA | ✅ Live |
| 🇦🇺 **Australia** | FSANZ | ✅ Live |
| 🇵🇭 **Philippines** | FDA Philippines | ✅ Live |
| 🇮🇳 **India** | FSSAI | ✅ Live |
| 🇨🇳 **China** | NHC / SAMR | ✅ Live |
| 🇰🇷 **South Korea** | MFDS | ✅ Live |
| 🇧🇷 **Brazil** | ANVISA | ✅ Live |
| 🇨🇴 **Colombia** | INVIMA | ✅ Live |
| 🇨🇱 **Chile** | MINSAL / ISP | ✅ Live |
| 🇲🇽 **Mexico** | COFEPRIS / SSA | ✅ Live |
| 🇦🇪 **UAE** | ESMA / Dubai Municipality | ✅ Live |
| 🇸🇦 **Saudi Arabia** | SFDA | ✅ Live |
| 🇿🇦 **South Africa** | Department of Health | ✅ Live |
| 🇲🇾 **Malaysia** | MOH Malaysia | 🔜 Planned |
| 🇻🇳 **Vietnam** | MOH Vietnam | 🔜 Planned |
| 🇮🇩 **Indonesia** | BPOM | 🔜 Planned |
| 🇹🇭 **Thailand** | Thai FDA | 🔜 Planned |
| 🇬🇧 **United Kingdom** | UK FSA | 🔜 Planned |

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

The server is deployed at `https://mcp-food-regulatory.vercel.app/mcp`. No local installation needed.

### Claude Desktop

Open **Settings → Developer → Edit Config** and add:

```json
{
  "mcpServers": {
    "food-regulatory": {
      "url": "https://mcp-food-regulatory.vercel.app/mcp"
    }
  }
}
```

Restart Claude. That's it.

### Cursor / Windsurf / Cline

Add the same block to `~/.cursor/mcp.json`, `~/.codeium/windsurf/mcp_config.json`, or your Cline MCP config.

### GitHub Copilot (VS Code)

VS Code uses a `"servers"` key instead of `"mcpServers"`. Create `.vscode/mcp.json`:

```json
{
  "servers": {
    "food-regulatory": {
      "url": "https://mcp-food-regulatory.vercel.app/mcp"
    }
  }
}
```

### Run locally (development)

```bash
git clone https://github.com/joshiansu/mcp-food-regulatory
cd mcp-food-regulatory
uv sync
uv run mcp-food-regulatory --transport streamable-http --port 8000
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
