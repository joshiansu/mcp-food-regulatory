# mcp-food-regulatory Setup & Philippines FDA Connector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold the mcp-food-regulatory project from its zip, add the Philippines FDA market connector with tests, and commit in two clean commits.

**Architecture:** Two-commit flow -- Commit 1 unpacks the existing scaffold (Codex + EU sources) into the proper `src/` layout. Commit 2 adds `ph_fda.py` (seeded claims + best-effort live standards search), extends the test suite, updates `server.py`, and adds `AGENTS.md`.

**Tech Stack:** Python 3.10+, FastMCP, httpx, BeautifulSoup4, Pydantic v2, uv, pytest-asyncio

---

## File Map

### Commit 1 -- scaffold only
| File | Action | Notes |
|---|---|---|
| `src/mcp_food_regulatory/__init__.py` | Create (empty) | Required for package |
| `src/mcp_food_regulatory/models.py` | Create (from zip) | Pydantic models |
| `src/mcp_food_regulatory/server.py` | Create (from zip) | FastMCP + 6 tools |
| `src/mcp_food_regulatory/sources/__init__.py` | Create (empty) | Required for subpackage |
| `src/mcp_food_regulatory/sources/base.py` | Create (from zip) | Abstract base class |
| `src/mcp_food_regulatory/sources/codex.py` | Create (from zip) | Codex source |
| `src/mcp_food_regulatory/sources/eu.py` | Create (from zip) | EU source |
| `src/mcp_food_regulatory/sources/template.py` | Create (from zip) | Template for new markets |
| `tests/__init__.py` | Create (empty) | Required for test discovery |
| `tests/test_sources.py` | Create (from zip) | Existing Codex + EU tests |
| `pyproject.toml` | Create (from zip) | Project metadata + deps |
| `README.md` | Create (from zip) | |
| `CONTRIBUTING.md` | Create (from zip) | |

### Commit 2 -- Philippines FDA
| File | Action | Notes |
|---|---|---|
| `src/mcp_food_regulatory/sources/ph_fda.py` | Create | New connector |
| `src/mcp_food_regulatory/server.py` | Modify | Import PhFDASource, add to SOURCES, update list_markets |
| `tests/test_sources.py` | Modify | Add TestPHFDASource class |
| `CLAUDE.md` | Modify | Update current status |
| `AGENTS.md` | Create | Same content as CLAUDE.md for other agent runtimes |

---

## Task 1: Set Up Directory Structure

