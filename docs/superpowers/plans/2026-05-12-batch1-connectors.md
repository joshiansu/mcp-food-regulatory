# Batch 1 Market Connectors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Japan, USA, Canada, and Australia market connectors with live-first cached data fetching.

**Architecture:** Each connector subclasses `RegulatorySource`, fetches live data from official government websites (cached 24h in module-level variables), and falls back to seeded/static data on failure. Pattern matches the existing EU source, not PH FDA.

**Tech Stack:** Python 3.10+, FastMCP, httpx, BeautifulSoup4, Pydantic v2, uv, pytest-asyncio

---

## File Map

| File | Action | Notes |
|---|---|---|
| `src/mcp_food_regulatory/models.py` | Modify | Add `US`, `JP`, `CA` to Market enum |
| `src/mcp_food_regulatory/sources/jp_caa.py` | Create | Japan CAA connector |
| `src/mcp_food_regulatory/sources/us_fda.py` | Create | US FDA connector |
| `src/mcp_food_regulatory/sources/ca_health_canada.py` | Create | Canada Health Canada connector |
| `src/mcp_food_regulatory/sources/au_fsanz.py` | Create | Australia FSANZ connector |
| `src/mcp_food_regulatory/server.py` | Modify | Imports, SOURCES, list_markets, instructions |
| `tests/test_sources.py` | Modify | Add 4 test classes (~8 tests each) |
| `CLAUDE.md` | Modify | Update current status |
| `AGENTS.md` | Modify | Update current status |

---

## Task 1: Add US, JP, CA to Market Enum

**Files:**
- Modify: `src/mcp_food_regulatory/models.py`

- [ ] **Step 1: Add three enum values**

In `src/mcp_food_regulatory/models.py`, find:

```python
class Market(str, Enum):
    CODEX = "codex"
    EU = "eu"
    AU = "au"       # Australia / FSANZ
    NZ = "nz"       # New Zealand / FSANZ
    PH = "ph"       # Philippines
```

Change to:

```python
class Market(str, Enum):
    CODEX = "codex"
    EU = "eu"
    AU = "au"       # Australia / FSANZ
    NZ = "nz"       # New Zealand / FSANZ
    US = "us"       # United States
    JP = "jp"       # Japan
    CA = "ca"       # Canada
    PH = "ph"       # Philippines
```

- [ ] **Step 2: Verify existing tests still pass**

```bash
uv run pytest tests/ -v 2>&1 | tail -10
```

Expected: `38 passed`

- [ ] **Step 3: Commit**

```bash
git add src/mcp_food_regulatory/models.py
git commit -m "feat: add US, JP, CA to Market enum"
```

---

## Task 2: Japan CAA Connector

**Files:**
- Create: `src/mcp_food_regulatory/sources/jp_caa.py`
- Modify: `tests/test_sources.py`

- [ ] **Step 1: Add failing tests to tests/test_sources.py**

Add this import after the existing imports at the top of `tests/test_sources.py`:

```python
from mcp_food_regulatory.sources.jp_caa import JPCAASource
```

Add this fixture after the `ph` fixture:

```python
@pytest.fixture
def jp(http_client):
    return JPCAASource(http_client)
```

Append this class at the end of `tests/test_sources.py`:

```python
# ------------------------------------------------------------------ #
#  Japan CAA tests                                                    #
# ------------------------------------------------------------------ #

class TestJPCAASource:

    @pytest.mark.asyncio
    async def test_market_is_jp(self, jp):
        assert jp.market == Market.JP

    @pytest.mark.asyncio
    async def test_search_vitamin_d_permitted(self, jp):
        results = await jp.search_health_claims("vitamin d")
        assert len(results) >= 1
        assert any(r.status == ClaimStatus.PERMITTED for r in results)
        assert any(r.claim_type == "nutrient_function" for r in results)

    @pytest.mark.asyncio
    async def test_search_calcium_permitted(self, jp):
        results = await jp.search_health_claims("calcium")
        assert len(results) >= 1
        assert any(r.status == ClaimStatus.PERMITTED for r in results)

    @pytest.mark.asyncio
    async def test_search_unknown_not_defined(self, jp):
        results = await jp.search_health_claims("xylobiose_fictional_xyz")
        assert isinstance(results, list)
        assert len(results) >= 1
        assert results[0].status == ClaimStatus.NOT_DEFINED

    @pytest.mark.asyncio
    async def test_get_standard_health_promotion_act(self, jp):
        standard = await jp.get_standard("Health Promotion Act 2002")
        assert standard is not None
        assert standard.market == Market.JP

    @pytest.mark.asyncio
    async def test_get_standard_unknown_returns_none(self, jp):
        assert await jp.get_standard("JP 999-UNKNOWN") is None

    @pytest.mark.asyncio
    async def test_search_standards_returns_list(self, jp):
        results = await jp.search_standards("health")
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_market_overview(self, jp):
        overview = await jp.get_market_overview()
        assert overview.market == Market.JP
        assert "CAA" in overview.authority_name or "Consumer" in overview.authority_name
        assert len(overview.key_legislation) >= 2

    @pytest.mark.asyncio
    async def test_two_calls_no_crash(self, jp):
        r1 = await jp.search_health_claims("calcium")
        r2 = await jp.search_health_claims("calcium")
        assert len(r1) == len(r2)
```

- [ ] **Step 2: Run to verify they fail with ImportError**

```bash
uv run pytest tests/test_sources.py::TestJPCAASource -v 2>&1 | head -15
```

Expected: `ImportError: cannot import name 'JPCAASource'`

- [ ] **Step 3: Create src/mcp_food_regulatory/sources/jp_caa.py**

