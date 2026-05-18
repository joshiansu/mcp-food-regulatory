# Future Scope -- mcp-food-regulatory

**Audience:** Regulatory affairs professionals at food companies  
**Principle:** Depth over breadth. Trustworthy data over wide coverage. Compliance risk drives priority.  
**Date:** 2026-05-18

---

## What this server does well today

23 markets implemented. 6 tools. FastMCP + Supabase call logging. Deployed on Vercel.
The seeded-data connector pattern works: it is fast, offline-capable, easy to contribute to,
and covers the most common orientation queries (is this claim type permitted in this market?).

The foundation is solid. The gap is depth, not architecture.

---

## Honest gaps

| Gap | Impact |
|-----|--------|
| 16 of 23 markets have no automated tests | Regressions in data go undetected |
| No staleness or confidence metadata on any response | Professional can't know if data is 2 months or 3 years old |
| `AdditiveStatus` model exists but every market returns `None` | Tool exists, answers nothing |
| Allergen labelling is absent from every market | Highest-risk compliance domain completely uncovered |
| Seeded data updated only via code PRs | Regulatory professional who spots an error cannot fix it |
| Label compliance verdict tool does not exist | Server gives raw data; professional synthesises by hand |

---

## Priority 1 -- Foundation: Make the data trustworthy

### 1a. Test coverage for all 23 markets

Only 7 markets have tests. The 16 added in batches 2 and 3 are untested.

**What to build:**
Parametrised test class in `tests/test_sources.py` that runs the same five assertions against every market in `SOURCES`:
1. `get_market_overview()` returns a non-empty `MarketOverview`
2. `search_health_claims("calcium")` returns at least one `ClaimResult`
3. `search_standards("")` returns a non-empty list
4. `get_standard` returns a result for at least one known standard ID per market
5. No connector raises an unhandled exception on the above calls

**Effort:** ~3 hours. Parametrise existing test patterns -- no new code paths.

---

### 1b. Confidence and staleness metadata

A regulatory professional needs to know: how fresh is this answer? Who verified it?

**What to build:**

Add two fields to `ClaimResult` and `Standard`:

```python
data_confidence: Literal["seeded", "live", "official_download"]
# seeded          = hand-written by a contributor; treat as orientation only
# live            = fetched from the authority website at query time
# official_download = parsed from an official structured file (e.g. EU Excel register)

verified_date: str | None   # ISO date when last confirmed correct
staleness_warning: bool      # True if verified_date is absent or >12 months old
```

Surface `staleness_warning: true` prominently in every tool response that has stale data.
Update all 23 connectors to set `data_confidence = "seeded"` and `verified_date` to the actual date the data was written.

**Effort:** 1 day. Model change + propagation through all connectors.

---

### 1c. Supabase as the canonical write path

**The problem:** Updating a seeded claim requires a Python code PR. A regulatory professional
who spots an error -- or a contributor in a market -- cannot fix it without a developer.

**What to build:**

Add two Supabase tables as the correction/update layer:

```sql
regulatory_claims(
  id, market, ingredient, claim_type, status, conditions,
  instrument, url, verified_date, confidence, updated_by, updated_at
)
regulatory_standards(
  id, market, standard_id, title, category, adopted,
  last_amended, summary, full_text_url, updated_by, updated_at
)
```

Each connector's `search_health_claims` and `get_standard` check Supabase first.
If a Supabase row exists for that market+ingredient, it takes precedence over the Python dict.
If Supabase is unavailable (no env vars), fall back to the Python dict transparently.

**The Python dicts become the bootstrap seed, not the ongoing source of truth.**
Add a comment to every `_CLAIM_PROVISIONS` dict: `# Read-only seed -- corrections go to Supabase`.
Add `scripts/seed_supabase.py` to do a one-time migration of all seeded data to Supabase.

This gives regulatory professionals a non-code path to submit corrections via Supabase dashboard,
and the Python dicts remain as a reliable offline fallback.

**Effort:** 2-3 days. Largest structural change -- highest leverage.

---

## Priority 2 -- Regulatory Change Tracking

