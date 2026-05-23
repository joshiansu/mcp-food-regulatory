# Handoff 3 -- Roadmap Restructure and Regulatory Generalist Expansion

**Date:** 2026-05-19
**Branch:** main
**Status:** COMPLETE -- documentation session, no code changes

---

## Context

This session was strategic planning, not implementation. A regulatory affairs professional
reviewed the server and proposed four new domains. Their input was incorporated into
`future_scope.md`, which was also reordered using a decision matrix (effort vs. impact).

No source files were changed. No tests were broken. Nothing is partially done.

---

## What changed this session

### 1. `future_scope.md` -- major restructure

**Added:**
- Decision matrix table near the top -- 14 rows scoring every feature on Effort, Impact,
  Dependencies, and verdict (Build Now / Plan / Defer). Two key decisions made explicit:
  - Label Compliance Checker v1 can ship before additive data (Classification + FOPNL +
    Allergen are enough for a useful first version)
  - Supabase write path deferred to Priority 12 (infrastructure with no user-visible value
    on its own)

**Four new domains added (from regulatory generalist input):**
1. Nutrient Content Claim Thresholds -- per-market numeric thresholds for "high in protein",
   "source of fibre", "no added sugar", "reduced fat", etc. New model `NutrientClaimThreshold`,
   two new tools `get_nutrient_claim_thresholds` and `compare_nutrient_claim_thresholds`.
2. Product Classification -- which framework applies to a product (food supplement vs. novel
   food vs. functional food). New model `ProductCategory`, two tools `get_product_categories`
   and `classify_product`. Covers EU, US, AU, JP, IN, CN, KR.
3. FOPNL (Front of Pack Nutritional Labelling) -- NutriScore, octagon warnings, Health Star
   Rating. Critical for Chile, Mexico, Colombia where a warning label legally prohibits health
   and nutrient claims on the same pack. New model `FOPNLRequirement`, two tools
   `get_fopnl_requirements` and `check_fopnl_eligibility`.
4. Fiscal Levies -- SSB tax tiers and sodium tax by market. New model `FiscalLevy`, two tools
   `get_fiscal_levies` and `check_levy_liability`. Initial markets: UK, ZA, MX, PH, IN, SA, UAE.

**Priority reorder (old → new):**

| New | Feature | Effort | Why moved |
|-----|---------|--------|-----------|
| P1 | Tests + confidence metadata | 2 days | Unchanged -- hygiene first |
| **P2** | **Nutrient content claim thresholds** | 2-3 days | Fastest high-impact feature; standalone; zero dependencies |
| **P3** | **Regulatory change tracking** | 2 days | Also fast; high professional need |
| **P4** | **Product classification** | 3-4 days | Foundational prereq for compliance checker |
| **P5** | **FOPNL** | 3-4 days | Feeds compliance checker; legislation moving fast |
| P6 | Allergen labelling | 1 week | Highest risk domain; unchanged priority relative to others |
| **P7** | **Label compliance checker v1** | 3-4 days | Ships after P4+P5+P6 -- no additive data needed |
| **P8** | **Fiscal levies** | 2-3 days | Fast fill-in; standalone; ships anytime |
| P9 | Additive permissions (EU register first, GSFA second) | 1+ week | EU register is 2 days; GSFA is 1+ week -- sequenced correctly |
| **P10** | **Label compliance checker v2** | 2-3 days | Extends v1 with additive domain |
| P11 | Remaining markets | ongoing | Now gets full domain coverage |
| **P12** | **Supabase write path** | 2-3 days | Deferred -- was Priority 1c; no user-visible value standalone |

### 2. `docs/questionnaire-regulatory-generalist.md` -- new file

19-question questionnaire for the regulatory professional whose input drove this session.
Covers: role and market focus, product classification pain points, claims workflow direction
(nutrient-up vs. claim-down), which FOPNL schemes she encounters, whether SSB/sodium tax
reaches her work at all, preferred output format, and open-ended domains not yet covered.

### 3. `docs/create_google_form.gs` -- new file