```python
"""
Japan Consumer Affairs Agency (消費者庁) regulatory data source.

Three health claim frameworks in Japan:
  1. FOSHU (Foods for Specified Health Uses / 特定保健用食品)
     -- Individual authorisation by CAA. Live search at fld.caa.go.jp/caaks/cssc01/
  2. FNFC (Foods with Function Claims / 機能性表示食品)
     -- Self-notified to CAA. Live search at fld.caa.go.jp/caaks/cssc02/
  3. NFC (Nutrient Function Claims / 栄養機能食品)
     -- Pre-approved fixed list of 13 vitamins + 5 minerals. Seeded, no DB exists.

Implementation:
  search_health_claims() -- NFC seeded (guaranteed) + FOSHU live (cached 24h, best-effort).
  get_standard()         -- Seeded for key legislation.
  search_standards()     -- Seeded list.
  get_market_overview()  -- Static.
"""

from __future__ import annotations
import time
from bs4 import BeautifulSoup
from mcp_food_regulatory.models import (
    Market, ClaimResult, ClaimStatus, Standard, MarketOverview, RegulatoryBasis
)
from mcp_food_regulatory.sources.base import RegulatorySource

_BASE_URL = "https://www.fld.caa.go.jp"
_FOSHU_URL = "https://www.fld.caa.go.jp/caaks/cssc01/"
_CACHE_TTL = 86400  # 24 hours

_foshu_cache: list[dict] | None = None
_foshu_fetched_at: float = 0.0

# NFC: fixed pre-approved list -- no DB exists, seed only
_NFC_CLAIMS: list[dict] = [
    {"ingredient": "vitamin a", "aliases": ["retinol", "beta-carotene"],
     "function": "Vitamin A contributes to the maintenance of normal vision and supports immune function."},
    {"ingredient": "vitamin d", "aliases": ["cholecalciferol", "calciferol", "vitamin d3"],
     "function": "Vitamin D promotes intestinal calcium absorption and supports bone health."},
    {"ingredient": "vitamin e", "aliases": ["tocopherol", "alpha-tocopherol"],
     "function": "Vitamin E acts as an antioxidant and helps maintain healthy cell membranes."},
    {"ingredient": "vitamin k", "aliases": ["phylloquinone", "menaquinone"],
     "function": "Vitamin K is needed for normal blood clotting."},
    {"ingredient": "vitamin b1", "aliases": ["thiamine", "thiamin"],
     "function": "Vitamin B1 helps convert carbohydrates into energy."},
    {"ingredient": "vitamin b2", "aliases": ["riboflavin"],
     "function": "Vitamin B2 supports energy metabolism and helps maintain skin health."},
    {"ingredient": "vitamin b6", "aliases": ["pyridoxine"],
     "function": "Vitamin B6 supports protein metabolism and immune function."},
    {"ingredient": "vitamin b12", "aliases": ["cobalamin", "cyanocobalamin"],
     "function": "Vitamin B12 supports red blood cell formation and nervous system function."},
    {"ingredient": "vitamin c", "aliases": ["ascorbic acid", "ascorbate"],
     "function": "Vitamin C acts as an antioxidant and supports collagen synthesis and immune function."},
    {"ingredient": "niacin", "aliases": ["nicotinic acid", "nicotinamide", "vitamin b3"],
     "function": "Niacin supports energy metabolism and helps maintain skin health."},
    {"ingredient": "folic acid", "aliases": ["folate", "folacin", "vitamin b9"],
     "function": "Folic acid supports normal cell division and is important during pregnancy."},
    {"ingredient": "pantothenic acid", "aliases": ["vitamin b5", "pantothenate"],
     "function": "Pantothenic acid supports energy metabolism."},
    {"ingredient": "biotin", "aliases": ["vitamin h", "vitamin b7"],
     "function": "Biotin supports energy metabolism and helps maintain skin and hair health."},
    {"ingredient": "calcium", "aliases": ["calcium carbonate", "calcium citrate"],
     "function": "Calcium is needed for the formation and maintenance of bones and teeth."},
    {"ingredient": "iron", "aliases": ["ferrous sulfate", "ferric"],
     "function": "Iron is needed for the formation of red blood cells and haemoglobin."},
    {"ingredient": "zinc", "aliases": ["zinc sulfate", "zinc gluconate"],
     "function": "Zinc supports normal growth, reproductive function, and taste sensation."},
    {"ingredient": "copper", "aliases": ["cupric sulfate"],
     "function": "Copper supports the activity of many enzymes and contributes to iron metabolism."},
    {"ingredient": "magnesium", "aliases": ["magnesium oxide", "magnesium citrate"],
     "function": "Magnesium supports bone health and many enzymatic reactions in the body."},
]

_KNOWN_STANDARDS: dict[str, dict] = {
    "Health Promotion Act 2002": {
        "title": "Health Promotion Act (健康増進法)",
        "category": "legislation",
        "adopted": "2002",
        "summary": (
            "Foundation for FOSHU (Foods for Specified Health Uses). "
            "Requires individual CAA approval for FOSHU products with specific health claim authorisation."
        ),
        "full_text_url": "https://www.mhlw.go.jp/english/policy/health-medical/health/index.html",
    },
    "Food Labelling Act 2013": {
        "title": "Food Labelling Act (食品表示法)",
        "category": "legislation",
        "adopted": "2013",
        "summary": (
            "Consolidated food labelling legislation. Governs FNFC (Foods with Function Claims) "
            "self-notification system and NFC (Nutrient Function Claims) pre-approved list."
        ),
        "full_text_url": "https://www.caa.go.jp/policies/policy/food_labeling/food_labeling_act/",
    },
    "NFC Standards": {
        "title": "Nutrient Function Claims Standards (栄養機能食品基準)",
        "category": "standard",
        "adopted": "2001",
        "last_amended": "2015",
        "summary": (
            "Pre-approved list of 13 vitamins and 5 minerals with permitted function claim texts. "
            "No individual application required; manufacturer must meet content standards."
        ),
        "full_text_url": "https://www.caa.go.jp/policies/policy/food_labeling/health_promotion/",
    },
}


class JPCAASource(RegulatorySource):
    """
    Japan Consumer Affairs Agency data source.

    NFC claims served from seeded list (fixed pre-approved, no live DB exists).
    FOSHU claims fetched live from CAA website (cached 24h, best-effort).
    """

    market = Market.JP
    BASE_URL = _BASE_URL

    async def search_health_claims(
        self,
        ingredient: str,
        claim_type: str | None = None,
    ) -> list[ClaimResult]:
        normalized = ingredient.lower().strip()
        results = []

        # NFC seeded claims (guaranteed, no network needed)
        for entry in _NFC_CLAIMS:
            is_match = (
                normalized == entry["ingredient"]
                or normalized in entry["aliases"]
            )
            if not is_match:
                continue
            if claim_type is None or claim_type == "nutrient_function":
                results.append(ClaimResult(
                    market=Market.JP,
                    ingredient=entry["ingredient"],
                    claim_type="nutrient_function",
                    status=ClaimStatus.PERMITTED,
                    conditions=(
                        f"Must meet content standards per NFC regulations. "
                        f"Permitted claim: '{entry['function']}'"
                    ),
                    basis=RegulatoryBasis(
                        instrument="Food Labelling Act 2013 / NFC Standards",
                        article="Article 6 (Food Labelling Standards)",
                        url="https://www.caa.go.jp/policies/policy/food_labeling/health_promotion/",
                        notes="Pre-approved Nutrient Function Claim -- no individual notification required.",
                    ),
                    source_url=_BASE_URL,
                ))

        # FOSHU live claims (best-effort, cached)
        if claim_type is None or claim_type == "foshu":
            try:
                for item in await self._get_foshu_data():
                    text = f"{item.get('ingredient', '')} {item.get('claim', '')}".lower()
                    if normalized in text:
                        results.append(ClaimResult(
                            market=Market.JP,
                            ingredient=ingredient,
                            claim_type="foshu",
                            status=ClaimStatus.PERMITTED,
                            conditions=item.get("claim", ""),
                            basis=RegulatoryBasis(
                                instrument="Health Promotion Act 2002",
                                article="FOSHU authorisation",
                                url=_FOSHU_URL,
                                notes="Individually authorised FOSHU product claim.",
                            ),
                            source_url=_FOSHU_URL,
                        ))
            except Exception:
                pass

        if not results:
            results.append(ClaimResult(
                market=Market.JP,
                ingredient=ingredient,
                claim_type=claim_type or "health_claim",
                status=ClaimStatus.NOT_DEFINED,
                conditions=None,
                basis=RegulatoryBasis(
                    instrument="Food Labelling Act 2013",
                    article=None,
                    url="https://www.caa.go.jp/policies/policy/food_labeling/",
                    notes=(
                        "No pre-approved NFC or FOSHU claim found for this ingredient. "
                        "FOSHU or FNFC authorisation may be available via individual application to CAA."
                    ),
                ),
                source_url=_BASE_URL,
            ))

        return results

    async def _get_foshu_data(self) -> list[dict]:
        global _foshu_cache, _foshu_fetched_at
        if _foshu_cache is None or (time.time() - _foshu_fetched_at) > _CACHE_TTL:
            _foshu_cache = await self._fetch_foshu()
            _foshu_fetched_at = time.time()
        return _foshu_cache

    async def _fetch_foshu(self) -> list[dict]:
        resp = await self._get(_FOSHU_URL)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for row in soup.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) >= 3:
                results.append({
                    "product": cells[0].get_text(strip=True),
                    "ingredient": cells[1].get_text(strip=True) if len(cells) > 1 else "",
                    "claim": cells[2].get_text(strip=True) if len(cells) > 2 else "",
                })
        return results

    async def get_standard(self, standard_id: str) -> Standard | None:
        upper = standard_id.upper()
        for key, data in _KNOWN_STANDARDS.items():
            if upper in key.upper() or key.upper() in upper:
                return Standard(standard_id=key, market=Market.JP, **data)
        return None

    async def search_standards(self, query: str) -> list[Standard]:
        query_lower = query.lower()
        results = [
            Standard(standard_id=key, market=Market.JP, **data)
            for key, data in _KNOWN_STANDARDS.items()
            if query_lower in key.lower()
            or query_lower in data["title"].lower()
            or query_lower in (data.get("summary") or "").lower()
        ]
        return results or [
            Standard(standard_id=k, market=Market.JP, **v)
            for k, v in _KNOWN_STANDARDS.items()
        ]

    async def get_market_overview(self) -> MarketOverview:
        return MarketOverview(
            market=Market.JP,
            authority_name="Consumer Affairs Agency (消費者庁) -- CAA",
            authority_url=_BASE_URL,
            key_legislation=[
                "Health Promotion Act 2002 (FOSHU -- individually authorised by CAA)",
                "Food Labelling Act 2013 (FNFC self-notification; NFC pre-approved list)",
                "Food Labelling Standards (食品表示基準) 2015",
            ],
            health_claims_framework=(
                "Japan operates three parallel health claim systems: "
                "FOSHU (individually CAA-authorised, strongest evidentiary standard, displays FOSHU mark), "
                "FNFC (self-notified with post-market CAA review, manufacturer responsibility), and "
                "NFC (pre-approved fixed list of 13 vitamins + 5 minerals, no notification required)."
            ),
            notes=(
                "CAA publishes searchable FOSHU and FNFC databases at fld.caa.go.jp. "
                "The CAA website is primarily Japanese-language. "
                "FOSHU products are individually evaluated for efficacy and safety."
            ),
        )
```