The most common panic for a regulatory affairs professional is: "Did something change and I missed it?"
No tool in this server addresses that. A professional launching an export into the EU or JP
has no way to ask "what changed in the last 6 months?" or set a watch on a market.

### New tool: `get_regulatory_updates(market, since_date)`

```python
get_regulatory_updates(market: str, since_date: str) -> dict
# Returns known regulatory changes for a market since the given ISO date.
# Fields: change_type, summary, effective_date, instrument, url, confidence.
```

### Data model

```python
class RegulatoryUpdate(BaseModel):
    market: Market
    change_type: Literal["new_claim_permitted", "claim_prohibited", "standard_amended",
                         "new_legislation", "enforcement_change"]
    summary: str
    effective_date: str | None
    instrument: str
    url: str | None
    data_confidence: Literal["seeded", "live", "official_download"]
    verified_date: str | None
```

### Data storage

Regulatory updates are seeded manually from verified official sources and stored in a Supabase
`regulatory_updates` table (with Python dict fallback for offline use). This is intentionally
not automated -- parsing regulatory announcement feeds is unreliable; a curated human-verified
log is more trustworthy than a scraped one.

Seed with the 10-15 most significant changes in the last 3 years for the highest-risk markets
(EU, US, AU, JP, CA) at launch. Contributors can add entries via Supabase dashboard.

Notable changes to seed immediately: US sesame mandate (FASTER Act, Jan 2023),
EU front-of-pack nutrition labelling proposal status, AU/NZ pregnancy warning requirements.

**Effort:** 2 days. New model + 1 tool + Supabase table + initial seed for 5 markets.

---

## Priority 3 -- Allergen Labelling (Highest Compliance Risk)

Allergen mislabelling triggers product recalls and fatalities. It is the highest-risk
compliance domain for any food company and is completely absent from this server.
This is a more critical gap than any missing market.

### The domain

Every market has a list of major allergens that must be declared, specific wording rules,
and precautionary labelling rules ("may contain"). These differ materially:

| Market | Major allergens | Precautionary |
|--------|----------------|---------------|
| EU | 14 (incl. lupin, molluscs, sulphites) | Voluntary; must not be misleading |
| US | Big 9 (sesame added 2023 under FASTER Act) | Voluntary; FALCPA-governed |
| AU/NZ | 10 (tree nuts as a group; sesame) | Mandatory if risk reasonably foreseeable |
| JP | 7 mandatory + 20 recommended | Specific prescribed wording per allergen |
| CA | 11 (incl. mustard, sesame) | Mandatory precautionary for 7 priority allergens |
| IN | 8 (FSSAI (Labelling) Regulations 2020) | Required declaration |
| CN | 8 recommended per GB 7718-2011 Annex C | Recommended; not mandatory |
| KR | 22 mandatory (most comprehensive in Asia) | Mandatory |

**Note on thresholds:** For most markets, allergen declaration is required whenever an allergen
is intentionally present as an ingredient -- there is no "safe level" below which declaration
is optional. The EU sulphites rule (>10mg/kg SO₂ equivalent) is one of the rare threshold-based
exceptions. Do not confuse declaration thresholds with claim thresholds: the EU "gluten-free"
claim threshold (≤20ppm) governs when a *claim* may be made, not when *declaration* is required.

### New model: `AllergenRequirement`

```python
class AllergenRequirement(BaseModel):
    market: Market
    allergen: str                             # "gluten", "peanut", "lupin", "sesame", ...
    mandatory: bool                           # Must be declared if present above threshold
    recommended: bool                         # Recommended but not legally required
    declaration_threshold: Optional[str]      # "≥20 ppm" (gluten EU), "any detectable level"
    required_wording: Optional[str]           # Exact prescribed wording (JP, KR)
    precautionary_rules: Optional[str]        # "may contain" / "produced in a facility" rules
    precautionary_mandatory: bool             # Is precautionary labelling legally required?
    basis: RegulatoryBasis
    data_confidence: Literal["seeded", "live", "official_download"]
    verified_date: Optional[str]
```

### New tools

```python
get_allergen_requirements(market: str, allergen: str | None = None) -> dict
# Returns full allergen list for a market, or details for a specific allergen.

compare_allergen_requirements(allergen: str, markets: list[str]) -> dict
# Cross-market comparison for one allergen -- "is sesame mandatory in US, EU, AU, JP?"
```