**Files:**
- Create: `src/mcp_food_regulatory/__init__.py`
- Create: `src/mcp_food_regulatory/sources/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create package directories**

```bash
mkdir -p src/mcp_food_regulatory/sources
mkdir -p tests
```

- [ ] **Step 2: Create empty `__init__.py` files**

```bash
touch src/mcp_food_regulatory/__init__.py
touch src/mcp_food_regulatory/sources/__init__.py
touch tests/__init__.py
```

---

## Task 2: Unpack Source Files from Zip

**Files:** All files listed under Commit 1 above.

The zip (`files.zip`) is in the project root. Files need to be placed at their correct paths -- they are NOT in subdirectories inside the zip.

- [ ] **Step 1: Copy top-level files from zip extract**

The zip was already extracted to `/tmp/mcp-food-regulatory-extracted/`. Copy files to their correct locations:

```bash
cp /tmp/mcp-food-regulatory-extracted/pyproject.toml ./pyproject.toml
cp /tmp/mcp-food-regulatory-extracted/README.md ./README.md
cp /tmp/mcp-food-regulatory-extracted/CONTRIBUTING.md ./CONTRIBUTING.md
```

- [ ] **Step 2: Copy source files**

```bash
cp /tmp/mcp-food-regulatory-extracted/models.py src/mcp_food_regulatory/models.py
cp /tmp/mcp-food-regulatory-extracted/server.py src/mcp_food_regulatory/server.py
cp /tmp/mcp-food-regulatory-extracted/base.py src/mcp_food_regulatory/sources/base.py
cp /tmp/mcp-food-regulatory-extracted/codex.py src/mcp_food_regulatory/sources/codex.py
cp /tmp/mcp-food-regulatory-extracted/eu.py src/mcp_food_regulatory/sources/eu.py
cp /tmp/mcp-food-regulatory-extracted/template.py src/mcp_food_regulatory/sources/template.py
cp /tmp/mcp-food-regulatory-extracted/test_sources.py tests/test_sources.py
```

---

## Task 3: Install Dependencies and Verify Existing Tests Pass

**Files:** None modified.

- [ ] **Step 1: Install project in dev mode**

```bash
uv sync --extra dev
```

Expected: resolves dependencies, installs mcp, fastmcp, httpx, bs4, pydantic, cachetools, python-dateutil, pytest, pytest-asyncio, pytest-httpx, ruff.

- [ ] **Step 2: Run existing tests**

```bash
uv run pytest tests/ -v
```

Expected: all Codex and EU tests pass. Some tests make live HTTP calls -- if network is unavailable, those tests may fail. The seeded-data tests (market identity, get_standard for known IDs, market_overview) must pass unconditionally.

- [ ] **Step 3: Run linter**

```bash
uv run ruff check src/
```

Expected: no errors.

---

## Task 4: Commit 1 -- Initial Scaffold

- [ ] **Step 1: Stage all scaffold files**

```bash
git add src/ tests/ pyproject.toml README.md CONTRIBUTING.md CLAUDE.md
```

- [ ] **Step 2: Commit**

```bash
git commit -m "$(cat <<'EOF'
chore: initial scaffold -- Codex + EU sources

Sets up src/ layout, pyproject.toml, tests, and existing
Codex Alimentarius + EU health claims connectors.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Write Failing Tests for Philippines FDA

**Files:**
- Modify: `tests/test_sources.py`

- [ ] **Step 1: Add PhFDASource import at top of test file**

In `tests/test_sources.py`, after the existing imports, add:

```python
from mcp_food_regulatory.sources.ph_fda import PhFDASource
```

- [ ] **Step 2: Add ph fixture after the `eu` fixture**

```python
@pytest.fixture
def ph(http_client):
    return PhFDASource(http_client)
```

- [ ] **Step 3: Add TestPHFDASource class at end of file**

```python
# ------------------------------------------------------------------ #
#  Philippines FDA tests                                              #
# ------------------------------------------------------------------ #

class TestPHFDASource:

    @pytest.mark.asyncio
    async def test_market_is_ph(self, ph):
        assert ph.market == Market.PH

    @pytest.mark.asyncio
    async def test_search_vitamin_d_permitted(self, ph):
        results = await ph.search_health_claims("vitamin d")
        assert len(results) >= 1
        assert any(r.status == ClaimStatus.PERMITTED for r in results)
        assert any(r.claim_type == "nutrient_function" for r in results)

    @pytest.mark.asyncio
    async def test_search_moringa_conditional(self, ph):
        results = await ph.search_health_claims("moringa")
        assert len(results) >= 1
        assert any(r.status == ClaimStatus.CONDITIONAL for r in results)

    @pytest.mark.asyncio
    async def test_search_malunggay_alias(self, ph):
        # malunggay is the local name -- alias lookup must work
        results = await ph.search_health_claims("malunggay")
        assert len(results) >= 1
        assert any(r.status == ClaimStatus.CONDITIONAL for r in results)

    @pytest.mark.asyncio
    async def test_search_inulin_not_defined(self, ph):
        results = await ph.search_health_claims("inulin")
        assert len(results) >= 1
        assert any(r.status == ClaimStatus.NOT_DEFINED for r in results)

    @pytest.mark.asyncio
    async def test_search_caffeine_not_defined(self, ph):
        results = await ph.search_health_claims("caffeine")
        assert len(results) >= 1
        assert any(r.status == ClaimStatus.NOT_DEFINED for r in results)

    @pytest.mark.asyncio
    async def test_get_standard_circular_2014_007(self, ph):
        standard = await ph.get_standard("FDA Circular 2014-007")
        assert standard is not None
        assert standard.market == Market.PH
        assert "Health" in standard.title or "Nutrient" in standard.title
        assert standard.key_definitions is not None

    @pytest.mark.asyncio
    async def test_get_standard_ra_3720(self, ph):
        standard = await ph.get_standard("Republic Act 3720")
        assert standard is not None
        assert standard.market == Market.PH

    @pytest.mark.asyncio
    async def test_get_standard_unknown_returns_none(self, ph):
        result = await ph.get_standard("PH 999-9999-UNKNOWN")
        assert result is None

    @pytest.mark.asyncio
    async def test_search_standards_returns_list(self, ph):
        # seeded fallback must work even if live fetch fails
        results = await ph.search_standards("health claims")
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_market_overview(self, ph):
        overview = await ph.get_market_overview()
        assert overview.market == Market.PH
        assert "FDA" in overview.authority_name
        assert len(overview.key_legislation) >= 3

    @pytest.mark.asyncio
    async def test_unknown_ingredient_no_crash(self, ph):
        results = await ph.search_health_claims("xylobiose_fictional_ingredient_xyz")
        assert isinstance(results, list)
        assert len(results) >= 1
        assert results[0].status == ClaimStatus.NOT_DEFINED
```