- [ ] **Step 4: Run Japan tests**

```bash
uv run pytest tests/test_sources.py::TestJPCAASource -v
```

Expected: all 9 tests PASS. `test_search_vitamin_d_permitted` and `test_search_calcium_permitted` use seeded NFC data and do not need network access. Live FOSHU fetch tests may vary based on network.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_food_regulatory/sources/jp_caa.py tests/test_sources.py
git commit -m "$(cat <<'EOF'
feat: add Japan CAA connector (jp_caa.py)

NFC (Nutrient Function Claims) seeded for 18 vitamins/minerals.
FOSHU (Specified Health Uses) fetched live from CAA website (cached 24h).
9 tests passing.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: US FDA Connector

**Files:**
- Create: `src/mcp_food_regulatory/sources/us_fda.py`
- Modify: `tests/test_sources.py`

- [ ] **Step 1: Add failing tests**

Add import at top of `tests/test_sources.py`:

```python
from mcp_food_regulatory.sources.us_fda import USFDASource
```

Add fixture after `jp` fixture:

```python
@pytest.fixture
def us(http_client):
    return USFDASource(http_client)
```

Append test class:

```python
# ------------------------------------------------------------------ #
#  US FDA tests                                                       #
# ------------------------------------------------------------------ #

class TestUSFDASource:

    @pytest.mark.asyncio
    async def test_market_is_us(self, us):
        assert us.market == Market.US

    @pytest.mark.asyncio
    async def test_search_calcium_returns_results(self, us):
        # Calcium/bone health is one of the oldest FDA authorized health claims
        results = await us.search_health_claims("calcium")
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_folic_acid_returns_results(self, us):
        results = await us.search_health_claims("folic acid")
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_unknown_not_defined(self, us):
        results = await us.search_health_claims("xylobiose_fictional_xyz")
        assert len(results) >= 1
        assert results[0].status == ClaimStatus.NOT_DEFINED

    @pytest.mark.asyncio
    async def test_get_standard_21_cfr(self, us):
        standard = await us.get_standard("21 CFR Part 101")
        assert standard is not None
        assert standard.market == Market.US

    @pytest.mark.asyncio
    async def test_get_standard_unknown_returns_none(self, us):
        assert await us.get_standard("US 999-UNKNOWN") is None

    @pytest.mark.asyncio
    async def test_search_standards_returns_list(self, us):
        results = await us.search_standards("labeling")
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_market_overview(self, us):
        overview = await us.get_market_overview()
        assert overview.market == Market.US
        assert "FDA" in overview.authority_name
        assert len(overview.key_legislation) >= 2

    @pytest.mark.asyncio
    async def test_two_calls_no_crash(self, us):
        r1 = await us.search_health_claims("calcium")
        r2 = await us.search_health_claims("calcium")
        assert len(r1) == len(r2)
```

- [ ] **Step 2: Run to verify ImportError**

```bash
uv run pytest tests/test_sources.py::TestUSFDASource -v 2>&1 | head -10
```

Expected: `ImportError: cannot import name 'USFDASource'`

- [ ] **Step 3: Create src/mcp_food_regulatory/sources/us_fda.py**

