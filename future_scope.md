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

## Decision matrix

*Effort = calendar time to ship with one developer. Impact = value delivered to a regulatory professional on completion.*

| Feature | Effort | Impact | Dependencies | Verdict |
|---------|--------|--------|--------------|---------|
| Test coverage (all 23 markets) | 3 hours | Low (infra) | -- | Build now -- hygiene |
| Staleness + confidence metadata | 1 day | Medium (trust) | -- | Build now -- trust signal |
| Nutrient content claim thresholds | 2-3 days | **High** | -- | **Build now -- fast win** |
| Regulatory change tracking | 2 days | **High** | Supabase table | Build now -- highest-anxiety professional need |
| Product classification | 3-4 days | **Very high** | -- | Build soon -- foundational for compliance checker |
| FOPNL | 3-4 days | **High** | -- | Build soon -- legislation moving fast; feeds compliance checker |
| Allergen labelling | 1 week | **Very high** | -- | Build soon -- highest compliance risk domain |
| Label compliance checker v1 | 3-4 days | **Very high** | Classification + FOPNL + Allergen | Build after those three -- ships before additives |
| Fiscal levies (SSB/sodium tax) | 2-3 days | Medium | -- | Fill-in -- fast, narrower audience |
| EU additive register | 2 days | High | -- | Plan -- cleaner dataset; do before GSFA |
| Codex GSFA | 1+ week | High | -- | Plan carefully -- complex multi-sheet Excel parsing |
| Label compliance checker v2 | 2-3 days | **Very high** | v1 + additive permissions | Plan -- adds additive domain once data exists |
| Supabase write path | 2-3 days | Low direct | Supabase tables | Defer -- enables contributor corrections but no new user capability |
| Remaining markets | 2-3 days each | Medium | Foundation phases | Ongoing |

**Key decision:** Label Compliance Checker does not need additive data to ship a first version. Classification + FOPNL + Allergen alone are enough for a useful v1. Additive permissions unlock v2.

**Key deferral:** Supabase write path is infrastructure that enables non-developer corrections. It does not add user-visible capability. Defer until after the high-impact domains are seeded.

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

## Priority 1 -- Foundation: Tests and Trust Signals

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

**Output design note (questionnaire, 2026-05-19):** The primary user wants to see the
regulation name, its publication date, and an "is this the latest version?" signal -- all
inline, not as a separate field to find. Format the tool output so `governing_instrument`
and `verified_date` appear adjacent, e.g.:
`"basis": "Food Safety and Quality Act 2005 -- last verified 2024-03-12 (may be outdated)"`
The staleness warning must be readable in a single glance, not buried.

**Effort:** 1 day. Model change + propagation through all connectors.

---

### 1c. Supabase as the canonical write path *(deferred -- see Priority 12)*

This is infrastructure that enables non-developer corrections to seeded data. It adds no
user-visible capability on its own. Deferred until high-impact domains are seeded and
the cost of a code PR for corrections becomes a real bottleneck.

**Effort when done:** 2-3 days. Full design retained in Priority 12 below.

---

## Priority 2 -- Nutrient Content Claims (Fast Win)

**Why now:** Fastest high-impact feature with zero dependencies. The most common question
from a regulatory generalist is not "is this claim permitted?" but "what does my product
need to qualify?" -- and the current server cannot answer it. Well-documented thresholds
in official regulation text; no complex parsing required.

### New model: `NutrientClaimThreshold`

```python
class NutrientClaimThreshold(BaseModel):
    market: Market
    nutrient: str                 # "protein", "fibre", "omega-3", "vitamin_c", ...
    claim_type: str               # "source_of", "high_in", "reduced", "low", "free", "no_added"
    claim_wording: str            # Exact permitted wording for this market
    threshold_value: str          # "≥12g/100g or ≥6g/100kcal"
    threshold_basis: str          # "per 100g", "per 100ml", "per serving", "per 100kcal"
    reference_value: str | None   # NRV or daily reference used (if % threshold)
    conditions: str | None        # "solid food only", "must also be low in fat", ...
    governing_instrument: str
    data_confidence: Literal["seeded", "live", "official_download"]
    verified_date: str | None
```

