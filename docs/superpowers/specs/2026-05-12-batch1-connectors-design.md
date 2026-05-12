# Batch 1 Market Connectors Design

**Date:** 2026-05-12
**Status:** Approved
**Markets:** Japan (jp), USA (us), Canada (ca), Australia (au)

## Overview

Add four live-first market connectors to mcp-food-regulatory. Unlike the PH FDA connector (seeded-only), Batch 1 connectors fetch live data from structured remote sources and cache in memory (24h TTL). Seeded data provides fallback when live fetch fails.

## Shared Architecture

All four connectors follow the EU source pattern (live fetch + cache), not the PH FDA pattern (seeded only).

### Method strategy per connector

| Method | Strategy |
|---|---|
| `search_health_claims()` | Live fetch (cached) → parse → filter by ingredient. Falls back to seeded on error. |
| `get_standard()` | Seeded dict fast-path. Returns None for unknown IDs. |
| `search_standards()` | Seeded list. No live fetch needed (standards are stable). |
| `get_market_overview()` | Static. |

### Shared caching pattern

Module-level cache per connector (never shared across connectors):

```python
import time

_cache: list | None = None
_cache_fetched_at: float = 0.0
_CACHE_TTL = 86400  # 24 hours

async def _get_claims_data(self) -> list:
    global _cache, _cache_fetched_at
    if _cache is None or (time.time() - _cache_fetched_at) > _CACHE_TTL:
        _cache = await self._fetch_remote()
        _cache_fetched_at = time.time()
    return _cache
```

### Fallback chain

Live fetch → seeded data → `ClaimResult(status=NOT_DEFINED)` (no crash, always returns a list)

## Per-Connector Specifications

### Japan -- `jp_caa.py`

**Authority:** Consumer Affairs Agency (消費者庁)
**Market enum:** `Market.JP`
**BASE_URL:** `https://www.fld.caa.go.jp`

**Live data sources:**
- FOSHU DB: `https://www.fld.caa.go.jp/caaks/cssc01/` -- CSV download of all approved FOSHU products
- FNFC DB: `https://www.fld.caa.go.jp/caaks/cssc02/` -- CSV download of all self-notified FNFC products

**Claim status mapping:**
- FOSHU entries → `PERMITTED` (individually authorised by CAA)
- FNFC entries → `CONDITIONAL` (self-notified, manufacturer responsibility)
- NFC (Nutrient Function Claims) → seeded only, `PERMITTED` (fixed pre-approved list of 13 nutrients: vitamins A/D/E/K/B1/B2/B6/B12/C, niacin, pantothenic acid, folic acid, calcium, iron, zinc, copper, magnesium)

**Ingredient matching:** search claim text and ingredient/food component columns for the query string (case-insensitive substring, CSV field-level only -- not across column names).

**Key seeded standards:**
- Health Promotion Act (健康増進法) 2002
- Food Labelling Act (食品表示法) 2013
- Foods for Specified Health Uses (特定保健用食品) Guidelines

**Primary legislation basis:** Health Promotion Act 2002 (FOSHU); Food Labelling Act 2013 (FNFC/NFC)

---

### USA -- `us_fda.py`

**Authority:** Food and Drug Administration
**Market enum:** `Market.US`
**BASE_URL:** `https://www.fda.gov`

**Live data sources:**
- Authorized Health Claims page: `https://www.fda.gov/food/food-labeling-nutrition/authorized-health-claims-meet-significant-scientific-agreement-ssa-standard`
- Qualified Health Claims page: `https://www.fda.gov/food/food-labeling-nutrition/qualified-health-claims-substances-conventional-foods`

**Claim status mapping:**
- Authorized Health Claims → `PERMITTED` (meet Significant Scientific Agreement standard, 21 CFR)
- Qualified Health Claims → `CONDITIONAL` (interim enforcement discretion, carry disclaimer)
- Structure/Function Claims → seeded fallback, `NOT_DEFINED` (self-notified, no public authoritative DB)

**Parsing:** both pages render claim titles as `<li>` items linking to individual claim pages. Parse the `<li>` text for ingredient matching.

**Key seeded standards:**
- 21 CFR Part 101 (Food Labeling)
- 21 CFR 101.14 (Authorized Health Claims -- general requirements)
- 21 CFR 101.70-101.83 (individual authorized claim regulations)
- FDA Modernization Act 1997

**Primary legislation basis:** 21 CFR Part 101 (FDA regulations); FDAMA 1997

---

### Canada -- `ca_health_canada.py`

**Authority:** Health Canada / CFIA
**Market enum:** `Market.CA`
**BASE_URL:** `https://www.canada.ca`

