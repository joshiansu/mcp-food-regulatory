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
    Market, ClaimResult, ClaimStatus, Standard, MarketOverview, RegulatoryBasis,
    NutrientClaimThreshold, RegulatoryUpdate,
)
from mcp_food_regulatory.sources.base import RegulatorySource
from mcp_food_regulatory.sources.regulatory_updates_seed import get_seeded_updates

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


# Japan nutrient content claim thresholds -- Food Labelling Standards (食品表示基準) 2015
# Chapter 2, Article 7 + Appendix tables for nutrient claims
# Verified against Cabinet Office Order No. 10 (2015) as amended to 2023
_JP_CLAIM_THRESHOLDS: list[dict] = [
    # --- Dietary fibre ---
    {"nutrient": "dietary fibre", "claim_type": "source_of", "claim_wording": "含む/入り (Contains dietary fibre)",
     "threshold_value": "≥3g/100g (solid) or ≥1.5g/100ml (liquid) or ≥1.5g/serving",
     "threshold_basis": "per 100g, per 100ml, or per serving",
     "governing_instrument": "Food Labelling Standards 2015, Appendix Table 12", "verified_date": "2023-12"},
    {"nutrient": "dietary fibre", "claim_type": "high_in", "claim_wording": "高い/豊富 (High in dietary fibre)",
     "threshold_value": "≥6g/100g (solid) or ≥3g/100ml (liquid) or ≥3g/serving",
     "threshold_basis": "per 100g, per 100ml, or per serving",
     "governing_instrument": "Food Labelling Standards 2015, Appendix Table 12", "verified_date": "2023-12"},
    # --- Protein ---
    {"nutrient": "protein", "claim_type": "source_of", "claim_wording": "含む/入り (Contains protein)",
     "threshold_value": "≥8.1g/100g (solid) or ≥4.1g/100ml (liquid) or ≥4.1g/serving",
     "threshold_basis": "per 100g, per 100ml, or per serving",
     "governing_instrument": "Food Labelling Standards 2015, Appendix Table 12", "verified_date": "2023-12"},
    {"nutrient": "protein", "claim_type": "high_in", "claim_wording": "高い/豊富 (High in protein)",
     "threshold_value": "≥16.2g/100g (solid) or ≥8.1g/100ml (liquid) or ≥8.1g/serving",
     "threshold_basis": "per 100g, per 100ml, or per serving",
     "governing_instrument": "Food Labelling Standards 2015, Appendix Table 12", "verified_date": "2023-12"},
    # --- Fat ---
    {"nutrient": "fat", "claim_type": "low", "claim_wording": "低い (Low fat)",
     "threshold_value": "≤3g/100g (solid) or ≤1.5g/100ml (liquid)",
     "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "Food Labelling Standards 2015, Appendix Table 12", "verified_date": "2023-12"},
    {"nutrient": "fat", "claim_type": "free", "claim_wording": "含まない (Fat free / No fat)",
     "threshold_value": "≤0.5g/100g or ≤0.5g/100ml", "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "Food Labelling Standards 2015, Appendix Table 12", "verified_date": "2023-12"},
    {"nutrient": "fat", "claim_type": "reduced", "claim_wording": "控えめ (Reduced fat)",
     "threshold_value": "≥25% less fat than comparable product", "threshold_basis": "compared to reference",
     "governing_instrument": "Food Labelling Standards 2015, Appendix Table 12", "verified_date": "2023-12"},
    # --- Saturated fat ---
    {"nutrient": "saturated fat", "claim_type": "low", "claim_wording": "低い (Low saturated fat)",
     "threshold_value": "≤1.5g/100g (solid) or ≤0.75g/100ml (liquid)",
     "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "Food Labelling Standards 2015, Appendix Table 12", "verified_date": "2023-12"},
    {"nutrient": "saturated fat", "claim_type": "free", "claim_wording": "含まない (Saturated fat free)",
     "threshold_value": "≤0.1g/100g or ≤0.1g/100ml", "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "Food Labelling Standards 2015, Appendix Table 12", "verified_date": "2023-12"},
    # --- Sugars ---
    {"nutrient": "sugars", "claim_type": "low", "claim_wording": "低い (Low sugar)",
     "threshold_value": "≤5g/100g (solid) or ≤2.5g/100ml (liquid)",
     "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "Food Labelling Standards 2015, Appendix Table 12", "verified_date": "2023-12"},
    {"nutrient": "sugars", "claim_type": "free", "claim_wording": "含まない (Sugar free / No sugar)",
     "threshold_value": "≤0.5g/100g or ≤0.5g/100ml", "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "Food Labelling Standards 2015, Appendix Table 12", "verified_date": "2023-12"},
    # --- Sodium ---
    {"nutrient": "sodium", "claim_type": "low", "claim_wording": "低い (Low sodium / Low salt)",
     "threshold_value": "≤120mg/100g or ≤60mg/100ml", "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "Food Labelling Standards 2015, Appendix Table 12", "verified_date": "2023-12"},
    {"nutrient": "sodium", "claim_type": "free", "claim_wording": "含まない (Sodium free / No sodium)",
     "threshold_value": "≤5mg/100g or ≤5mg/100ml", "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "Food Labelling Standards 2015, Appendix Table 12", "verified_date": "2023-12"},
    {"nutrient": "sodium", "claim_type": "reduced", "claim_wording": "控えめ (Reduced sodium)",
     "threshold_value": "≥25% less sodium than comparable product", "threshold_basis": "compared to reference",
     "governing_instrument": "Food Labelling Standards 2015, Appendix Table 12", "verified_date": "2023-12"},
    # --- Energy ---
    {"nutrient": "energy", "claim_type": "low", "claim_wording": "低い (Low calorie)",
     "threshold_value": "≤100kcal/100g (solid) or ≤20kcal/100ml (liquid)",
     "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "Food Labelling Standards 2015, Appendix Table 12", "verified_date": "2023-12"},
    {"nutrient": "energy", "claim_type": "free", "claim_wording": "含まない (Calorie free / No calorie)",
     "threshold_value": "≤5kcal/100g or ≤5kcal/100ml", "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "Food Labelling Standards 2015, Appendix Table 12", "verified_date": "2023-12"},
    {"nutrient": "energy", "claim_type": "reduced", "claim_wording": "控えめ (Reduced calorie)",
     "threshold_value": "≥25% less energy than comparable product", "threshold_basis": "compared to reference",
     "governing_instrument": "Food Labelling Standards 2015, Appendix Table 12", "verified_date": "2023-12"},
]


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
                    ingredient_text = item.get("ingredient", "").lower()
                    claim_text = item.get("claim", "").lower()
                    if normalized in ingredient_text or normalized in claim_text:
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

    async def get_regulatory_updates(
        self,
        since_date: str | None = None,
    ) -> list[RegulatoryUpdate]:
        """Return seeded Japan regulatory updates, optionally filtered by date."""
        return get_seeded_updates(Market.JP, since_date)

    async def get_nutrient_claim_thresholds(
        self,
        nutrient: str | None = None,
    ) -> list[NutrientClaimThreshold]:
        """Return Japan nutrient content claim thresholds from Food Labelling Standards 2015."""
        results = []
        for t in _JP_CLAIM_THRESHOLDS:
            if nutrient is None or nutrient.lower() in t["nutrient"].lower():
                results.append(NutrientClaimThreshold(
                    market=Market.JP,
                    nutrient=t["nutrient"],
                    claim_type=t["claim_type"],
                    claim_wording=t["claim_wording"],
                    threshold_value=t["threshold_value"],
                    threshold_basis=t["threshold_basis"],
                    reference_value=t.get("reference_value"),
                    conditions=t.get("conditions"),
                    governing_instrument=t["governing_instrument"],
                    data_confidence="seeded",
                    verified_date=t.get("verified_date"),
                ))
        return results

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