### Key divergences (sample)

| Claim | EU | US | AU/NZ | IN |
|-------|----|----|-------|-----|
| "Source of protein" | ≥12g/100g or ≥6g/100kcal | General substantiation only | ≥10g/serve and ≥5% energy | ≥10g/100g |
| "High in fibre" | ≥6g/100g or ≥3g/100kcal | ≥20% DV/serving | ≥4g/serve | ≥6g/100g |
| "No added sugar" | No sugars of any kind added | No added sugars as ingredients | No added sugars or concentrated sugars | No added sugars (incl. honey, syrups) |
| "Reduced fat" | ≥30% less than reference food | ≥25% less than reference food | ≥25% less | ≥25% less |

### New tools

```python
get_nutrient_claim_thresholds(market: str, nutrient: str | None = None) -> dict
# All thresholds for a market, or thresholds for a specific nutrient

compare_nutrient_claim_thresholds(nutrient: str, claim_type: str, markets: list[str]) -> dict
# Cross-market comparison -- "what does 'high in fibre' require in EU, US, AU, IN?"
```

**Priority ingredients for initial seed (questionnaire, 2026-05-19 -- beverages user):**

1. **Sugar-free / no added sugar / no added sugars** -- highest priority. Definitions diverge
   significantly and directly intersect SSB tax thresholds: a product reformulated to drop
   below a tax tier may simultaneously gain or lose a sugar claim.