### Data storage

**Use the same two-layer pattern as all other connectors.** Python dicts are the offline fallback;
Supabase rows override them when available. The server runs in stdio mode without a guaranteed
network connection, so Supabase-only storage would break offline usage.

```python
# Each connector checks Supabase first; falls back to Python dict if unavailable.
_ALLERGEN_PROVISIONS: dict[str, dict] = {
    "gluten": { ... },   # offline seed
    "peanut": { ... },
    ...
}
```

Add a Supabase `allergens` table as the correction/update layer:

```sql
allergens(
  id, market, allergen, mandatory, recommended, declaration_threshold,
  required_wording, precautionary_rules, precautionary_mandatory,
  basis_instrument, basis_url, verified_date, confidence
)
```

If a Supabase row exists for that market+allergen, it takes precedence.
If Supabase is unavailable, the Python dict is returned transparently.
Add `scripts/seed_allergens.py` for the initial Supabase load.

**Priority markets for initial data:** EU, US, AU, JP, CA, IN, CN, KR.
Covers the highest-volume food export markets. BR, SA, KR, ZA in follow-up.

**Effort:** 3-4 days. New model + 2 tools + Supabase seed for 8 markets.

---

## Priority 4 -- Additive Permissions (Codex GSFA + EU Register)

The `AdditiveStatus` model and `get_additive_status` tool exist but every market returns `None`.
The Codex GSFA and EU additive register are both published as downloadable structured files --
the cleanest regulatory datasets in the world. Not using them is a waste.

### Phase A -- Codex GSFA (downloadable Excel/CSV)

The Codex GSFA is available as a downloadable structured dataset at `fao.org/gsfaonline`.
Parse the official Excel export and load to Supabase on a scheduled refresh.

Answers: "Is [additive] permitted in [food category] under Codex, and at what maximum level?"

```python
# CodexSource.get_additive_status("carrageenan", "infant_formula")
# → AdditiveStatus(permitted=False, basis="CXS 192-1995 Table 1 -- not listed for infant formula")
```

**Parsing caveat:** The GSFA Excel export is a complex multi-sheet workbook with conditional
maximum levels, footnotes, and food category hierarchy encoded across columns. Initial parsing
and data normalisation is closer to 1 week, not 2 days. The scheduled refresh mechanism also
needs to be described: a Vercel cron job that downloads, parses, and upserts to Supabase,
with a checksum guard to skip unchanged exports. Plan for this explicitly before starting.

### Phase B -- EU Additive Register (downloadable)

EU Commission publishes authorised food additives as a structured Excel file at:
`food.ec.europa.eu/food-safety/food-improvement-agents/additives_en`

Parse and load to Supabase. Lookup by E-number or additive name.

```python
# EUSource.get_additive_status("E407 carrageenan", "infant_formula")  
# → AdditiveStatus(permitted=False, conditions="Not listed in Annex II for infant formulae")
```

### Phase C -- Key market seeded data

US (21 CFR Part 172-178 + GRAS list), AU/NZ (FSANZ Schedule 8), JP (MHL Ministry list).
These are best served as seeded data since they don't have clean download endpoints.
Focus on the 50 highest-frequency food additives (emulsifiers, preservatives, sweeteners, colours).

**Effort:** Phase A: 2 days. Phase B: 2 days. Phase C: 3 days.

---

## Priority 5 -- Label Compliance Checker

Once Priorities 1-3 are in place, a compliance checker synthesises all three domains
into an actionable verdict. This is the single highest-value tool for a regulatory professional.

### New tool: `check_label_compliance(product, markets)`

**Design principle:** Works with partial inputs. A product can have only claims checked,
or only allergens, or all three. Each domain check is independent.

**Input:**

```json
{
  "product_name": "Omega-3 Capsules",
  "markets": ["eu", "us", "au"],
  "claims": [
    {"type": "health_claim", "text": "EPA and DHA contribute to normal heart function"},
    {"type": "nutrition_claim", "text": "High in Omega-3"}
  ],
  "allergens_present": ["fish"],
  "additives": [
    {"name": "carrageenan", "food_category": "dietary_supplement"}
  ]
}
```

