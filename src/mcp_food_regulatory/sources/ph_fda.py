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
            )
            if not is_match:
                continue
            if claim_type is None or claim_type.lower() == entry["claim_type"]:
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
