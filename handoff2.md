# Handoff 2 -- South Asian Connectors (In Progress)

**Date:** 2026-05-18
**Branch:** main
**Status:** PARTIALLY COMPLETE -- session ended mid-task

---

## Context

The user asked to add all South Asian countries from `regulatory_data_sources.xlsx`.
After handoff1.md (which covered 10 markets: IN, CN, KR, BR, CO, CL, MX, AE, SA, ZA),
this session started work on the 6 remaining South Asian markets: PK, BD, LK, NP, BT, MV.

---

## What was completed this session

### 1. Excel file updated
`regulatory_data_sources.xlsx` now has 21 data rows (was 15).
Rows added: PK, BD, LK, NP, BT, MV -- all with authority, regulations, URLs, scrape difficulty, and strategy notes.

### 2. `models.py` updated
Six new `Market` enum values added (NOT yet committed):

```python
PK = "pk"   # Pakistan / PFA + PSQCA
BD = "bd"   # Bangladesh / BFSA
LK = "lk"   # Sri Lanka / FCAU + SLSI
NP = "np"   # Nepal / DFTQC
BT = "bt"   # Bhutan / BFDRA
MV = "mv"   # Maldives / MFDA
```

### 3. Source files created (NOT yet committed)

| File | Status |
|------|--------|
| `src/mcp_food_regulatory/sources/pk_pfa.py` | DONE |
| `src/mcp_food_regulatory/sources/bd_bfsa.py` | DONE |
| `src/mcp_food_regulatory/sources/lk_fcau.py` | NOT STARTED |
| `src/mcp_food_regulatory/sources/np_dftqc.py` | NOT STARTED |
| `src/mcp_food_regulatory/sources/bt_bfdra.py` | NOT STARTED |
| `src/mcp_food_regulatory/sources/mv_mfda.py` | NOT STARTED |

---

## What still needs to be done

### Step 1 -- Create the 4 remaining source files

Use `src/mcp_food_regulatory/sources/in_fssai.py` as a style reference (same region, similar regulatory complexity).

**`lk_fcau.py` -- Sri Lanka**
- Class: `LKFCAUSource`, `market = Market.LK`
- Authority: Food Control Administration Unit (FCAU) / Sri Lanka Standards Institution (SLSI)
- Key regs: Food Act No. 26 of 1980 (amended); Food (Labelling) Regulations 2005; SLS 516
- URLs: `https://www.health.gov.lk/foodcontrol`, `https://www.slsi.lk`, `https://www.documents.gov.lk/`
- Notes: Codex-aligned; limited positive claim list; claims require FCAU review

**`np_dftqc.py` -- Nepal**
- Class: `NPDFTQCSource`, `market = Market.NP`
- Authority: Department of Food Technology and Quality Control (DFTQC)
- Key regs: Food Act 1966 (2nd Amendment 2017); Food Rules 1970; Food Labelling Directive 2074 BS (= 2017 AD)
- URLs: `http://www.dftqc.gov.np`, `https://www.moald.gov.np`, `https://www.nepallaw.gov.np/`
- Notes: Content primarily in Nepali; Codex-aligned; DFTQC under Ministry of Agriculture

**`bt_bfdra.py` -- Bhutan**
- Class: `BTBFDRASource`, `market = Market.BT`
- Authority: Bhutan Food and Drug Regulatory Authority (BFDRA)
- Key regs: Food Safety and Quality Act 2005; Food Safety Rules and Regulations 2016
- URLs: `https://www.bfdra.gov.bt`, `https://www.nab.gov.bt/`
- Notes: Very small market; follows WHO/Codex; minimal health-claim-specific regulations

**`mv_mfda.py` -- Maldives**
- Class: `MVMFDASource`, `market = Market.MV`
- Authority: Maldives Food and Drug Authority (MFDA)
- Key regs: Food Safety Act Law No. 8/2019; Food Labelling Regulations
- URLs: `https://www.mfda.gov.mv`, `https://www.parliament.gov.mv/`
- Notes: Very small island market; MFDA est. 2019; Codex-aligned; minimal positive claims list

### Step 2 -- Register all 6 in `server.py`

Add imports after the existing South Asian block (after `za_doh` import):

```python
from mcp_food_regulatory.sources.pk_pfa import PKPFASource
from mcp_food_regulatory.sources.bd_bfsa import BDBFSASource
from mcp_food_regulatory.sources.lk_fcau import LKFCAUSource
from mcp_food_regulatory.sources.np_dftqc import NPDFTQCSource
from mcp_food_regulatory.sources.bt_bfdra import BTBFDRASource
from mcp_food_regulatory.sources.mv_mfda import MVMFDASource
```

Add to `SOURCES` dict:

```python
Market.PK: PKPFASource,
Market.BD: BDBFSASource,
Market.LK: LKFCAUSource,
Market.NP: NPDFTQCSource,
Market.BT: BTBFDRASource,
Market.MV: MVMFDASource,
```

Update the server instructions string to include the new market codes.

### Step 3 -- Verify

```bash
uv run python -c "from mcp_food_regulatory.server import SOURCES; print([m.value for m in SOURCES])"
uv run pytest tests/ -v
```

### Step 4 -- Commit and push

```bash
git add regulatory_data_sources.xlsx src/mcp_food_regulatory/models.py \
  src/mcp_food_regulatory/server.py \
  src/mcp_food_regulatory/sources/pk_pfa.py \
  src/mcp_food_regulatory/sources/bd_bfsa.py \
  src/mcp_food_regulatory/sources/lk_fcau.py \
  src/mcp_food_regulatory/sources/np_dftqc.py \
  src/mcp_food_regulatory/sources/bt_bfdra.py \
  src/mcp_food_regulatory/sources/mv_mfda.py \
  handoff2.md

git commit -m "feat: add South Asian market connectors (PK, BD, LK, NP, BT, MV)"
git push origin main
```

---

## Implementation pattern reminder

All source files follow this structure (see `in_fssai.py` for closest reference):

```python
_KNOWN_STANDARDS: dict[str, dict] = { ... }   # 2-3 key regulations
_CLAIM_PROVISIONS: dict[str, list[dict]] = { ... }  # vitamin c, vitamin d, calcium, dietary fibre

class XYZSource(RegulatorySource):
    market = Market.XY
    BASE_URL = "..."

    async def search_health_claims(self, ingredient, claim_type=None): ...
    async def get_standard(self, standard_id): ...
    async def search_standards(self, query): ...
    async def get_market_overview(self): ...
```

For BT and MV (very small markets with minimal regulations), seeded provisions can be
minimal -- just note Codex alignment and direct to the authority portal.