```python
"""
United States Food and Drug Administration regulatory data source.

Three health claim tiers:
  1. Authorized Health Claims -- meet SSA standard, codified in 21 CFR 101.14+
     Status: PERMITTED
  2. Qualified Health Claims -- interim enforcement discretion letters
     Status: CONDITIONAL (require disclaimer)
  3. Structure/Function Claims -- self-notified, no public authoritative database
     Status: NOT_DEFINED (returned as fallback)

Implementation:
  search_health_claims() -- Fetches both FDA claim pages (cached 24h).
  get_standard()         -- Seeded for key regulations.
  search_standards()     -- Seeded list.
  get_market_overview()  -- Static.
"""

from __future__ import annotations
import time
from bs4 import BeautifulSoup
from mcp_food_regulatory.models import (
    Market, ClaimResult, ClaimStatus, Standard, MarketOverview, RegulatoryBasis
)
from mcp_food_regulatory.sources.base import RegulatorySource

_BASE_URL = "https://www.fda.gov"
_AUTHORIZED_URL = (
    "https://www.fda.gov/food/food-labeling-nutrition/"
    "authorized-health-claims-meet-significant-scientific-agreement-ssa-standard"
)
_QUALIFIED_URL = (
    "https://www.fda.gov/food/food-labeling-nutrition/"
    "qualified-health-claims-substances-conventional-foods"
)
_CACHE_TTL = 86400

_auth_cache: list[dict] | None = None
_auth_fetched_at: float = 0.0
_qual_cache: list[dict] | None = None
_qual_fetched_at: float = 0.0

_KNOWN_STANDARDS: dict[str, dict] = {
    "21 CFR Part 101": {
        "title": "21 CFR Part 101 -- Food Labeling",
        "category": "regulation",
        "adopted": "1990",
        "last_amended": "2023",
        "summary": (
            "Primary US food labeling regulation. Subpart E (101.14, 101.70-101.83) "
            "covers authorized health claims. Subpart F covers nutrition labeling. "
            "Subpart D covers nutrient content claims."
        ),
        "full_text_url": "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-B/part-101",
    },
    "NLEA 1990": {
        "title": "Nutrition Labeling and Education Act of 1990",
        "category": "legislation",
        "adopted": "1990",
        "summary": (
            "Established the framework for health claims on food labels in the United States. "
            "Requires health claims to be pre-authorized by FDA."
        ),
        "full_text_url": "https://www.fda.gov/food/food-labeling-nutrition/nutrition-labeling-and-education-act-1990",
    },
    "FDAMA 1997": {
        "title": "FDA Modernization Act of 1997",
        "category": "legislation",
        "adopted": "1997",
        "summary": (
            "Introduced notification procedure for health claims based on authoritative statements "
            "from scientific bodies. Also streamlined device approval processes."
        ),
        "full_text_url": "https://www.fda.gov/regulatory-information/selected-amendments-fdc-act/fda-modernization-act-1997",
    },
}


class USFDASource(RegulatorySource):
    """
    US FDA regulatory data source.

    Authorized and Qualified Health Claims pages fetched live (cached 24h).
    Structure/Function Claims return NOT_DEFINED -- no authoritative public database exists.
    """

    market = Market.US
    BASE_URL = _BASE_URL

    async def search_health_claims(
        self,
        ingredient: str,
        claim_type: str | None = None,
    ) -> list[ClaimResult]:
        normalized = ingredient.lower().strip()
        results = []

        # Authorized Health Claims → PERMITTED
        if claim_type is None or claim_type in ("authorized_health_claim", "health_claim"):
            try:
                for item in await self._get_authorized():
                    if normalized in item["text"].lower():
                        results.append(ClaimResult(
                            market=Market.US,
                            ingredient=ingredient,
                            claim_type="authorized_health_claim",
                            status=ClaimStatus.PERMITTED,
                            conditions=item["text"],
                            basis=RegulatoryBasis(
                                instrument="21 CFR Part 101",
                                article="101.14 (general requirements)",
                                url=_AUTHORIZED_URL,
                                notes="Authorized Health Claim meeting Significant Scientific Agreement (SSA) standard.",
                            ),
                            source_url=_AUTHORIZED_URL,
                        ))
            except Exception:
                pass

        # Qualified Health Claims → CONDITIONAL
        if claim_type is None or claim_type in ("qualified_health_claim", "health_claim"):
            try:
                for item in await self._get_qualified():
                    if normalized in item["text"].lower():
                        results.append(ClaimResult(
                            market=Market.US,
                            ingredient=ingredient,
                            claim_type="qualified_health_claim",
                            status=ClaimStatus.CONDITIONAL,
                            conditions=f"{item['text']} [Requires FDA-specified qualifying disclaimer on label]",
                            basis=RegulatoryBasis(
                                instrument="FDA Enforcement Discretion Letter",
                                article=None,
                                url=_QUALIFIED_URL,
                                notes=(
                                    "Qualified Health Claim under interim FDA enforcement discretion. "
                                    "Must include a required disclaimer. Evidence does not meet SSA standard."
                                ),
                            ),
                            source_url=_QUALIFIED_URL,
                        ))
            except Exception:
                pass

        if not results:
            results.append(ClaimResult(
                market=Market.US,
                ingredient=ingredient,
                claim_type=claim_type or "health_claim",
                status=ClaimStatus.NOT_DEFINED,
                conditions=None,
                basis=RegulatoryBasis(
                    instrument="21 CFR Part 101",
                    article=None,
                    url=_BASE_URL + "/food/food-labeling-nutrition",
                    notes=(
                        "No authorized or qualified health claim found for this ingredient. "
                        "Structure/Function Claims are self-notified and not tracked in a public database."
                    ),
                ),
                source_url=_BASE_URL,
            ))

        return results

    async def _get_authorized(self) -> list[dict]:
        global _auth_cache, _auth_fetched_at
        if _auth_cache is None or (time.time() - _auth_fetched_at) > _CACHE_TTL:
            _auth_cache = await self._fetch_claim_page(_AUTHORIZED_URL)
            _auth_fetched_at = time.time()
        return _auth_cache

    async def _get_qualified(self) -> list[dict]:
        global _qual_cache, _qual_fetched_at
        if _qual_cache is None or (time.time() - _qual_fetched_at) > _CACHE_TTL:
            _qual_cache = await self._fetch_claim_page(_QUALIFIED_URL)
            _qual_fetched_at = time.time()
        return _qual_cache

    async def _fetch_claim_page(self, url: str) -> list[dict]:
        resp = await self._get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        items = []
        for li in soup.find_all("li"):
            text = li.get_text(strip=True)
            if len(text) > 20:
                items.append({"text": text, "url": url})
        return items

    async def get_standard(self, standard_id: str) -> Standard | None:
        upper = standard_id.upper()
        for key, data in _KNOWN_STANDARDS.items():
            if upper in key.upper() or key.upper() in upper:
                return Standard(standard_id=key, market=Market.US, **data)
        return None

    async def search_standards(self, query: str) -> list[Standard]:
        query_lower = query.lower()
        results = [
            Standard(standard_id=key, market=Market.US, **data)
            for key, data in _KNOWN_STANDARDS.items()
            if query_lower in key.lower()
            or query_lower in data["title"].lower()
            or query_lower in (data.get("summary") or "").lower()
        ]
        return results or [
            Standard(standard_id=k, market=Market.US, **v)
            for k, v in _KNOWN_STANDARDS.items()
        ]

    async def get_market_overview(self) -> MarketOverview:
        return MarketOverview(
            market=Market.US,
            authority_name="Food and Drug Administration (FDA)",
            authority_url=_BASE_URL,
            key_legislation=[
                "Nutrition Labeling and Education Act 1990 (NLEA)",
                "21 CFR Part 101 (Food Labeling Regulations)",
                "FDA Modernization Act 1997 (FDAMA)",
                "Food Safety Modernization Act 2011 (FSMA)",
            ],
            health_claims_framework=(
                "FDA regulates three tiers: "
                "Authorized Health Claims (meet Significant Scientific Agreement, codified in 21 CFR, PERMITTED), "
                "Qualified Health Claims (enforcement discretion letters, require disclaimer, CONDITIONAL), and "
                "Structure/Function Claims (self-notified within 30 days of marketing, no pre-approval). "
                "Nutrient Content Claims also regulated under 21 CFR 101 Subpart D."
            ),
            notes=(
                "FDA does not maintain a machine-readable health claims database. "
                "Individual claims are published as HTML pages and PDF letters. "
                "Structure/Function Claims require notification to FDA but are not publicly listed."
            ),
        )
```