Google Apps Script that creates the questionnaire as a Google Form. Run it at
script.google.com → New project → paste → Run → createForm. Shareable link appears in
the Execution log.

---

## Questionnaire responses -- key findings (2026-05-19)

Responses received from the regulatory generalist. Raw responses in `docs/questionnaire-regulatory-generalist.md`.
Summary of decisions driven by her input:

### Who she is
In-house regulatory at a food company. **Pure beverages** (carbonated, juice, functional,
plant-based). Works across concept, formulation, and pre-launch stages -- not post-launch
monitoring. Checks all four claim questions (permitted? threshold? wording? substantiation?)
and approaches them claim-down ("I want to say X, what does my product need?").

### Her markets -- the biggest gap
**EU, Malaysia, Indonesia, Vietnam, Philippines, Nigeria, Ghana, Thailand.**

Of those 8 markets, the server currently has:
- EU -- fully implemented
- Philippines -- EXISTS but is a stub (`NotImplementedError`)
- Malaysia, Indonesia, Vietnam, Thailand, Nigeria -- in future scope as P11 but not built
- **Ghana -- not in the server AND not in future scope at all**

This is the most significant finding from the questionnaire. The server covers 23 markets
but misses 6 of the 8 she works in daily. P11 (remaining markets) needs to be accelerated
and reordered around her actual market set, not the theoretical commercial importance list.

### Market priority update for P11

New order based on her markets + Ghana gap:

| Priority | Market | Current status | Notes |
|----------|--------|---------------|-------|
| 1 | Philippines (PH) | Stub -- NotImplementedError | Fix immediately; already registered |
| 2 | Malaysia (MY) | Not built | Her #2 market; structured NPRA/MOH data |
| 3 | Thailand (TH) | Not built | Her #8; also has Healthier Choice FOPNL |
| 4 | Indonesia (ID) | Not built | Her #3; BPOM increasingly active |
| 5 | Vietnam (VN) | Not built | Her #4; ASEAN export hub |
| 6 | Ghana (GH) | Not in server or scope | Her #8; FDAU / FDA Ghana; add to scope |
| 7 | Nigeria (NG) | Not built | Already in P11 scope |
| 8 | United Kingdom (GB) | Not built | Post-Brexit divergence from EU |

### Claims -- what to seed for P2

She named **sugar-free**, **prebiotics**, and **trend-dependent health claims** as her most
complex nutrient/claim categories. For beverages specifically:

- **"Sugar free" / "no added sugar"**: definitions diverge significantly across EU (no sugars
  of any kind added), US (no added sugars as ingredients), AU (no concentrated sugars), and
  ASEAN markets. This is the highest-priority seed for P2. Also directly intersects with SSB
  tax thresholds -- a product reformulated for a lower tax tier may gain or lose a sugar claim.
- **Prebiotics**: No EU-approved health claim exists for "prebiotics" as a category (specific
  substances like inulin have claims; the generic term does not). Japan (FOSHU/FFC) and Korea
  have prebiotic-adjacent claims. ASEAN markets have inconsistent frameworks. This is a domain
  gap -- the server should flag "no approved claim for generic prebiotic term in EU" rather than
  returning an empty result. Seed for EU, JP, KR, TH at minimum with accurate status.
- **Trend claims**: Her note that health claims depend on "trend in market" directly points to
  P3 (Regulatory Change Tracking) -- knowing what was newly approved or restricted in the last
  12 months is exactly what she needs.

### FOPNL -- what she actually encounters

She ticked Health Star Rating (AU/NZ) and Healthier Choice (Thailand/Singapore). She knows
about LATAM octagon restrictions but doesn't work in those markets. For P5:

- **Thailand (Healthier Choice)** is her primary active FOPNL market -- seed this first
- **AU/NZ (HSR)** is secondary but she ticked it -- include in initial seed
- NutriScore and LATAM octagon labels: include for completeness but not her priority

She confirmed she needs the tool to **calculate** eligibility (given nutrition per 100g),
not just describe the framework.

### SSB tax -- directly in scope