- [ ] **Step 4: Run tests to verify they fail with ImportError (not yet implemented)**

```bash
uv run pytest tests/test_sources.py::TestPHFDASource -v
```

Expected: `ImportError: cannot import name 'PhFDASource'` or `ModuleNotFoundError`. This confirms we're on the right TDD path.

---

## Task 6: Implement `ph_fda.py`

**Files:**
- Create: `src/mcp_food_regulatory/sources/ph_fda.py`

- [ ] **Step 1: Create `src/mcp_food_regulatory/sources/ph_fda.py`** with full content:

```python
"""
Philippines Food and Drug Administration (FDA) regulatory data source.

Authority: Food and Drug Administration Philippines
Website:   https://www.fda.gov.ph

Health claims are governed primarily by:
  - FDA Circular No. 2014-007 (Supplemental Guidelines on Health and Nutrient Claims)
  - Republic Act 3720 (Food, Drug and Cosmetic Act)
  - DOH Circular No. 2013-010 (10 Herbal Plants endorsed by DOH)

Implementation strategy:
  search_health_claims() -- seeded static data, no network calls
  get_standard()         -- seeded for known circulars, None for unknown
  search_standards()     -- attempts live fetch of fda.gov.ph/food-regulations/,
                            falls back to seeded circular list on failure
  get_market_overview()  -- static
"""

from __future__ import annotations
from bs4 import BeautifulSoup
from mcp_food_regulatory.models import (
    Market, ClaimResult, ClaimStatus, Standard, MarketOverview, RegulatoryBasis
)
from mcp_food_regulatory.sources.base import RegulatorySource

_BASE_URL = "https://www.fda.gov.ph"
_REGULATIONS_URL = "https://www.fda.gov.ph/food-regulations/"

_SEEDED_CLAIMS: list[dict] = [
    {
        "ingredient": "vitamin d",
        "aliases": ["vitamin d3", "cholecalciferol", "calciferol"],
        "claim_type": "nutrient_function",
        "status": ClaimStatus.PERMITTED,
        "conditions": (
            "Must meet minimum content level per Schedule 2. "
            "Permitted claim: 'Vitamin D is needed for normal growth and development of bones and teeth.'"
        ),
        "basis": RegulatoryBasis(
            instrument="FDA Circular No. 2014-007",
            article="Schedule 2",
            url="https://www.fda.gov.ph/wp-content/uploads/2014/09/FDA-Circular-2014-0007.pdf",
            notes="Nutrient function claim -- pre-authorized, no individual application required.",
        ),
    },
    {
        "ingredient": "calcium",
        "aliases": ["calcium carbonate", "calcium citrate", "calcium phosphate"],
        "claim_type": "nutrient_function",
        "status": ClaimStatus.PERMITTED,
        "conditions": (
            "Must meet minimum content level per Schedule 2. "
            "Permitted claim: 'Calcium is needed for normal growth and development of bones and teeth.'"
        ),
        "basis": RegulatoryBasis(
            instrument="FDA Circular No. 2014-007",
            article="Schedule 2",
            url="https://www.fda.gov.ph/wp-content/uploads/2014/09/FDA-Circular-2014-0007.pdf",
            notes="Nutrient function claim -- pre-authorized.",
        ),
    },
    {
        "ingredient": "iron",
        "aliases": ["ferrous sulfate", "ferrous gluconate", "ferric"],
        "claim_type": "nutrient_function",
        "status": ClaimStatus.PERMITTED,
        "conditions": (
            "Must meet minimum content level per Schedule 2. "
            "Permitted claim: 'Iron is needed for the formation of red blood cells and hemoglobin.'"
        ),
        "basis": RegulatoryBasis(
            instrument="FDA Circular No. 2014-007",
            article="Schedule 2",
            url="https://www.fda.gov.ph/wp-content/uploads/2014/09/FDA-Circular-2014-0007.pdf",
            notes="Nutrient function claim -- pre-authorized.",
        ),
    },
    {
        "ingredient": "zinc",
        "aliases": ["zinc sulfate", "zinc gluconate", "zinc oxide"],
        "claim_type": "nutrient_function",
        "status": ClaimStatus.PERMITTED,
        "conditions": (
            "Must meet minimum content level per Schedule 2. "
            "Permitted claim: 'Zinc is needed for normal growth and sexual maturation.'"
        ),
        "basis": RegulatoryBasis(
            instrument="FDA Circular No. 2014-007",
            article="Schedule 2",
            url="https://www.fda.gov.ph/wp-content/uploads/2014/09/FDA-Circular-2014-0007.pdf",
            notes="Nutrient function claim -- pre-authorized.",
        ),
    },
    {
        "ingredient": "dietary fibre",
        "aliases": ["dietary fiber", "fibre", "fiber"],
        "claim_type": "nutrition_claim",
        "status": ClaimStatus.CONDITIONAL,
        "conditions": (
            "Minimum 3g fibre per serving (or 1.5g per 100 kcal) for 'Source of Fibre'. "
            "Minimum 6g per serving for 'High Fibre'. Per Schedule 1, FDA Circular 2014-007."
        ),
        "basis": RegulatoryBasis(
            instrument="FDA Circular No. 2014-007",
            article="Schedule 1",
            url="https://www.fda.gov.ph/wp-content/uploads/2014/09/FDA-Circular-2014-0007.pdf",
            notes="Nutrition claim -- content threshold applies.",
        ),
    },
    {
        "ingredient": "probiotics",
        "aliases": ["lactobacillus", "bifidobacterium", "probiotic", "live cultures"],
        "claim_type": "function_claim",
        "status": ClaimStatus.CONDITIONAL,
        "conditions": (
            "Must demonstrate minimum viable count at end of shelf life. "
            "Permitted function claims limited to general gut health statements per Schedule 3. "
            "Disease-specific claims require individual authorization."
        ),
        "basis": RegulatoryBasis(
            instrument="FDA Circular No. 2014-007",
            article="Schedule 3",
            url="https://www.fda.gov.ph/wp-content/uploads/2014/09/FDA-Circular-2014-0007.pdf",
            notes="Function claim -- conditions and viable count requirements apply.",
        ),
    },
    {
        "ingredient": "omega-3",
        "aliases": ["fish oil", "dha", "epa", "omega 3", "docosahexaenoic acid", "eicosapentaenoic acid"],
        "claim_type": "nutrient_function",
        "status": ClaimStatus.CONDITIONAL,
        "conditions": (
            "DHA function claim ('DHA contributes to normal brain function') permitted "
            "with minimum 200mg DHA per serving. Must not imply disease prevention."
        ),
        "basis": RegulatoryBasis(
            instrument="FDA Circular No. 2014-007",
            article="Schedule 2",
            url="https://www.fda.gov.ph/wp-content/uploads/2014/09/FDA-Circular-2014-0007.pdf",
            notes="Nutrient function claim -- DHA content threshold applies.",
        ),
    },
    {
        "ingredient": "moringa",
        "aliases": ["malunggay", "moringa oleifera"],
        "claim_type": "traditional_herbal",
        "status": ClaimStatus.CONDITIONAL,
        "conditions": (
            "Claims limited to traditional use statements "
            "(e.g. 'traditionally used to support lactation'). "
            "Disease treatment or cure claims are prohibited. "
            "Must comply with FDA labeling requirements for food supplements under RA 3720."
        ),
        "basis": RegulatoryBasis(
            instrument="DOH Circular No. 2013-010",
            article=None,
            url=None,
            notes=(
                "Moringa (Malunggay) recognized by DOH for nutritional value. "
                "RA 3720 applies for food supplement registration."
            ),
        ),
    },
    {
        "ingredient": "caffeine",
        "aliases": ["caffeine anhydrous"],
        "claim_type": "health_claim",
        "status": ClaimStatus.NOT_DEFINED,
        "conditions": None,
        "basis": RegulatoryBasis(
            instrument="FDA Circular No. 2014-007",
            article=None,
            url="https://www.fda.gov.ph/wp-content/uploads/2014/09/FDA-Circular-2014-0007.pdf",
            notes=(
                "No specific health claim provision for caffeine in PH regulatory framework. "
                "Safety limits on caffeine content in beverages apply separately."
            ),
        ),
    },
    {
        "ingredient": "inulin",
        "aliases": ["fos", "fructooligosaccharides", "chicory root", "chicory"],
        "claim_type": "prebiotic",
        "status": ClaimStatus.NOT_DEFINED,
        "conditions": None,
        "basis": RegulatoryBasis(
            instrument="FDA Circular No. 2014-007",
            article=None,
            url="https://www.fda.gov.ph/wp-content/uploads/2014/09/FDA-Circular-2014-0007.pdf",
            notes=(
                "Prebiotic claims are not specifically authorized in PH. "
                "Inulin may qualify as a dietary fibre nutrition claim if content thresholds are met."
            ),
        ),
    },
    {
        "ingredient": "coconut oil",
        "aliases": ["vco", "virgin coconut oil", "coconut"],
        "claim_type": "health_claim",
        "status": ClaimStatus.NOT_DEFINED,
        "conditions": None,
        "basis": RegulatoryBasis(
            instrument="FDA Circular No. 2014-007",
            article=None,
            url="https://www.fda.gov.ph/wp-content/uploads/2014/09/FDA-Circular-2014-0007.pdf",
            notes=(
                "FDA has issued advisories against unsubstantiated health claims for VCO. "
                "No authorized health claims exist for coconut oil under PH regulatory framework."
            ),
        ),
    },
    {
        "ingredient": "taro",
        "aliases": ["gabi", "colocasia esculenta"],
        "claim_type": "health_claim",
        "status": ClaimStatus.NOT_DEFINED,
        "conditions": None,
        "basis": RegulatoryBasis(
            instrument="FDA Circular No. 2014-007",
            article=None,
            url="https://www.fda.gov.ph/wp-content/uploads/2014/09/FDA-Circular-2014-0007.pdf",
            notes="No specific health claim provision for taro in PH regulatory framework.",
        ),
    },
]

_KNOWN_STANDARDS: dict[str, dict] = {
    "FDA Circular 2014-007": {
        "title": "Supplemental Guidelines on Health and Nutrient Claims for Food Products",
        "category": "circular",
        "adopted": "2014",
        "summary": (
            "Primary framework governing health and nutrient claims in the Philippines. "
            "Schedule 1: Nutrition claims (e.g. 'high fibre', 'low fat'). "
            "Schedule 2: Nutrient function claims (pre-authorized list). "
            "Schedule 3: Other function claims (conditions apply). "
            "Disease risk reduction claims require individual application."
        ),
        "full_text_url": "https://www.fda.gov.ph/wp-content/uploads/2014/09/FDA-Circular-2014-0007.pdf",
        "key_definitions": {
            "Nutrient function claim": (
                "A claim that describes the physiological role of a nutrient in growth, "
                "development, and normal functions of the body."
            ),
            "Health claim": (
                "Any representation that states a relationship exists between a food "
                "or constituent and health."
            ),
            "Nutrition claim": (
                "Any claim that states a food has particular nutritional properties."
            ),
        },
    },
    "Republic Act 3720": {
        "title": "Food, Drug and Cosmetic Act",
        "category": "legislation",
        "adopted": "1963",
        "last_amended": "2009",
        "summary": (
            "Foundational Philippine law governing food, drugs, and cosmetics. "
            "Empowers the FDA to regulate food labeling and health claims. "
            "Prohibits false or misleading labeling."
        ),
        "full_text_url": "https://www.fda.gov.ph/republic-act-3720/",
    },
    "DOH Circular 2013-010": {
        "title": "10 Herbal Plants Endorsed by the Department of Health",
        "category": "circular",
        "adopted": "2013",
        "summary": (
            "Endorses 10 Philippine herbal plants for traditional medicinal use: "
            "Akapulko, Ampalaya, Bawang, Bayabas, Lagundi, Niyog-niyogan, "
            "Sambong, Tsaang Gubat, Ulasimang Bato, and Yerba Buena. "
            "Moringa (Malunggay) is additionally recognized by DOH for nutritional value."
        ),
        "full_text_url": None,
    },
    "AO 88-B s.1984": {
        "title": "Rules and Regulations Governing the Labeling of Processed Foods",
        "category": "administrative_order",
        "adopted": "1984",
        "summary": "Establishes labeling requirements for processed food products including mandatory declarations.",
        "full_text_url": None,
    },
    "FDA MC 2020-005": {
        "title": "Labeling Requirements for Food Products",
        "category": "memorandum_circular",
        "adopted": "2020",
        "summary": "Updated labeling requirements covering nutrition facts panel, allergen declarations, and claims.",
        "full_text_url": None,
    },
}


class PhFDASource(RegulatorySource):
    """
    Philippines FDA regulatory data source.

    search_health_claims -- seeded data only, deterministic
    get_standard         -- seeded; returns None for unknown IDs
    search_standards     -- best-effort live fetch, falls back to seed
    get_market_overview  -- static
    """

    market = Market.PH
    BASE_URL = _BASE_URL

    async def search_health_claims(
        self,
        ingredient: str,
        claim_type: str | None = None,
    ) -> list[ClaimResult]:
        normalized = ingredient.lower().strip()
        results = []
        for entry in _SEEDED_CLAIMS:
            is_match = (
                normalized == entry["ingredient"]
                or normalized in entry["aliases"]
                or any(alias in normalized for alias in entry["aliases"])
                or any(normalized in alias for alias in entry["aliases"])
            )
            if not is_match:
                continue
            if claim_type is None or claim_type.lower() in entry["claim_type"]:
                results.append(ClaimResult(
                    market=Market.PH,
                    ingredient=entry["ingredient"],
                    claim_type=entry["claim_type"],
                    status=entry["status"],
                    conditions=entry.get("conditions"),
                    basis=entry.get("basis"),
                    source_url=_BASE_URL,
                ))
        if not results:
            results.append(ClaimResult(
                market=Market.PH,
                ingredient=ingredient,
                claim_type=claim_type or "health_claim",
                status=ClaimStatus.NOT_DEFINED,
                conditions=None,
                basis=RegulatoryBasis(
                    instrument="FDA Circular No. 2014-007",
                    article=None,
                    url="https://www.fda.gov.ph/wp-content/uploads/2014/09/FDA-Circular-2014-0007.pdf",
                    notes="No specific provision found for this ingredient in the PH FDA regulatory framework.",
                ),
                source_url=_BASE_URL,
            ))
        return results

    async def get_standard(self, standard_id: str) -> Standard | None:
        upper = standard_id.upper()
        for key, data in _KNOWN_STANDARDS.items():
            if upper in key.upper() or key.upper() in upper:
                return Standard(standard_id=key, market=Market.PH, **data)
        return None

    async def search_standards(self, query: str) -> list[Standard]:
        try:
            live = await self._fetch_live_standards(query)
            if live:
                return live
        except Exception:
            pass
        return self._search_seeded_standards(query)

    async def _fetch_live_standards(self, query: str) -> list[Standard]:
        resp = await self._get(_REGULATIONS_URL)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        query_lower = query.lower()
        results = []
        for link in soup.find_all("a", href=True):
            text = link.get_text(strip=True)
            if query_lower in text.lower() and len(text) > 10:
                href = link["href"]
                if not href.startswith("http"):
                    href = f"{_BASE_URL}{href}"
                results.append(Standard(
                    standard_id=text[:80],
                    market=Market.PH,
                    title=text,
                    category="regulation",
                    full_text_url=href,
                ))
        return results[:10]

    def _search_seeded_standards(self, query: str) -> list[Standard]:
        query_lower = query.lower()
        results = [
            Standard(standard_id=key, market=Market.PH, **data)
            for key, data in _KNOWN_STANDARDS.items()
            if (
                query_lower in key.lower()
                or query_lower in data["title"].lower()
                or query_lower in (data.get("summary") or "").lower()
            )
        ]
        if not results:
            results = [
                Standard(standard_id=key, market=Market.PH, **data)
                for key, data in _KNOWN_STANDARDS.items()
            ]
        return results

    async def get_market_overview(self) -> MarketOverview:
        return MarketOverview(
            market=Market.PH,
            authority_name="Food and Drug Administration Philippines (FDA)",
            authority_url=_BASE_URL,
            key_legislation=[
                "Republic Act 3720 (Food, Drug and Cosmetic Act)",
                "FDA Circular No. 2014-007 (Health and Nutrient Claims)",
                "DOH Circular No. 2013-010 (10 Herbal Plants)",
                "Administrative Order 88-B s.1984 (Food Labeling)",
            ],
            health_claims_framework=(
                "Health and nutrient claims are governed by FDA Circular No. 2014-007. "
                "Pre-authorized nutrient function claims (Schedule 2) may be used without "
                "individual application if content thresholds are met. "
                "Disease risk reduction claims require separate authorization. "
                "Traditional herbal claims are governed by DOH circulars."
            ),
            notes=(
                "The Philippines FDA sits under the Department of Health (DOH). "
                "Food supplement claims are regulated separately from food product claims."
            ),
        )
```