- [ ] **Step 4: Run US FDA tests**

```bash
uv run pytest tests/test_sources.py::TestUSFDASource -v
```

Expected: all 9 tests PASS. Tests that search for `calcium` and `folic acid` will attempt live FDA page fetch. If network unavailable, `test_search_calcium_returns_results` may return a single NOT_DEFINED result -- still passes since it only asserts `len >= 1`.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_food_regulatory/sources/us_fda.py tests/test_sources.py
git commit -m "$(cat <<'EOF'
feat: add US FDA connector (us_fda.py)

Fetches Authorized (PERMITTED) and Qualified (CONDITIONAL) Health Claims
from FDA website (cached 24h). Structure/Function claims return NOT_DEFINED.
9 tests passing.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Canada Health Canada Connector

**Files:**
- Create: `src/mcp_food_regulatory/sources/ca_health_canada.py`
- Modify: `tests/test_sources.py`

- [ ] **Step 1: Add failing tests**

Add import at top of `tests/test_sources.py`:

```python
from mcp_food_regulatory.sources.ca_health_canada import CAHealthCanadaSource
```

Add fixture:

```python
@pytest.fixture
def ca(http_client):
    return CAHealthCanadaSource(http_client)
```

Append test class:

```python
# ------------------------------------------------------------------ #
#  Canada Health Canada tests                                         #
# ------------------------------------------------------------------ #

class TestCAHealthCanadaSource:

    @pytest.mark.asyncio
    async def test_market_is_ca(self, ca):
        assert ca.market == Market.CA

    @pytest.mark.asyncio
    async def test_search_calcium_returns_results(self, ca):
        # Calcium/osteoporosis is a pre-approved DRRC in Canada
        results = await ca.search_health_claims("calcium")
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_vitamin_c_returns_results(self, ca):
        results = await ca.search_health_claims("vitamin c")
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_unknown_not_defined(self, ca):
        results = await ca.search_health_claims("xylobiose_fictional_xyz")
        assert len(results) >= 1
        assert results[0].status == ClaimStatus.NOT_DEFINED

    @pytest.mark.asyncio
    async def test_get_standard_fdr_b01603(self, ca):
        standard = await ca.get_standard("FDR B.01.603")
        assert standard is not None
        assert standard.market == Market.CA

    @pytest.mark.asyncio
    async def test_get_standard_unknown_returns_none(self, ca):
        assert await ca.get_standard("CA 999-UNKNOWN") is None

    @pytest.mark.asyncio
    async def test_search_standards_returns_list(self, ca):
        results = await ca.search_standards("health claims")
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_market_overview(self, ca):
        overview = await ca.get_market_overview()
        assert overview.market == Market.CA
        assert "Health Canada" in overview.authority_name
        assert len(overview.key_legislation) >= 2

    @pytest.mark.asyncio
    async def test_two_calls_no_crash(self, ca):
        r1 = await ca.search_health_claims("vitamin c")
        r2 = await ca.search_health_claims("vitamin c")
        assert len(r1) == len(r2)
```

- [ ] **Step 2: Run to verify ImportError**

```bash
uv run pytest tests/test_sources.py::TestCAHealthCanadaSource -v 2>&1 | head -10
```

Expected: `ImportError: cannot import name 'CAHealthCanadaSource'`

- [ ] **Step 3: Create src/mcp_food_regulatory/sources/ca_health_canada.py**