**Live data sources:**
- Disease Risk Reduction Claims page: `https://www.canada.ca/en/health-canada/services/food-nutrition/food-labelling/health-claims/diet-related-health-claims.html`
- Nutrient Function Claims page: `https://www.canada.ca/en/health-canada/services/food-nutrition/food-labelling/health-claims/nutrient-function-claims.html`

**Claim status mapping:**
- Disease Risk Reduction Claims → `PERMITTED` (pre-approved under FDR B.01.603)
- Nutrient Function Claims → `PERMITTED` (pre-approved under FDR B.01.500 series)

**Parsing:** both pages use structured HTML tables with substance/food component columns. Parse table rows for ingredient matching.

**Key seeded standards:**
- Food and Drug Regulations (FDR) B.01.603 -- Disease Risk Reduction Claims
- FDR B.01.500-B.01.513 -- Nutrient Function Claims
- Safe Food for Canadians Regulations (SFCR) 2019

**Primary legislation basis:** Food and Drug Regulations (FDR); Food and Drugs Act

---

### Australia -- `au_fsanz.py`

**Authority:** Food Standards Australia New Zealand
**Market enum:** `Market.AU`
**BASE_URL:** `https://www.foodstandards.gov.au`

**Live data source:**
- FSANZ Standard 1.2.7 on legislation.gov.au: `https://www.legislation.gov.au/Series/F2015L00411`

**Claim status mapping:**
- General level health claims → `CONDITIONAL` (must meet nutrient profiling score; claim from pre-approved list in Standard 1.2.7 Schedule 3)
- High level health claims → `PERMITTED` (pre-approved in Schedule 4 of Standard 1.2.7)
- Self-substantiated claims → `NOT_DEFINED` (not in pre-approved lists)

**Parsing:** legislation.gov.au renders the standard as structured HTML. Parse Schedule 3 and Schedule 4 tables for food-health relationships and permitted claim text.

**Key seeded standards:**
- Standard 1.2.7 -- Nutrition, Health and Related Claims
- Standard 1.2.8 -- Nutrition Information Requirements
- Australia New Zealand Food Standards Code

**Primary legislation basis:** Standard 1.2.7 (Food Standards Code); Food Standards Australia New Zealand Act 1991

---

## Tests

One `TestXXXSource` class per connector added to `tests/test_sources.py`. Tests make live network calls (consistent with Codex/EU pattern). ~8 tests per connector:

1. `test_market_is_xx` -- market enum check
2. `test_search_[ingredient]_permitted` -- PERMITTED path
3. `test_search_[ingredient]_conditional` -- CONDITIONAL path (where applicable)
4. `test_search_unknown_not_defined` -- fallback, no crash
5. `test_get_standard_[primary_id]` -- seeded standard lookup
6. `test_search_standards_returns_list` -- seeded list
7. `test_market_overview` -- static data
8. `test_cache_populated_after_search` -- verify `_cache is not None` after first call

Total: ~32 new tests, suite grows from 38 → ~70.

## models.py -- Add Missing Market Enums

`Market.JP`, `Market.US`, and `Market.CA` do not exist yet. Add to `src/mcp_food_regulatory/models.py` Market enum:

```python
US = "us"       # United States
JP = "jp"       # Japan
CA = "ca"       # Canada
```

`Market.AU` already exists. This must happen before any connector can use these enums.

## Server Registration

### Imports added to `server.py`

```python
from mcp_food_regulatory.sources.jp_caa import JPCAASource
from mcp_food_regulatory.sources.us_fda import USFDASource
from mcp_food_regulatory.sources.ca_health_canada import CAHealthCanadaSource
from mcp_food_regulatory.sources.au_fsanz import AUFSANZSource
```

### SOURCES dict

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

### list_markets() -- move to implemented

`au`, `us`, `ca`, `jp` moved from `planned_contributions_welcome` to `implemented`.

### FastMCP instructions string

Updated to include: `jp (Japan CAA), us (US FDA), ca (Health Canada), au (FSANZ)`

## Commit Strategy

5 commits total:
1. `feat: add Japan CAA connector (jp_caa.py)` -- connector + tests
2. `feat: add US FDA connector (us_fda.py)` -- connector + tests
3. `feat: add Health Canada connector (ca_health_canada.py)` -- connector + tests
4. `feat: add FSANZ connector (au_fsanz.py)` -- connector + tests
5. `feat: register Batch 1 connectors in server.py` -- server.py + CLAUDE.md + AGENTS.md

## CLAUDE.md / AGENTS.md Update

```
## Current status
Codex + EU + PH FDA + JP + US + CA + AU implemented.
Batch 1 complete. Next batch: br_anvisa.py, kr_mfds.py, sa_sfda.py
```