- [ ] **Step 2: Run PH FDA tests to verify they pass**

```bash
uv run pytest tests/test_sources.py::TestPHFDASource -v
```

Expected: all 12 tests PASS. `test_search_standards_returns_list` may hit the live FDA site or fall back to seeded -- both outcomes pass.

---

## Task 7: Update `server.py` to Register PhFDASource

**Files:**
- Modify: `src/mcp_food_regulatory/server.py`

- [ ] **Step 1: Add PhFDASource import**

In `src/mcp_food_regulatory/server.py`, the existing imports are:

```python
from mcp_food_regulatory.sources.codex import CodexSource
from mcp_food_regulatory.sources.eu import EUSource
```

Change to:

```python
from mcp_food_regulatory.sources.codex import CodexSource
from mcp_food_regulatory.sources.eu import EUSource
from mcp_food_regulatory.sources.ph_fda import PhFDASource
```

- [ ] **Step 2: Add PhFDASource to SOURCES dict**

The existing SOURCES dict is:

```python
SOURCES = {
    Market.CODEX: CodexSource,
    Market.EU: EUSource,
}
```

Change to:

```python
SOURCES = {
    Market.CODEX: CodexSource,
    Market.EU: EUSource,
    Market.PH: PhFDASource,
}
```

- [ ] **Step 3: Move "ph" to implemented in list_markets()**