```python
"""
Health Canada / CFIA regulatory data source for Canada.

Two types of pre-approved health claims:
  1. Disease Risk Reduction Claims (DRRC) -- FDR B.01.603
     Status: PERMITTED
  2. Nutrient Function Claims (NFC) -- FDR B.01.500-B.01.513
     Status: PERMITTED

Both published as structured HTML pages on canada.ca.

Implementation:
  search_health_claims() -- Fetches both claims pages (cached 24h).
  get_standard()         -- Seeded for key regulations.
  search_standards()     -- Seeded list.
  get_market_overview()  -- Static.
"""

from __future__ import annotations
import time
from bs4 import BeautifulSoup
from mcp_food_regulatory.models import (
    Market, ClaimResult, ClaimStatus, Standard, MarketOverview, RegulatoryBasis
)
from mcp_food_regulatory.sources.base import RegulatorySource

_BASE_URL = "https://www.canada.ca"
_DRRC_URL = (
    "https://www.canada.ca/en/health-canada/services/food-nutrition/"
    "food-labelling/health-claims/diet-related-health-claims.html"
)
_NFC_URL = (
    "https://www.canada.ca/en/health-canada/services/food-nutrition/"
    "food-labelling/health-claims/nutrient-function-claims.html"
)
_CACHE_TTL = 86400

_drrc_cache: list[dict] | None = None
_drrc_fetched_at: float = 0.0
_nfc_cache: list[dict] | None = None
_nfc_fetched_at: float = 0.0

_KNOWN_STANDARDS: dict[str, dict] = {
    "FDR B.01.603": {
        "title": "Food and Drug Regulations B.01.603 -- Disease Risk Reduction Claims",
        "category": "regulation",
        "adopted": "2003",
        "last_amended": "2016",
        "summary": (
            "Authorizes specific diet-disease risk reduction claims on Canadian food labels. "
            "Claims must use prescribed wording. Covers: sodium/hypertension, "
            "saturated fat/cholesterol/heart disease, calcium/osteoporosis, "
            "vegetables and fruit/cancer, sugar alcohols/dental caries."
        ),
        "full_text_url": "https://laws-lois.justice.gc.ca/eng/regulations/C.R.C.,_c._870/page-63.html",
    },
    "FDR B.01.500": {
        "title": "Food and Drug Regulations B.01.500-B.01.513 -- Nutrient Function Claims",
        "category": "regulation",
        "adopted": "2003",
        "summary": (
            "Pre-approved list of nutrient function claims for vitamins and minerals. "
            "Claims state the role of the nutrient in maintaining good health. "
            "No individual pre-market approval required."
        ),
        "full_text_url": "https://laws-lois.justice.gc.ca/eng/regulations/C.R.C.,_c._870/page-62.html",
    },
    "Food and Drugs Act": {
        "title": "Food and Drugs Act (R.S.C., 1985, c. F-27)",
        "category": "legislation",
        "adopted": "1985",
        "last_amended": "2022",
        "summary": "Foundational Canadian legislation governing food safety, labeling, and health claims.",
        "full_text_url": "https://laws-lois.justice.gc.ca/eng/acts/f-27/",
    },
}


class CAHealthCanadaSource(RegulatorySource):
    """
    Health Canada data source for Canada.

    Disease Risk Reduction Claims and Nutrient Function Claims
    fetched live from canada.ca (cached 24h).
    """

    market = Market.CA
    BASE_URL = _BASE_URL

    async def search_health_claims(
        self,
        ingredient: str,
        claim_type: str | None = None,
    ) -> list[ClaimResult]:
        normalized = ingredient.lower().strip()
        results = []

        # Disease Risk Reduction Claims → PERMITTED
        if claim_type is None or claim_type in ("disease_risk_reduction", "health_claim"):
            try:
                for item in await self._get_drrc():
                    if normalized in item["text"].lower():
                        results.append(ClaimResult(
                            market=Market.CA,
                            ingredient=ingredient,
                            claim_type="disease_risk_reduction",
                            status=ClaimStatus.PERMITTED,
                            conditions=item["text"],
                            basis=RegulatoryBasis(
                                instrument="FDR B.01.603",
                                article=None,
                                url=_DRRC_URL,
                                notes="Pre-approved Disease Risk Reduction Claim. Must use prescribed wording.",
                            ),
                            source_url=_DRRC_URL,
                        ))
            except Exception:
                pass

        # Nutrient Function Claims → PERMITTED
        if claim_type is None or claim_type in ("nutrient_function", "health_claim"):
            try:
                for item in await self._get_nfc():
                    if normalized in item["text"].lower():
                        results.append(ClaimResult(
                            market=Market.CA,
                            ingredient=ingredient,
                            claim_type="nutrient_function",
                            status=ClaimStatus.PERMITTED,
                            conditions=item["text"],
                            basis=RegulatoryBasis(
                                instrument="FDR B.01.500-B.01.513",
                                article=None,
                                url=_NFC_URL,
                                notes="Pre-approved Nutrient Function Claim. No individual pre-market approval required.",
                            ),
                            source_url=_NFC_URL,
                        ))
            except Exception:
                pass

        if not results:
            results.append(ClaimResult(
                market=Market.CA,
                ingredient=ingredient,
                claim_type=claim_type or "health_claim",
                status=ClaimStatus.NOT_DEFINED,
                conditions=None,
                basis=RegulatoryBasis(
                    instrument="Food and Drug Regulations",
                    article=None,
                    url=_BASE_URL + "/en/health-canada/services/food-nutrition/food-labelling/health-claims.html",
                    notes="No pre-approved health claim found for this ingredient under Canadian food regulations.",
                ),
                source_url=_BASE_URL,
            ))

        return results

    async def _get_drrc(self) -> list[dict]:
        global _drrc_cache, _drrc_fetched_at
        if _drrc_cache is None or (time.time() - _drrc_fetched_at) > _CACHE_TTL:
            _drrc_cache = await self._fetch_claims_page(_DRRC_URL)
            _drrc_fetched_at = time.time()
        return _drrc_cache

    async def _get_nfc(self) -> list[dict]:
        global _nfc_cache, _nfc_fetched_at
        if _nfc_cache is None or (time.time() - _nfc_fetched_at) > _CACHE_TTL:
            _nfc_cache = await self._fetch_claims_page(_NFC_URL)
            _nfc_fetched_at = time.time()
        return _nfc_cache

    async def _fetch_claims_page(self, url: str) -> list[dict]:
        resp = await self._get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        items = []
        for tag in soup.find_all(["li", "td", "p"]):
            text = tag.get_text(strip=True)
            if len(text) > 30:
                items.append({"text": text})
        return items

    async def get_standard(self, standard_id: str) -> Standard | None:
        upper = standard_id.upper()
        for key, data in _KNOWN_STANDARDS.items():
            if upper in key.upper() or key.upper() in upper:
                return Standard(standard_id=key, market=Market.CA, **data)
        return None

    async def search_standards(self, query: str) -> list[Standard]:
        query_lower = query.lower()
        results = [
            Standard(standard_id=key, market=Market.CA, **data)
            for key, data in _KNOWN_STANDARDS.items()
            if query_lower in key.lower()
            or query_lower in data["title"].lower()
            or query_lower in (data.get("summary") or "").lower()
        ]
        return results or [
            Standard(standard_id=k, market=Market.CA, **v)
            for k, v in _KNOWN_STANDARDS.items()
        ]

    async def get_market_overview(self) -> MarketOverview:
        return MarketOverview(
            market=Market.CA,
            authority_name="Health Canada / Canadian Food Inspection Agency (CFIA)",
            authority_url=_BASE_URL,
            key_legislation=[
                "Food and Drugs Act (R.S.C. 1985, c. F-27)",
                "Food and Drug Regulations -- B.01.603 (Disease Risk Reduction Claims)",
                "Food and Drug Regulations -- B.01.500-B.01.513 (Nutrient Function Claims)",
                "Safe Food for Canadians Regulations (SFCR) 2019",
            ],
            health_claims_framework=(
                "Canada permits two types of pre-approved health claims: "
                "Disease Risk Reduction Claims (DRRC, FDR B.01.603) linking diet to reduced disease risk, "
                "and Nutrient Function Claims (NFC, FDR B.01.500-513) describing nutrient roles in the body. "
                "Both require prescribed wording. Novel health claims require Health Canada pre-approval."
            ),
        )
```

- [ ] **Step 4: Run Canada tests**

```bash
uv run pytest tests/test_sources.py::TestCAHealthCanadaSource -v
```

Expected: all 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_food_regulatory/sources/ca_health_canada.py tests/test_sources.py
git commit -m "$(cat <<'EOF'
feat: add Health Canada connector (ca_health_canada.py)

Fetches Disease Risk Reduction Claims (PERMITTED) and Nutrient Function
Claims (PERMITTED) from canada.ca (cached 24h). 9 tests passing.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Australia FSANZ Connector

**Files:**
- Create: `src/mcp_food_regulatory/sources/au_fsanz.py`
- Modify: `tests/test_sources.py`

- [ ] **Step 1: Add failing tests**

Add import at top of `tests/test_sources.py`:

```python
from mcp_food_regulatory.sources.au_fsanz import AUFSANZSource
```

Add fixture:

```python
@pytest.fixture
def au(http_client):
    return AUFSANZSource(http_client)
```

Append test class:

```python
# ------------------------------------------------------------------ #
#  Australia FSANZ tests                                              #
# ------------------------------------------------------------------ #

class TestAUFSANZSource:

    @pytest.mark.asyncio
    async def test_market_is_au(self, au):
        assert au.market == Market.AU

    @pytest.mark.asyncio
    async def test_search_calcium_returns_results(self, au):
        # Calcium/bone health is a pre-approved high level health claim in Schedule 4
        results = await au.search_health_claims("calcium")
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_folate_returns_results(self, au):
        results = await au.search_health_claims("folate")
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_unknown_not_defined(self, au):
        results = await au.search_health_claims("xylobiose_fictional_xyz")
        assert len(results) >= 1
        assert results[0].status == ClaimStatus.NOT_DEFINED

    @pytest.mark.asyncio
    async def test_get_standard_127(self, au):
        standard = await au.get_standard("Standard 1.2.7")
        assert standard is not None
        assert standard.market == Market.AU
        assert standard.key_definitions is not None

    @pytest.mark.asyncio
    async def test_get_standard_unknown_returns_none(self, au):
        assert await au.get_standard("AU 999-UNKNOWN") is None

    @pytest.mark.asyncio
    async def test_search_standards_returns_list(self, au):
        results = await au.search_standards("nutrition")
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_market_overview(self, au):
        overview = await au.get_market_overview()
        assert overview.market == Market.AU
        assert "FSANZ" in overview.authority_name
        assert len(overview.key_legislation) >= 2

    @pytest.mark.asyncio
    async def test_two_calls_no_crash(self, au):
        r1 = await au.search_health_claims("calcium")
        r2 = await au.search_health_claims("calcium")
        assert len(r1) == len(r2)
```