Both direct questions (advising on tier) and formulation decisions affecting her label work.
She confirmed she needs sugar → tier → rate mapping, and noted it depends on the framework
(threshold-based vs. flat levy). Her markets for SSB tax:

| Market | Status in P8 seed plan | Her relevance |
|--------|------------------------|---------------|
| Philippines (PH) | Already planned (TRAIN Act) | Yes -- her #5 market |
| Thailand (TH) | Not in current seed list -- add it | Yes -- her #8 market |
| Malaysia (MY) | Not in current seed list -- add it | Yes -- MY SSB levy since 2019 |
| Indonesia (ID) | Not in current seed list -- add it | Yes -- her #3 market |
| Nigeria (NG) | Not in current seed list -- add it | Yes -- excise on carbonated drinks |
| Ghana (GH) | Not in current seed list -- add it | Yes -- GH has SSB levy |

### Trust signal -- what matters most

"References to specific regulation with information on when was it published, is it latest."

This is exactly what `staleness_warning` and `verified_date` (P1b) address. But her phrasing
reveals something more specific: she doesn't just want a warning flag -- she wants to see
the regulation name, its publication date, and a signal that it's the current version. The
`governing_instrument` field already captures the name; `verified_date` captures when it was
last checked; the `staleness_warning` boolean needs to surface prominently in the tool output
alongside the regulation reference, not just as a footer.

### Output format -- confirmed design

Structured verdict with pass/fail/warning + regulation references. She explicitly did NOT
select plain-language summary or comparison table. This validates the current
`check_label_compliance` output design.

### No additional domains

She answered No to Q17 and Q18 -- no domains beyond what's already planned, no markets
with unusually hard-to-find data from her perspective.

---

## What to build next

**P1 -- Tests + confidence metadata** is still the correct starting point.

On confidence metadata: per her Q19 answer, the staleness warning must appear inline next
to the `governing_instrument` field in every tool response, not as a standalone flag. Design
the output so a professional immediately sees "Food Safety and Quality Act 2005 -- verified
2024-03-12, may be outdated" rather than a separate `staleness_warning: true` field they
have to look for.

**PH fix (before P2):** Philippines is registered in `SOURCES` but throws `NotImplementedError`.
She listed PH as her #5 market. Fix it before building new domains -- a broken market in
her core set is worse than a missing one.

**P2 -- Nutrient content claim thresholds:**
Seed priority ingredients (beverages focus):
1. Sugar-free / no added sugar / no added sugars (highest priority -- intersects SSB tax)
2. Prebiotics -- seed as "not approved as generic term in EU; specific substances vary" to
   return an accurate result rather than empty
3. Protein, fibre, vitamins/minerals (standard)

Expand market seed list beyond EU/US/AU/JP/CA/IN/CN to include her markets:
**MY, TH, PH** as additional initial markets for P2 seed data.

Starter checklist for P2:
1. Add `NutrientClaimThreshold` to `models.py`
2. Add `_CLAIM_THRESHOLDS` dict starting with EU, US, AU, JP, PH, MY, TH
3. Register `get_nutrient_claim_thresholds` and `compare_nutrient_claim_thresholds` in `server.py`
4. Add tests in `tests/test_sources.py`

See `future_scope.md` Priority 2 for the full model definition.

**P8 -- Fiscal Levies:** Add MY, TH, ID, NG, GH to the SSB tax seed market list.

---

---

## Current project state

| Dimension | Status |
|-----------|--------|
| Markets | 23 (codex, eu, ph, jp, us, ca, au + 10 batch 2/3 + 6 South Asian) |
| Tools | 6 (list_markets, get_market_overview, search_health_claims, get_standard, search_standards, get_additive_status) |
| Tests | 7 markets covered (batch 1 only) -- 16 untested |
| AdditiveStatus | Model exists; all markets return None |
| Deployment | Vercel (live) |
| Logging | Supabase call log (active) |
| New domains | None implemented yet -- all in future_scope.md |

---

## Files changed this session

```
M  future_scope.md
A  docs/questionnaire-regulatory-generalist.md
A  docs/create_google_form.gs
```

No source files, no models, no tests -- purely planning and documentation.
