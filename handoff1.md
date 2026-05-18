# Handoff 1 -- Batch 2/3 Market Connectors

**Date:** 2026-05-18
**Branch:** main

---

## What was done

Added 10 new market connectors sourced from `regulatory_data_sources.xlsx`, bringing the server from 7 to 17 implemented markets.

### Files changed

| File | Change |
|------|--------|
| `src/mcp_food_regulatory/models.py` | Added 10 new `Market` enum values: `IN, CN, KR, BR, CO, CL, MX, AE, SA, ZA` |
| `src/mcp_food_regulatory/server.py` | Added 10 imports + 10 entries in `SOURCES` dict; updated server instructions string |
| `CLAUDE.md` | Updated current status section |

### New source files (all in `src/mcp_food_regulatory/sources/`)

| File | Market | Authority | Key Regulation(s) |
|------|--------|-----------|-------------------|
| `in_fssai.py` | India | FSSAI | FSS (Advertising & Claims) Regulations 2018, Schedule I & II |
| `cn_nhc.py` | China | NHC / SAMR / NMPA | GB 28050-2011; Decree 51 (27 NHC-approved health food functions) |
| `kr_mfds.py` | South Korea | MFDS | Health Functional Food Act; MFDS HFF Standards (standardised + individually recognised pathways) |
| `br_anvisa.py` | Brazil | ANVISA | RDC 429/2020 (labelling); RDC 432/2020 Annex I (nutrition) & Annex II (health claims) |
| `co_invima.py` | Colombia | INVIMA | Resolución 2508/2012; Decreto 1275/2023 (FOPL); Codex CAC/GL 23 |
| `cl_minsal.py` | Chile | MINSAL / ISP | DS 977/96 RSA Art. 110-115; Ley 20.606 (octagonal warnings) |
| `mx_cofepris.py` | Mexico | COFEPRIS / SSA | NOM-051-SCFI/SSA1-2010 (2020 amendment); NOM-086-SSA1-1994 |
| `ae_esma.py` | UAE | ESMA / Dubai Municipality / ADAFSA | UAE.S 2055; GSO CAC/GL 23; UAE.S GSO 9:2013 |
| `sa_sfda.py` | Saudi Arabia | SFDA | SFDA.FD 9001:2017; GSO CAC/GL 23; GSO 9:2013 |
| `za_doh.py` | South Africa | DoH | R146/2010 Annexure B & C (FCD Act 54/1972) |

---

## Implementation pattern

Each connector follows the same structure as the batch 1 files (eu.py, ca_health_canada.py):

- **`_KNOWN_STANDARDS`** -- seeded dict of key regulations with title, summary, and full-text URL
- **`_CLAIM_PROVISIONS`** -- seeded claims for common ingredients: vitamin C, vitamin D, calcium, dietary fibre, omega-3
- **`search_health_claims()`** -- returns seeded results; falls back to a NOT_DEFINED result with the correct official source URL if the ingredient is not seeded
- **`get_standard()`** -- case-insensitive lookup against `_KNOWN_STANDARDS`
- **`search_standards()`** -- keyword search across seeded standards; returns all if no match
- **`get_market_overview()`** -- static summary of authority, key legislation, and claims framework

---

## Notable market-specific details

- **China (CN):** Two pathways -- general foods use GB 28050-2011 nutrition claims only; health foods (保健食品) require NMPA registration and must use one of 27 NHC-approved function claims. All 27 are seeded in `cn_nhc.py`.
- **South Korea (KR):** Dedicated Health Functional Food (HFF) category separate from general foods. Two pathways: standardised (고시형, no individual approval needed) and individually recognised (개별인정형). GMP certification mandatory.
- **Chile (CL) / Mexico (MX):** Both have front-of-pack octagonal warning systems (Ley 20.606 and NOM-051 2020 respectively). Products bearing warnings cannot use health claims on the front panel.
- **UAE (AE):** Multiple authorities by emirate (ESMA federal, Dubai Municipality, ADAFSA for Abu Dhabi). ESMA databank requires subscription for some standards.
- **South Africa (ZA):** Draft update (R429) has been in consultation for years; R146/2010 remains the operative regulation.
- **Saudi Arabia (SA):** Most structured of the Gulf states; bilingual (Arabic/English) regulations available via SFDA portal.

---

## Verification

```
uv run python -c "from mcp_food_regulatory.server import SOURCES; print([m.value for m in SOURCES])"
# ['codex', 'eu', 'ph', 'jp', 'us', 'ca', 'au', 'in', 'cn', 'kr', 'br', 'co', 'cl', 'mx', 'ae', 'sa', 'za']

uv run pytest tests/ -v
# 74 passed in 27.26s
```

---

## What is NOT done / next steps

- Tests for the 10 new connectors (tests/test_sources.py only covers batch 1 markets)
- Live scraping for markets with accessible structured data (BR/ANVISA claims page, KR/MFDS portal)
- `ph_fda.py` is registered but implemented with a stub (NotImplementedError) -- pre-existing issue
- Markets remaining from template.py suggestions: MY, VN, ID, TH, GB