The existing `list_markets()` function has:

```python
    implemented = {
        "codex": "Codex Alimentarius Commission (FAO/WHO)",
        "eu": "European Commission / EFSA",
    }
    planned = {
        "au": "Food Standards Australia New Zealand (FSANZ)",
        "ph": "Philippines FDA",
        ...
    }
```

Change to:

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

- [ ] **Step 4: Update the FastMCP instructions string**

Find:

```python
        "Supported markets: codex (Codex Alimentarius), eu (European Union). "
```

Change to:

```python
        "Supported markets: codex (Codex Alimentarius), eu (European Union), ph (Philippines FDA). "
```

---

## Task 8: Update CLAUDE.md and Add AGENTS.md

**Files:**
- Modify: `CLAUDE.md`
- Create: `AGENTS.md`

- [ ] **Step 1: Update Current Status in CLAUDE.md**

Find in `CLAUDE.md`:

```
## Current status
Codex + EU implemented. Next: ph_fda.py, my_moh.py, au_fsanz.py
```

Change to:

```
## Current status
Codex + EU + PH FDA implemented. Next: my_moh.py, au_fsanz.py
```

- [ ] **Step 2: Create AGENTS.md**

Create `AGENTS.md` with this exact content (AGENTS.md is read by OpenAI Codex and similar agent runtimes):

