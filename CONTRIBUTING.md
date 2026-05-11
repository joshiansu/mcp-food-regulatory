# Contributing to mcp-food-regulatory

The highest-value contribution is adding a new market connector. Each market is a single Python file. Here's exactly how to do it.

---

## Adding a new market connector

### 1. Copy the template

```bash
cp src/mcp_food_regulatory/sources/template.py \
   src/mcp_food_regulatory/sources/ph_fda.py
```

### 2. Implement the class

Open your new file and implement these 4 methods:

```python
class PHFDASource(RegulatorySource):
    market = Market.PH
    BASE_URL = "https://pfda.doh.gov.ph"

    async def search_health_claims(self, ingredient, claim_type=None) -> list[ClaimResult]:
        ...

    async def get_standard(self, standard_id) -> Standard | None:
        ...

    async def search_standards(self, query) -> list[Standard]:
        ...

    async def get_market_overview(self) -> MarketOverview:
        ...
```

### 3. Research the data sources

Before writing any code, research how the market stores its data:

| Market | Primary source | Access method |
|--------|---------------|---------------|
| Philippines | pfda.doh.gov.ph + Administrative Orders | Web scraping |
| Malaysia | mysmetinfo.moh.gov.my + Food Act 1983 | Web scraping |
| Vietnam | vfa.gov.vn + QCVN documents | PDF parsing + scraping |
| Indonesia | pom.go.id + BPOM regulations | Web scraping |
| Thailand | fda.moph.go.th | Web scraping |
| Australia/NZ | foodstandards.gov.au (FSANZ) | Structured website |

**Tip:** Start with seeded data for the 5-10 most common queries, then add live search as a fallback. See `codex.py` for this pattern.

### 4. Register in server.py

Add your source to the `SOURCES` dict:

```python
from mcp_food_regulatory.sources.ph_fda import PHFDASource

SOURCES = {
    Market.CODEX: CodexSource,
    Market.EU: EUSource,
    Market.PH: PHFDASource,   # ← add this
}
```

### 5. Add tests

Add a test class to `tests/test_sources.py`:

```python
class TestPHFDASource:
    @pytest.mark.asyncio
    async def test_market_is_ph(self, http_client):
        source = PHFDASource(http_client)
        assert source.market == Market.PH

    @pytest.mark.asyncio
    async def test_market_overview(self, http_client):
        source = PHFDASource(http_client)
        overview = await source.get_market_overview()
        assert overview.market == Market.PH
        assert overview.authority_name  # not empty
```

### 6. Update README.md

Change your market row in the table from `🔜 Planned` to `✅ Implemented`.

### 7. Open a PR

PR title format: `feat: add [Market] connector`

---

## Improving seed data

If you have domain expertise in a market, the best contribution is expanding the `_*_CLAIM_PROVISIONS` dicts in the source files with accurate, cited regulatory data. Each entry needs:

- `claim_type`: string identifier
- `status`: one of `permitted`, `prohibited`, `pending`, `not_defined`, `conditional`
- `conditions`: plain-English description of conditions
- `instrument`: official name of the regulation
- `url`: direct link to the primary legal text

---

## Code standards

- Python 3.10+
- Type hints on all functions
- Docstrings on all public methods
- `ruff` for linting: `uv run ruff check src/`
- Tests must pass: `uv run pytest tests/ -v`

---

## What we don't want

- Paid API integrations (must be publicly accessible data)
- Storing/caching copyrighted regulatory texts (links only)
- Presenting regulatory data as legal advice
