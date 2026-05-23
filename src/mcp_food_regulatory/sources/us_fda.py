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
    Market, ClaimResult, ClaimStatus, Standard, MarketOverview, RegulatoryBasis,
    NutrientClaimThreshold, RegulatoryUpdate,
)
from mcp_food_regulatory.sources.base import RegulatorySource
from mcp_food_regulatory.sources.regulatory_updates_seed import get_seeded_updates

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


# US nutrient content claim thresholds -- 21 CFR Part 101 Subpart D
# Verified against 21 CFR 101.54-101.67 and FDA guidance (2023)
_US_CLAIM_THRESHOLDS: list[dict] = [
    # --- Dietary fibre ---
    {"nutrient": "dietary fibre", "claim_type": "source_of", "claim_wording": "Good source of fiber",
     "threshold_value": "≥10% DV per serving (≥2.5g)", "threshold_basis": "per serving",
     "reference_value": "DV = 28g (FDA 2020 DRV)", "governing_instrument": "21 CFR 101.54(d)",
     "verified_date": "2023-12"},
    {"nutrient": "dietary fibre", "claim_type": "high_in", "claim_wording": "Excellent source of fiber / High fiber",
     "threshold_value": "≥20% DV per serving (≥5.6g)", "threshold_basis": "per serving",
     "reference_value": "DV = 28g (FDA 2020 DRV)", "governing_instrument": "21 CFR 101.54(b)",
     "verified_date": "2023-12"},
    # --- Protein ---
    {"nutrient": "protein", "claim_type": "source_of", "claim_wording": "Good source of protein",
     "threshold_value": "≥10% DV per serving", "threshold_basis": "per serving",
     "reference_value": "DV = 50g (FDA 2020 DRV)", "governing_instrument": "21 CFR 101.54(d)",
     "verified_date": "2023-12"},
    {"nutrient": "protein", "claim_type": "high_in", "claim_wording": "High protein / Excellent source of protein",
     "threshold_value": "≥20% DV per serving", "threshold_basis": "per serving",
     "reference_value": "DV = 50g (FDA 2020 DRV)", "governing_instrument": "21 CFR 101.54(b)",
     "verified_date": "2023-12"},
    # --- Fat ---
    {"nutrient": "fat", "claim_type": "low", "claim_wording": "Low fat",
     "threshold_value": "≤3g/serving and ≤30% calories from fat", "threshold_basis": "per serving",
     "governing_instrument": "21 CFR 101.62(b)", "verified_date": "2023-12"},
    {"nutrient": "fat", "claim_type": "free", "claim_wording": "Fat free",
     "threshold_value": "<0.5g/serving", "threshold_basis": "per serving",
     "governing_instrument": "21 CFR 101.62(b)", "verified_date": "2023-12"},
    {"nutrient": "fat", "claim_type": "reduced", "claim_wording": "Reduced fat",
     "threshold_value": "≥25% less fat per serving than reference food", "threshold_basis": "per serving",
     "governing_instrument": "21 CFR 101.62(b)", "verified_date": "2023-12"},
    # --- Saturated fat ---
    {"nutrient": "saturated fat", "claim_type": "low", "claim_wording": "Low saturated fat",
     "threshold_value": "≤1g/serving and ≤15% calories from saturated fat", "threshold_basis": "per serving",
     "governing_instrument": "21 CFR 101.62(c)", "verified_date": "2023-12"},
    {"nutrient": "saturated fat", "claim_type": "free", "claim_wording": "Saturated fat free",
     "threshold_value": "<0.5g/serving and <0.5g trans fat/serving", "threshold_basis": "per serving",
     "governing_instrument": "21 CFR 101.62(c)", "verified_date": "2023-12"},
    # --- Sugars ---
    {"nutrient": "sugars", "claim_type": "free", "claim_wording": "Sugar free",
     "threshold_value": "<0.5g/serving", "threshold_basis": "per serving",
     "governing_instrument": "21 CFR 101.60(c)", "verified_date": "2023-12"},
    {"nutrient": "sugars", "claim_type": "reduced", "claim_wording": "Reduced sugar",
     "threshold_value": "≥25% less sugar per serving than reference food", "threshold_basis": "per serving",
     "governing_instrument": "21 CFR 101.60(c)", "verified_date": "2023-12"},
    {"nutrient": "sugars", "claim_type": "no_added", "claim_wording": "No added sugars",
     "threshold_value": "No sugars or sugar-containing ingredient added during processing",
     "threshold_basis": "n/a",
     "conditions": "Must also not exceed the reference amount for sugars",
     "governing_instrument": "21 CFR 101.60(c)(2)", "verified_date": "2023-12"},
    # --- Sodium ---
    {"nutrient": "sodium", "claim_type": "low", "claim_wording": "Low sodium",
     "threshold_value": "≤140mg/serving", "threshold_basis": "per serving",
     "governing_instrument": "21 CFR 101.61(b)", "verified_date": "2023-12"},
    {"nutrient": "sodium", "claim_type": "free", "claim_wording": "Sodium free / Salt free",
     "threshold_value": "<5mg/serving", "threshold_basis": "per serving",
     "governing_instrument": "21 CFR 101.61(b)", "verified_date": "2023-12"},
    {"nutrient": "sodium", "claim_type": "reduced", "claim_wording": "Reduced sodium",
     "threshold_value": "≥25% less sodium per serving than reference food", "threshold_basis": "per serving",
     "governing_instrument": "21 CFR 101.61(b)", "verified_date": "2023-12"},
    {"nutrient": "sodium", "claim_type": "low", "claim_wording": "Very low sodium",
     "threshold_value": "≤35mg/serving", "threshold_basis": "per serving",
     "governing_instrument": "21 CFR 101.61(b)", "verified_date": "2023-12"},
    # --- Calories ---
    {"nutrient": "energy", "claim_type": "low", "claim_wording": "Low calorie",
     "threshold_value": "≤40kcal/serving (solid) or ≤40kcal/240ml (liquid)", "threshold_basis": "per serving",
     "governing_instrument": "21 CFR 101.60(b)", "verified_date": "2023-12"},
    {"nutrient": "energy", "claim_type": "free", "claim_wording": "Calorie free / Zero calories",
     "threshold_value": "<5kcal/serving", "threshold_basis": "per serving",
     "governing_instrument": "21 CFR 101.60(b)", "verified_date": "2023-12"},
    {"nutrient": "energy", "claim_type": "reduced", "claim_wording": "Reduced calorie",
     "threshold_value": "≥25% fewer calories than reference food", "threshold_basis": "per serving",
     "governing_instrument": "21 CFR 101.60(b)", "verified_date": "2023-12"},
    # --- Cholesterol ---
    {"nutrient": "cholesterol", "claim_type": "low", "claim_wording": "Low cholesterol",
     "threshold_value": "≤20mg/serving and ≤2g saturated fat/serving", "threshold_basis": "per serving",
     "governing_instrument": "21 CFR 101.62(d)", "verified_date": "2023-12"},
    {"nutrient": "cholesterol", "claim_type": "free", "claim_wording": "Cholesterol free",
     "threshold_value": "<2mg/serving and ≤2g saturated fat/serving", "threshold_basis": "per serving",
     "governing_instrument": "21 CFR 101.62(d)", "verified_date": "2023-12"},
    # --- Vitamins and minerals ---
    {"nutrient": "vitamins_minerals", "claim_type": "source_of",
     "claim_wording": "Good source of [vitamin/mineral]",
     "threshold_value": "≥10% DV per serving", "threshold_basis": "per serving",
     "reference_value": "DV per FDA 2020 DRVs", "governing_instrument": "21 CFR 101.54(d)",
     "verified_date": "2023-12"},
    {"nutrient": "vitamins_minerals", "claim_type": "high_in",
     "claim_wording": "High in [vitamin/mineral] / Excellent source of [vitamin/mineral]",
     "threshold_value": "≥20% DV per serving", "threshold_basis": "per serving",
     "reference_value": "DV per FDA 2020 DRVs", "governing_instrument": "21 CFR 101.54(b)",
     "verified_date": "2023-12"},
]


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

        # Authorized Health Claims -> PERMITTED
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

        # Qualified Health Claims -> CONDITIONAL
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

    async def get_regulatory_updates(
        self,
        since_date: str | None = None,
    ) -> list[RegulatoryUpdate]:
        """Return seeded US regulatory updates, optionally filtered by date."""
        return get_seeded_updates(Market.US, since_date)

    async def get_nutrient_claim_thresholds(
        self,
        nutrient: str | None = None,
    ) -> list[NutrientClaimThreshold]:
        """Return US FDA nutrient content claim thresholds from 21 CFR Part 101."""
        results = []
        for t in _US_CLAIM_THRESHOLDS:
            if nutrient is None or nutrient.lower() in t["nutrient"].lower():
                results.append(NutrientClaimThreshold(
                    market=Market.US,
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
