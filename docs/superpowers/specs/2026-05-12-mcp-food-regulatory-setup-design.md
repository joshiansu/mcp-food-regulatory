# mcp-food-regulatory: Setup & Philippines FDA Connector Design

**Date:** 2026-05-12
**Status:** Approved

## Overview

Set up the mcp-food-regulatory git repo from its scaffolded zip, add the Philippines FDA market connector, get all tests passing, and add agent context docs.

## Approach

Two-commit flow (Approach B):
- **Commit 1** -- scaffold repo from zip (`chore: initial scaffold -- Codex + EU sources`)
- **Commit 2** -- Philippines FDA connector + tests + doc updates (`feat: add Philippines FDA market connector`)

## Commit 1: Repo Scaffold

Unpack `files.zip` into the correct `src/` layout required by `pyproject.toml`:

```
mcp-food-regulatory/
├── CLAUDE.md
├── CONTRIBUTING.md
├── README.md
├── pyproject.toml
├── src/
│   └── mcp_food_regulatory/
│       ├── __init__.py
│       ├── server.py
│       ├── models.py
│       └── sources/
│           ├── __init__.py
│           ├── base.py
│           ├── codex.py
│           ├── eu.py
│           └── template.py
└── tests/
    ├── __init__.py
    └── test_sources.py
```

`__init__.py` files are empty. No other changes to the existing source files.

## Commit 2: Philippines FDA Connector

### Authority

Philippines Food and Drug Administration -- `https://www.fda.gov.ph`

Note: `pfda.doh.gov.ph` in the template is incorrect -- that is the Philippine Fisheries Development Authority, a separate agency.

### Primary Legislation (for seed data basis)

- FDA Circular No. 2014-007 -- Supplemental Guidelines on Health and Nutrient Claims for Food Products (primary health claims framework, PH equivalent of EC 1924/2006)
- Republic Act 3720 -- Food, Drug and Cosmetic Act (foundational law)
- DOH Circular No. 2013-010 -- 10 Herbal Plants Endorsed by the Department of Health (for botanical claims)

### Implementation Strategy: Seeded + Best-effort Live

- `search_health_claims()` -- seeded only, deterministic
- `get_standard()` -- seeded for known circulars, returns None for unknown
- `search_standards()` -- attempts live fetch of `fda.gov.ph/food-regulations/`, falls back to seeded circular list on failure
- `get_market_overview()` -- static

### Seeded Ingredients

| Ingredient | Claim Type | Status | Regulatory Basis |
|---|---|---|---|
| Vitamin D | nutrient_function | PERMITTED | FDA Circular 2014-007, Schedule 2 |
| Calcium | nutrient_function | PERMITTED | FDA Circular 2014-007, Schedule 2 |
| Iron | nutrient_function | PERMITTED | FDA Circular 2014-007, Schedule 2 |
| Zinc | nutrient_function | PERMITTED | FDA Circular 2014-007, Schedule 2 |
| Dietary fibre | nutrition_claim | CONDITIONAL | FDA Circular 2014-007, Schedule 1 (min. content threshold applies) |
| Probiotics (Lactobacillus) | function_claim | CONDITIONAL | FDA Circular 2014-007, Schedule 3 |
| Omega-3 / fish oil | nutrient_function | CONDITIONAL | FDA Circular 2014-007, Schedule 2 |
| Moringa / malunggay | traditional_herbal | CONDITIONAL | DOH Circular 2013-010 (limited to traditional function claims) |
| Caffeine | health_claim | NOT_DEFINED | No specific provision in FDA Circular 2014-007 |
| Inulin | prebiotic | NOT_DEFINED | No prebiotic claim authorization in PH |
| Coconut oil / VCO | health_claim | NOT_DEFINED | FDA advisory against unsubstantiated claims |
| Taro | health_claim | NOT_DEFINED | No specific provision |

### Seeded Standards (fallback for `search_standards`)

- FDA Circular No. 2014-007 -- Health and Nutrient Claims
- Republic Act 3720 -- Food, Drug and Cosmetic Act
- DOH Circular 2013-010 -- 10 Herbal Plants
- FDA Administrative Order 88-B s.1984 -- Food Regulations
- FDA Memorandum Circular 2020-005 -- Labeling Requirements

### Server Update

Move `"ph"` from `planned_contributions_welcome` to `implemented` in `list_markets()` tool.
Add `PhFDASource` to the `SOURCES` dict in `server.py`.

### Tests Added (`TestPHFDASource` in `test_sources.py`)

- `test_market_is_ph`
- `test_search_vitamin_d_permitted`
- `test_search_moringa_conditional`
- `test_search_inulin_not_defined`
- `test_search_caffeine_not_defined`
- `test_get_standard_circular_2014_007`
- `test_search_standards_returns_list`
- `test_market_overview`
- `test_unknown_ingredient_no_crash`

All tests use seeded data only -- no network calls, no mocking needed.

### Docs

- `CLAUDE.md` -- update Current Status: mark PH done, MY/AU still pending
- `AGENTS.md` -- create with same content as CLAUDE.md (for OpenAI Codex and other agent runtimes)