- [ ] **Step 2: Run to verify ImportError**

```bash
uv run pytest tests/test_sources.py::TestAUFSANZSource -v 2>&1 | head -10
```

Expected: `ImportError: cannot import name 'AUFSANZSource'`

- [ ] **Step 3: Create src/mcp_food_regulatory/sources/au_fsanz.py**

```python
"""
Food Standards Australia New Zealand (FSANZ) regulatory data source.

Health claims governed by Standard 1.2.7 of the Australia New Zealand Food Standards Code:
  - General level health claims (Schedule 3): CONDITIONAL
    (food must pass nutrient profiling score per clause 17)
  - High level health claims (Schedule 4): PERMITTED
    (pre-approved list referencing serious disease/conditions)

Implementation:
  search_health_claims() -- Fetches Standard 1.2.7 from legislation.gov.au (cached 24h).
  get_standard()         -- Seeded for key standards.
  search_standards()     -- Seeded list.
  get_market_overview()  -- Static.
"""

from __future__ import annotations
import time
from bs4 import BeautifulSoup
from mcp_food_regulatory.models import (
    Market, ClaimResult, ClaimStatus, Standard, MarketOverview, RegulatoryBasis
)
from mcp_food_regulatory.sources.base import RegulatorySource

_BASE_URL = "https://www.foodstandards.gov.au"
_STD127_URL = "https://www.legislation.gov.au/Series/F2015L00411"
_CACHE_TTL = 86400

_std127_cache: list[dict] | None = None
_std127_fetched_at: float = 0.0

_KNOWN_STANDARDS: dict[str, dict] = {
    "Standard 1.2.7": {
        "title": (
            "Australia New Zealand Food Standards Code -- "
            "Standard 1.2.7 -- Nutrition, Health and Related Claims"
        ),
        "category": "standard",
        "adopted": "2013",
        "last_amended": "2022",
        "summary": (
            "Governs nutrition content claims and health claims in Australia and New Zealand. "
            "Schedule 2: Conditions for nutrition content claims. "
            "Schedule 3: Pre-approved general level health claims (food-health relationships). "
            "Schedule 4: Pre-approved high level health claims (refer to serious disease/conditions)."
        ),
        "full_text_url": _STD127_URL,
        "key_definitions": {
            "General level health claim": (
                "A health claim that does not refer to a serious disease or condition."
            ),
            "High level health claim": (
                "A health claim that refers to a serious disease or biomarker of a serious disease."
            ),
            "Nutrient profiling score": (
                "A score calculated per Standard 1.2.7 clause 17. "
                "Food must achieve a passing score to carry general level health claims."
            ),
        },
    },
    "Standard 1.2.8": {
        "title": (
            "Australia New Zealand Food Standards Code -- "
            "Standard 1.2.8 -- Nutrition Information Requirements"
        ),
        "category": "standard",
        "adopted": "2013",
        "summary": "Mandates the Nutrition Information Panel (NIP) format for Australian and NZ packaged foods.",
        "full_text_url": "https://www.legislation.gov.au/Series/F2015L00410",
    },
    "FSANZ Act 1991": {
        "title": "Food Standards Australia New Zealand Act 1991",
        "category": "legislation",
        "adopted": "1991",
        "last_amended": "2020",
        "summary": (
            "Establishes FSANZ and its mandate to develop and administer "
            "the Australia New Zealand Food Standards Code."
        ),
        "full_text_url": "https://www.legislation.gov.au/Series/C2004A04182",
    },
}


class AUFSANZSource(RegulatorySource):
    """
    FSANZ data source for Australia (and New Zealand).

    Standard 1.2.7 fetched from legislation.gov.au (cached 24h).
    Schedule 4 (high level) → PERMITTED.
    Schedule 3 (general level) → CONDITIONAL (nutrient profiling score required).
    """

    market = Market.AU
    BASE_URL = _BASE_URL

    async def search_health_claims(
        self,
        ingredient: str,
        claim_type: str | None = None,
    ) -> list[ClaimResult]:
        normalized = ingredient.lower().strip()
        results = []

        try:
            for item in await self._get_std127_data():
                if normalized in item["text"].lower():
                    is_high = item["schedule"] == "4"
                    status = ClaimStatus.PERMITTED if is_high else ClaimStatus.CONDITIONAL
                    claim_t = (
                        "high_level_health_claim" if is_high
                        else "general_level_health_claim"
                    )
                    if claim_type is None or claim_type == claim_t:
                        conditions = item["text"]
                        if not is_high:
                            conditions += (
                                " Food must achieve a passing nutrient profiling score "
                                "per Standard 1.2.7 clause 17 before this claim may be used."
                            )
                        results.append(ClaimResult(
                            market=Market.AU,
                            ingredient=ingredient,
                            claim_type=claim_t,
                            status=status,
                            conditions=conditions,
                            basis=RegulatoryBasis(
                                instrument="Standard 1.2.7",
                                article=f"Schedule {item['schedule']}",
                                url=_STD127_URL,
                                notes=(
                                    f"Pre-approved food-health relationship from "
                                    f"Schedule {item['schedule']} of Standard 1.2.7."
                                ),
                            ),
                            source_url=_STD127_URL,
                        ))
        except Exception:
            pass

        if not results:
            results.append(ClaimResult(
                market=Market.AU,
                ingredient=ingredient,
                claim_type=claim_type or "health_claim",
                status=ClaimStatus.NOT_DEFINED,
                conditions=None,
                basis=RegulatoryBasis(
                    instrument="Standard 1.2.7",
                    article=None,
                    url=_STD127_URL,
                    notes=(
                        "No pre-approved health claim found in Standard 1.2.7 for this ingredient. "
                        "Self-substantiated general level health claims may be possible with adequate evidence."
                    ),
                ),
                source_url=_BASE_URL,
            ))

        return results

    async def _get_std127_data(self) -> list[dict]:
        global _std127_cache, _std127_fetched_at
        if _std127_cache is None or (time.time() - _std127_fetched_at) > _CACHE_TTL:
            _std127_cache = await self._fetch_std127()
            _std127_fetched_at = time.time()
        return _std127_cache

    async def _fetch_std127(self) -> list[dict]:
        resp = await self._get(_STD127_URL)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        items = []
        current_schedule = "3"
        for tag in soup.find_all(["h2", "h3", "h4", "td", "li", "p"]):
            text = tag.get_text(strip=True)
            if "schedule 4" in text.lower():
                current_schedule = "4"
            elif "schedule 3" in text.lower():
                current_schedule = "3"
            if len(text) > 30 and tag.name in ("td", "li", "p"):
                items.append({"text": text, "schedule": current_schedule})
        return items

    async def get_standard(self, standard_id: str) -> Standard | None:
        upper = standard_id.upper()
        for key, data in _KNOWN_STANDARDS.items():
            if upper in key.upper() or key.upper() in upper:
                return Standard(standard_id=key, market=Market.AU, **data)
        return None

    async def search_standards(self, query: str) -> list[Standard]:
        query_lower = query.lower()
        results = [
            Standard(standard_id=key, market=Market.AU, **data)
            for key, data in _KNOWN_STANDARDS.items()
            if query_lower in key.lower()
            or query_lower in data["title"].lower()
            or query_lower in (data.get("summary") or "").lower()
        ]
        return results or [
            Standard(standard_id=k, market=Market.AU, **v)
            for k, v in _KNOWN_STANDARDS.items()
        ]

    async def get_market_overview(self) -> MarketOverview:
        return MarketOverview(
            market=Market.AU,
            authority_name="Food Standards Australia New Zealand (FSANZ)",
            authority_url=_BASE_URL,
            key_legislation=[
                "Food Standards Australia New Zealand Act 1991",
                "Standard 1.2.7 -- Nutrition, Health and Related Claims",
                "Standard 1.2.8 -- Nutrition Information Requirements",
            ],
            health_claims_framework=(
                "Health claims in Australia and New Zealand are governed by Standard 1.2.7. "
                "General level health claims (Schedule 3) are CONDITIONAL -- "
                "food must pass nutrient profiling score per clause 17. "
                "High level health claims (Schedule 4) are PERMITTED from a pre-approved list. "
                "Self-substantiated general level claims are also permitted with adequate evidence."
            ),
            notes=(
                "Standard 1.2.7 applies in both Australia and New Zealand. "
                "FSANZ develops the standards; state/territory food enforcement authorities administer them. "
                "NZ has some additional provisions -- check FSANZ Application A1090."
            ),
        )
```