```markdown
# mcp-food-regulatory

MCP server for food regulatory data. FastMCP + Python 3.10+.

## Commands
- `uv run pytest tests/ -v` -- run tests
- `uv run mcp-food-regulatory` -- start server (stdio)
- `uv run ruff check src/` -- lint

## Architecture
- `src/mcp_food_regulatory/server.py` -- tool registration
- `src/mcp_food_regulatory/sources/` -- one file per market
- Add markets by copying `sources/template.py` and registering in `SOURCES` dict in server.py

## Current status
Codex + EU + PH FDA implemented. Next: my_moh.py, au_fsanz.py
```

---

## Task 9: Run Full Test Suite and Lint

**Files:** None modified.

- [ ] **Step 1: Run all tests**

```bash
uv run pytest tests/ -v
```

Expected: all tests pass (Codex + EU + PH FDA). Note: tests that make live HTTP calls (some Codex and EU tests) will pass only with network access.

- [ ] **Step 2: Run linter**

```bash
uv run ruff check src/
```

Expected: no errors.

---

## Task 10: Commit 2 -- Philippines FDA Connector

- [ ] **Step 1: Stage all new and modified files**

```bash
git add src/mcp_food_regulatory/sources/ph_fda.py \
        src/mcp_food_regulatory/server.py \
        tests/test_sources.py \
        CLAUDE.md \
        AGENTS.md
```

- [ ] **Step 2: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat: add Philippines FDA market connector

Implements PhFDASource with 12 seeded ingredients (vitamin D, calcium,
iron, zinc, dietary fibre, probiotics, omega-3, moringa/malunggay,
caffeine, inulin, coconut oil/VCO, taro) against per-ingredient
regulatory basis (FDA Circular 2014-007, RA 3720, DOH 2013-010).

search_standards() attempts live fetch of fda.gov.ph with seeded fallback.
All other methods are seeded/static for test reliability.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```