2. **Prebiotics** -- no EU-approved health claim exists for "prebiotics" as a generic term
   (specific substances like inulin/FOS have individual claims; the category term does not).
   Most ASEAN markets are similarly silent. Seed with accurate status ("not approved as generic
   term; substance-specific claims only") rather than returning an empty result.
3. **Vitamins / minerals** -- standard; seed for all 7 initial markets.
4. **Protein, fibre** -- standard; diverging thresholds per table above.

**Initial markets:** EU, US, AU, JP, CA, IN, CN + **MY, TH, PH** (added to reflect confirmed
primary user's market set).

**Effort:** 2-3 days. Seeded data for 10 markets.

---

## Priority 3 -- Regulatory Change Tracking

The most common panic for a regulatory affairs professional is: "Did something change and I missed it?"
No tool in this server addresses that. Fast to build -- 2 days -- and the payoff is immediate:
a professional launching an export into the EU or JP can ask "what changed in the last 6 months?"

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

## Priority 4 -- Product Classification and Categorization

*(Moved from Regulatory Generalist Expansion -- now Priority 4 because it is a prerequisite for the Label Compliance Checker v1.)*

**Why here:** Same effort as allergen labelling but it unblocks the compliance checker earlier.
Classification determines which regulatory framework applies -- without it, a compliance check
is ambiguous. 3-4 days, well-documented data, zero dependencies.

### What to build

```python
class ProductCategory(BaseModel):
    market: Market
    category_name: str          # "food supplement", "functional food", "novel food", ...
    regulatory_definition: str
    governing_instrument: str
    approval_required: bool
    approval_pathway: str | None    # "pre-market notification", "pre-market approval", "general food law"
    claims_framework: str           # Which claims framework applies in this category
    labelling_framework: str
    data_confidence: Literal["seeded", "live", "official_download"]
    verified_date: str | None
```

Key market distinctions:

| Market | Classification complexity |
|--------|--------------------------|
| EU | Food supplement (2002/46/EC) vs. novel food (2015/2283) vs. fortified food (1925/2006) -- different approval pathways |
| US | Dietary supplement (DSHEA) vs. conventional food vs. food additive -- determines structure/function vs. health claim eligibility |
| AU/NZ | Standard 1.1.2 category system; complementary medicines are TGA, not FSANZ |
| IN | FSSAI categories (Schedule I-III) + Ayurvedic / nutraceutical split under FSSAI 2022 |
| JP | FOSHU / FFC / FNFC -- three frameworks with distinct claim rules and approval burdens |
| CN | Health food (保健食品, SAMR registration) vs. novel food (新食品原料) vs. conventional |
| KR | Health functional food (건강기능식품) vs. general food -- different ministry, different claims |

### New tools

```python
get_product_categories(market: str) -> dict
# All product categories in a market with definitions and governing instruments

classify_product(market: str, product_description: str, ingredients: list[str]) -> dict
# Returns likely category classification and the questions a regulator would ask to confirm
```

**Effort:** 3-4 days. Seeded data for EU, US, AU, JP, IN, CN, KR.

---

## Priority 5 -- FOPNL (Front of Pack Nutritional Labelling)

*(Moved from Regulatory Generalist Expansion -- now Priority 5 because it feeds the compliance checker and legislation is moving fast in 2025-2026.)*

**Why here:** 3-4 days to build, well-documented threshold data, and a critical input to the
compliance checker. In Chile, Mexico, and Colombia a FOPNL warning legally prohibits health
and nutrient claims on the same pack -- making FOPNL a prerequisite check, not an add-on.

### FOPNL schemes by market

| Market | Scheme | Mandatory? | Claims impact |
|--------|--------|------------|---------------|
| EU | NutriScore (voluntary; proposed mandatory) | Voluntary | D/E score may bar nutrient claims in FR, DE |
| UK | Multiple Traffic Light / GDA hybrid | Voluntary (retailer-driven) | Retailer listing, not legal bar |
| AU/NZ | Health Star Rating | Voluntary | Retail positioning and claims strategy |
| Chile | Octagonal warning labels | **Mandatory** | Warning label prohibits health/nutrition claims on same pack |
| Mexico | Octagonal warning labels (NOM-051) | **Mandatory** | Same prohibition; also prohibits nutrient claims |
| Brazil | Lupa warnings (ANVISA RDC 429/2020) | **Mandatory** | "ALTO EM" triangles; impacts nutrient claims |
| Colombia | Octagonal warning labels | **Mandatory** | Similar to Chile/Mexico |
| India | FSSAI FOPNL (draft) | Proposed mandatory | Under development; expected to impact high-sugar/fat/salt |
| Thailand | Healthier Choice logo | Voluntary | May coexist with or conflict with nutrient claims |

### New model and tools

```python
class FOPNLRequirement(BaseModel):
    market: Market
    scheme_name: str
    mandatory: bool
    governing_instrument: str
    algorithm_basis: str                    # "octagon threshold per 100g", "HSR v5", ...
    trigger_thresholds: dict                # {"sugar": ">22.5g/100g", ...}
    claims_prohibited_when_warning: bool
    logo_available: bool
    data_confidence: Literal["seeded", "live", "official_download"]
    verified_date: str | None

get_fopnl_requirements(market: str) -> dict
check_fopnl_eligibility(market: str, product_nutrition: dict) -> dict
# Returns whether warning labels apply and which claims are therefore prohibited
```

**Effort:** 3-4 days. Seeded data for CL, MX, BR, CO, AU, UK, EU.

---

## Priority 6 -- Allergen Labelling (Highest Compliance Risk)

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

## Priority 7 -- Label Compliance Checker v1

*(Shipped before additive permissions because Classification + FOPNL + Allergen alone are
enough for a useful first version. Additive domain adds in v2.)*

**Why here:** This is the highest-leverage tool -- it synthesises three domains into an
actionable verdict. With Classification (P4), FOPNL (P5), and Allergen (P6) complete,
v1 can ship. Additive data is not required for v1.

### New tool: `check_label_compliance(product, markets)`

**Input:**

```json
{
  "product_name": "Omega-3 Capsules",
  "markets": ["eu", "us", "au"],
  "product_category": "food_supplement",
  "claims": [
    {"type": "health_claim", "text": "EPA and DHA contribute to normal heart function"},
    {"type": "nutrition_claim", "text": "High in Omega-3"}
  ],
  "allergens_present": ["fish"],
  "nutrition_per_100g": {"total_sugars": 0, "fat": 72, "saturated_fat": 12}
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
      "detail": "Heart function claim for EPA+DHA requires ≥250mg EPA+DHA per daily serving per EU 432/2012.",
      "basis": "EU 432/2012 + EC 1924/2006 Art.13(1)"
    }
  ],
  "warnings": [
    {
      "domain": "allergen",
      "detail": "Fish must be declared in bold in the ingredient list per EU 1169/2011 Annex II."
    }
  ],
  "fopnl": {
    "scheme": "NutriScore",
    "mandatory": false,
    "claims_blocked": false
  }
}
```

**This is NOT a label text generator.** Output is a structured gap analysis -- issues and
their regulatory basis -- not generated label copy.

**Effort:** 3-4 days. Orchestration only -- no new data. Requires Priorities 4, 5, 6.

---

## Priority 8 -- Fiscal Levies: SSB Tax and Sodium Tax

*(Fast fill-in -- 2-3 days, medium impact, well-documented data, standalone.)*

**Why here:** Reformulation to avoid a tax tier (e.g. reducing sugar below 8g/100ml in the UK)
directly drives label changes. Regulatory generalists field these questions. Fast to build and
ships independently of the compliance checker.

### What to build

```python
class FiscalLevy(BaseModel):
    market: Market
    levy_name: str
    product_scope: str              # "sugar-sweetened beverages", "savoury snacks", ...
    trigger_nutrient: str           # "total sugars", "added sugars", "sodium"
    tiers: list[dict]               # [{"threshold": "≥8g/100ml", "rate": "£0.24/L"}]
    effective_date: str
    governing_instrument: str
    formulation_threshold: str      # The threshold companies reformulate to stay below
    label_impact: str | None        # Any labelling change triggered by levy tier
    data_confidence: Literal["seeded", "live", "official_download"]
    verified_date: str | None

get_fiscal_levies(market: str | None = None, levy_type: str | None = None) -> dict
check_levy_liability(market: str, product_type: str, sugar_per_100ml: float | None, sodium_per_100g: float | None) -> dict
```

### SSB taxes by market (initial seed)

Markets marked * are active markets for the confirmed primary user of this server (questionnaire, 2026-05-19).

| Market | Tiers | Rate |
|--------|-------|------|
| UK (SDIL) | <5g/100ml exempt; 5-8g lower; ≥8g upper | £0.18/L / £0.24/L |
| Philippines (TRAIN Act) * | Sugar-sweetened vs. HFCS vs. non-caloric | PHP 6/L / 12/L |
| Thailand * | Tiered by sugar content (excise) | Multiple tiers -- research needed |
| Malaysia * | SSB levy since 2019 (>12g/100ml added sugar) | MYR 0.40/L |
| Indonesia * | Excise on sweetened beverages (PMK 63/2021) | IDR 2,500/L |
| Nigeria * | Excise on non-alcoholic sweetened drinks (Finance Act 2021) | NGN 10/L |
| Ghana * | SSB levy (Health Levy, 2023 Budget) | GHS equivalent -- research needed |
| South Africa | >4g/100ml added sugar | 2.21c/g above 4g threshold |
| Mexico (IEPS) | ≥1kcal/100ml added sugar | 1 peso/L |
| Saudi Arabia | SSBs flat | 50% ad valorem |
| UAE | SSBs flat | 50% ad valorem |
| India | GST on carbonated + sugar | 28% + 12% cess |

**Effort:** 2-3 days. Well-structured official tax authority publications. TH, GH rates marked
"research needed" -- verify against current Finance Ministry publications before seeding.

---

## Priority 9 -- Additive Permissions

The `AdditiveStatus` model and `get_additive_status` tool exist but every market returns `None`.
Build EU register first (cleaner dataset, 2 days), then Codex GSFA (complex parsing, 1+ week).

### Phase A -- EU Additive Register *(do first)*

EU Commission publishes authorised food additives as a structured Excel file at
`food.ec.europa.eu/food-safety/food-improvement-agents/additives_en`.
Parse and load to Supabase. Lookup by E-number or additive name.

```python
# EUSource.get_additive_status("E407 carrageenan", "infant_formula")
# → AdditiveStatus(permitted=False, conditions="Not listed in Annex II for infant formulae")
```

**Effort:** 2 days. One clean structured file, well-labelled columns.

### Phase B -- Codex GSFA *(plan carefully)*

Available as a downloadable dataset at `fao.org/gsfaonline`. Complex multi-sheet workbook
with conditional maximum levels, footnotes, and food category hierarchy across columns.
Parsing and normalisation is closer to 1 week, not 2 days. Requires a Vercel cron job
that downloads, parses, and upserts to Supabase with a checksum guard for unchanged exports.
**Plan the parsing pipeline explicitly before starting.**

```python
# CodexSource.get_additive_status("carrageenan", "infant_formula")
# → AdditiveStatus(permitted=False, basis="CXS 192-1995 Table 1 -- not listed for infant formula")
```

**Effort:** 1+ week. Do not underestimate.

### Phase C -- Key market seeded data

US (21 CFR Part 172-178 + GRAS list), AU/NZ (FSANZ Schedule 8), JP (MHL Ministry list).
Seeded data only -- no clean download endpoints. Focus on the 50 highest-frequency additives
(emulsifiers, preservatives, sweeteners, colours).

**Effort:** 3 days.

---

## Priority 10 -- Label Compliance Checker v2

*(Extends Priority 7 v1 with additive domain. Requires Priority 9 Phase A at minimum.)*

Add additive checks to the existing compliance checker output. No new tool -- extends
`check_label_compliance` input to accept an `additives` list and adds an `"additive"` domain
to the per-market verdict.

```json
"passed": [
  {"domain": "additive", "detail": "Carrageenan (E407) is permitted in dietary supplements under EU Annex II."}
]
```

**Effort:** 2-3 days. Logic only -- depends on additive data from Priority 9.

---

## Priority 11 -- Remaining Markets (full domain coverage)

New markets get health claims + allergens + additives + FOPNL + classification from day one.

Priority order updated to reflect confirmed user market set (questionnaire, 2026-05-19).
The first six markets below are active markets for the known primary user of this server.

| Priority | Market | Code | Authority | Notes |
|----------|--------|------|-----------|-------|
| 1 | Philippines | PH | FDA Philippines | Registered but stub -- fix before building new domains |
| 2 | Malaysia | MY | MOH / NPRA | Structured data; SSB levy since 2019; Healthier Choice adjacent |
| 3 | Thailand | TH | Thai FDA / ACFS | Healthier Choice FOPNL scheme; SSB excise tax; ASEAN hub |
| 4 | Indonesia | ID | BPOM | BPOM increasingly active; SSB tax; 4th most populous country |
| 5 | Vietnam | VN | MOH / MARD | Fast-growing ASEAN export hub |
| 6 | Ghana | GH | FDA Ghana / FDAU | Not previously in scope -- add; SSB levy exists; primary user's market |
| 7 | Nigeria | NG | NAFDAC | Largest African economy; excise on carbonated drinks |
| 8 | United Kingdom | GB | FSA / FSS | Post-Brexit EU divergence growing; own health claims register |
| 9 | Turkey | TR | KKGM | EU-candidate; large export market; structured data |
| 10 | Argentina | AR | ANMAT | Major LATAM market; Codex-aligned |

**Note on PH:** The Philippines connector is registered in `SOURCES` and the `Market.PH` enum
exists, but the class raises `NotImplementedError`. Fix this as an urgent correctness issue --
a broken registered market is worse than an absent one.

**Effort:** 2-3 days per market with full domain coverage.

---

## Priority 12 -- Supabase as the Canonical Write Path *(deferred infrastructure)*

*(Previously Priority 1c -- deferred because it adds no user-visible capability on its own.
Build this once the seeded data volume makes code-PR corrections a real bottleneck.)*

**What to build:**

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

Each connector checks Supabase first; falls back to Python dict transparently if unavailable.
The Python dicts become `# Read-only seed -- corrections go to Supabase`.
Add `scripts/seed_supabase.py` for the one-time migration.

**Effort:** 2-3 days. Enables non-developer corrections via Supabase dashboard.

---

## What is explicitly out of scope

- **Natural language / RAG / semantic search** -- the MCP tool interface is the right abstraction for regulatory professionals; they know what they're looking for
- **Organic / sustainability certification** -- a different authority structure, not health-claim adjacent
- **Country-of-origin labelling** -- important but a separate regulatory domain; candidate for a future sibling server
- **Halal / Kosher certification** -- certification body landscape is too fragmented for structured data at this time
- **Generated label copy** -- the compliance checker produces gap analysis verdicts, not label text

---

## Execution order

Ordered by: impact delivered per day of effort, with fast wins first and dependency-heavy work after its prerequisites.

```
Phase 1   Tests + confidence metadata                                              (2 days)   ← hygiene + trust
Phase 2   Nutrient content claim thresholds: 7 markets seeded                     (2-3 days) ← fast win, standalone
Phase 3   Regulatory change tracking: tool + Supabase table + 5 markets           (2 days)   ← fast win, high need
Phase 4   Product classification: 7 markets seeded                                (3-4 days) ← foundational
Phase 5   FOPNL: 8 markets seeded + check_fopnl_eligibility tool                  (3-4 days) ← prereq for v1 checker
Phase 6   Allergen labelling: 2 tools + 8 markets (dict + Supabase)               (1 week)   ← highest risk domain
Phase 7   Label compliance checker v1 (uses P4 + P5 + P6 -- no additives yet)    (3-4 days) ← highest leverage tool
Phase 8   Fiscal levies: SSB + sodium, 7 markets seeded                           (2-3 days) ← fill-in, standalone
Phase 9   Additive permissions: EU register (Phase A) + key seeded (Phase C)      (1 week)   ← cleaner data first
Phase 10  Codex GSFA parsing (Phase B -- complex, plan pipeline before starting)  (1+ week)  ← plan carefully
Phase 11  Label compliance checker v2 (adds additive domain)                      (2-3 days) ← extends P7
Phase 12  MY, ID, VN, TH, GB, TR -- full domain coverage each                    (ongoing)  ← market expansion
Phase 13  Supabase write path (non-developer corrections)                          (2-3 days) ← deferred infra
```

Each phase ships independently and adds value without the next phase.

**Cumulative unlocks:**
- After Phase 3: 3 fast tools shipped, data is trustworthy, change tracking live
- After Phase 7: Label Compliance Checker v1 live -- the single highest-leverage tool, covering classification + FOPNL + allergen
- After Phase 11: Full compliance checker with additive domain -- complete product

---

## Success metrics

| Phase | Metric |
|-------|--------|
| 1 | 100% of 23 markets have automated tests; every response includes `data_confidence` and `staleness_warning` |
| 2 | `compare_nutrient_claim_thresholds("fibre", "high_in", ["eu", "us", "au"])` returns correct differing thresholds; `get_nutrient_claim_thresholds("eu", "protein")` lists all four claim tiers with exact wording |
| 3 | `get_regulatory_updates("us", "2023-01-01")` returns the sesame mandate (FASTER Act, effective Jan 2023) |
| 4 | `get_product_categories("jp")` returns FOSHU, FFC, and FNFC as distinct frameworks; `classify_product("us", ...)` correctly distinguishes dietary supplement from conventional food |
| 5 | `get_fopnl_requirements("cl")` returns mandatory status and claims prohibition flag; `check_fopnl_eligibility("cl", {"total_sugars": 25})` returns warning applies + health claims prohibited |
| 6 | `get_allergen_requirements("eu", "gluten")` returns bold wording requirement and EU 1169/2011 reference; offline fallback returns data when Supabase is unavailable |
| 7 | `check_label_compliance` on a Chilean product with >22.5g sugar/100g and a health claim returns `non_compliant` with FOPNL as the blocker -- before any claims analysis runs |
| 8 | `check_levy_liability("gb", "carbonated_drink", sugar_per_100ml=9.0)` returns upper tier at £0.24/L |
| 9 | `get_additive_status("E407 carrageenan", "infant_formula", "eu")` returns correct "not permitted" verdict from EU register |
| 10 | `get_additive_status("carrageenan", "infant_formula", "codex")` returns correct "not permitted" verdict from GSFA |
| 11 | `check_label_compliance` correctly flags a carrageenan additive issue in infant formula for the EU market |
| 12 | 30+ markets with health claims + allergens + additives + FOPNL + classification all returning non-empty tested data |