**Output per market:**

```json
{
  "market": "eu",
  "verdict": "non_compliant",
  "blockers": [
    {
      "domain": "health_claim",
      "detail": "Heart function claim for EPA+DHA requires ≥250mg EPA+DHA per daily serving per EU 432/2012. Cannot verify without nutrition facts.",
      "basis": "EU 432/2012 + EC 1924/2006 Art.13(1)"
    }
  ],
  "warnings": [
    {
      "domain": "allergen",
      "detail": "Fish must be declared in bold in the ingredient list per EU 1169/2011 Annex II. Ensure 'fish' appears in bold in the full ingredient declaration."
    }
  ],
  "passed": [
    {"domain": "additive", "detail": "Carrageenan is permitted in dietary supplements under EU additive regulations."}
  ]
}
```

**What this is NOT:** A label text generator. Output is a structured gap analysis -- issues and their regulatory basis -- not generated label copy.

**Effort:** 3-4 days. Orchestration logic only -- no new data. Requires Priorities 3 and 4.

---

## Priority 6 -- Remaining Markets (with full domain coverage)

After the foundation is solid and three domains are implemented, new markets get health claims
+ allergens + additives from day one -- not just the shallow seeded connector.

Priority order by regulatory data accessibility and commercial importance:

| Market | Code | Authority | Why now |
|--------|------|-----------|---------|
| Malaysia | MY | MOH / Kementerian Kesihatan | Large Muslim-majority market; halal intersects with claims |
| Indonesia | ID | BPOM | 4th most populous country; BPOM increasingly active |
| Vietnam | VN | MOH / MARD | Fast-growing; ASEAN export hub |
| Thailand | TH | Thai FDA | ASEAN hub; relatively structured data |
| United Kingdom | GB | FSA / FSS | Post-Brexit EU divergence growing; own health claims register |
| Turkey | TR | KKGM | EU-candidate; large export market; structured data |
| Argentina | AR | ANMAT | Major LATAM market; Codex-aligned |
| Nigeria | NG | NAFDAC | Largest African economy; hardest to scrape |

**Effort:** 2-3 days per market with full domain coverage (vs. 1 day for health-claims only).

---

## What is explicitly out of scope

- **Natural language / RAG / semantic search** -- the MCP tool interface is the right abstraction for regulatory professionals; they know what they're looking for
- **Organic / sustainability certification** -- a different authority structure, not health-claim adjacent
- **Country-of-origin labelling** -- important but a separate regulatory domain; candidate for a future sibling server
- **Halal / Kosher certification** -- certification body landscape is too fragmented for structured data at this time
- **Generated label copy** -- the compliance checker produces gap analysis verdicts, not label text

---

## Execution order

```
Phase 1  Tests + confidence metadata + Supabase write path                (1 week)
Phase 2  Regulatory updates tool + Supabase table + 5 markets seeded      (2 days)
Phase 3  Allergen model + 2 tools + 8 markets (dict + Supabase)           (1 week)
Phase 4  Additive permissions: Codex GSFA + EU register + 3 seeded        (2.5 weeks)
Phase 5  Label compliance checker tool                                     (1 week)
Phase 6  MY, ID, VN, TH, GB, TR -- full domain coverage each              (ongoing)
```

Each phase ships independently and adds value without the next phase.

---

## Success metrics

| Phase | Metric |
|-------|--------|
| 1 | 100% markets have automated tests; every response includes `data_confidence` and `staleness_warning` |
| 2 | `get_regulatory_updates("us", "2023-01-01")` returns the sesame mandate (FASTER Act, effective Jan 2023) |
| 3 | `get_allergen_requirements("eu", "gluten")` returns correct bold wording requirement and regulation reference; offline fallback works without Supabase |
| 4 | `get_additive_status("carrageenan", "infant_formula", "codex")` returns correct "not permitted" verdict from GSFA |
| 5 | `check_label_compliance` correctly identifies at least one blocker for a product with a known EU compliance issue |
| 6 | 30+ markets with health claims + allergens + additives all returning non-empty, tested data |