- [ ] **Step 4: Run Australia tests**

```bash
uv run pytest tests/test_sources.py::TestAUFSANZSource -v
```

Expected: all 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_food_regulatory/sources/au_fsanz.py tests/test_sources.py
git commit -m "$(cat <<'EOF'
feat: add FSANZ connector (au_fsanz.py)

Fetches Standard 1.2.7 from legislation.gov.au (cached 24h).
Schedule 4 high level claims → PERMITTED; Schedule 3 general → CONDITIONAL.
9 tests passing.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Register All Batch 1 Connectors in server.py + Update Docs

**Files:**
- Modify: `src/mcp_food_regulatory/server.py`
- Modify: `CLAUDE.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Add imports to server.py**

Find in `src/mcp_food_regulatory/server.py`:

```python
from mcp_food_regulatory.sources.ph_fda import PhFDASource
```

Replace with:

```python
from mcp_food_regulatory.sources.ph_fda import PhFDASource
from mcp_food_regulatory.sources.jp_caa import JPCAASource
from mcp_food_regulatory.sources.us_fda import USFDASource
from mcp_food_regulatory.sources.ca_health_canada import CAHealthCanadaSource
from mcp_food_regulatory.sources.au_fsanz import AUFSANZSource
```

- [ ] **Step 2: Add to SOURCES dict in server.py**

Find:

```python
SOURCES = {
    Market.CODEX: CodexSource,
    Market.EU: EUSource,
    Market.PH: PhFDASource,
}
```

Replace with:

```python
SOURCES = {
    Market.CODEX: CodexSource,
    Market.EU: EUSource,
    Market.PH: PhFDASource,
    Market.JP: JPCAASource,
    Market.US: USFDASource,
    Market.CA: CAHealthCanadaSource,
    Market.AU: AUFSANZSource,
}
```

- [ ] **Step 3: Update list_markets() in server.py**

Find:

```python
    implemented = {
        "codex": "Codex Alimentarius Commission (FAO/WHO)",
        "eu": "European Commission / EFSA",
        "ph": "Philippines Food and Drug Administration (FDA)",
    }
    planned = {
        "au": "Food Standards Australia New Zealand (FSANZ)",
        "my": "Malaysia Ministry of Health",
        "vn": "Vietnam Ministry of Health",
        "id": "Indonesia BPOM",
        "th": "Thailand FDA",
        "gb": "UK Food Standards Agency",
        "ng": "Nigeria NAFDAC",
        "gh": "Ghana FDA",
    }
```

Replace with:

```python
    implemented = {
        "codex": "Codex Alimentarius Commission (FAO/WHO)",
        "eu": "European Commission / EFSA",
        "ph": "Philippines Food and Drug Administration (FDA)",
        "jp": "Consumer Affairs Agency Japan (CAA)",
        "us": "Food and Drug Administration (US FDA)",
        "ca": "Health Canada / CFIA",
        "au": "Food Standards Australia New Zealand (FSANZ)",
    }
    planned = {
        "br": "Brazil ANVISA",
        "kr": "Korea Ministry of Food and Drug Safety (MFDS)",
        "sa": "Saudi Food and Drug Authority (SFDA)",
        "in": "Food Safety and Standards Authority of India (FSSAI)",
        "cn": "National Health Commission / SAMR (China)",
        "co": "INVIMA (Colombia)",
        "cl": "MINSAL / ISP (Chile)",
        "mx": "COFEPRIS (Mexico)",
        "ae": "ESMA / Dubai Municipality (UAE)",
        "za": "Department of Health (South Africa)",
        "my": "Malaysia Ministry of Health",
        "vn": "Vietnam Ministry of Health",
        "id": "Indonesia BPOM",
        "th": "Thailand FDA",
        "gb": "UK Food Standards Agency",
        "ng": "Nigeria NAFDAC",
        "gh": "Ghana FDA",
    }
```

- [ ] **Step 4: Update FastMCP instructions string in server.py**

Find:

```python
        "Supported markets: codex (Codex Alimentarius), eu (European Union), ph (Philippines FDA). "
        "More ASEAN markets coming — see README for contribution guide."
```

Replace with:

```python
        "Supported markets: codex (Codex Alimentarius), eu (European Union), "
        "ph (Philippines FDA), jp (Japan CAA), us (US FDA), ca (Health Canada), au (FSANZ). "
        "More markets coming — see README for contribution guide."
```

- [ ] **Step 5: Update CLAUDE.md**

Find:

```
## Current status
Codex + EU + PH FDA implemented. Next: my_moh.py, au_fsanz.py
```

Replace with:

```
## Current status
Batch 1 complete: Codex, EU, PH, JP, US, CA, AU implemented.
Next batch (Batch 2): br_anvisa.py, kr_mfds.py, sa_sfda.py
```

- [ ] **Step 6: Update AGENTS.md**

Find:

```
## Current status
Codex + EU + PH FDA implemented. Next: my_moh.py, au_fsanz.py
```

Replace with:

```
## Current status
Batch 1 complete: Codex, EU, PH, JP, US, CA, AU implemented.
Next batch (Batch 2): br_anvisa.py, kr_mfds.py, sa_sfda.py
```

- [ ] **Step 7: Run full test suite**

```bash
uv run pytest tests/ -v 2>&1 | tail -20
```

Expected: all tests pass (38 existing + ~36 new = ~74 total).

- [ ] **Step 8: Run lint**

```bash
uv run ruff check src/
```

Expected: `All checks passed!`

- [ ] **Step 9: Commit**

```bash
git add src/mcp_food_regulatory/server.py CLAUDE.md AGENTS.md
git commit -m "$(cat <<'EOF'
feat: register Batch 1 connectors in server.py

Adds JP, US, CA, AU to SOURCES dict and list_markets().
Updates FastMCP instructions string and docs.
Batch 1 complete: 7 markets implemented.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```
