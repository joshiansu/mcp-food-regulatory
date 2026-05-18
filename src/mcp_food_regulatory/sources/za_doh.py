"""
South Africa -- Department of Health (DoH).

Key regulations:
  Foodstuffs, Cosmetics and Disinfectants Act 54 of 1972 (FCD Act)
  Regulation R146 of 2010 (Labelling and Advertising of Foodstuffs)
    -- governs health claims and advertising of food

R146 of 2010 contains the permitted claims list in its annexures. Proposed
update (Draft R429) has been in consultation for years without finalisation.
DoH website has PDFs; very limited structured online data.

Strategy: seed R146 permitted claims provisions; direct to DoH for full text.
"""

from __future__ import annotations
from mcp_food_regulatory.models import (
    Market, ClaimResult, ClaimStatus, Standard, MarketOverview, RegulatoryBasis
)
from mcp_food_regulatory.sources.base import RegulatorySource

_BASE_URL = "https://www.health.gov.za"
_DOH_FOOD_URL = "https://www.health.gov.za/foodcontrol/"
_GOV_DOCS_URL = "https://www.gov.za/documents/foodstuffs-cosmetics-and-disinfectants-act"

_KNOWN_STANDARDS: dict[str, dict] = {
    "R146/2010": {
        "title": "Regulations Relating to the Labelling and Advertising of Foodstuffs (R146 of 2010)",
        "category": "regulation",
        "adopted": "2010",
        "summary": (
            "Primary regulation governing health claims and advertising on food labels in South Africa. "
            "Issued under the FCD Act 54/1972. "
            "Annexure A lists permitted label declarations. "
            "Annexure B lists conditions for nutrient content claims. "
            "Annexure C lists permitted health claims with conditions. "
            "Draft R429 (proposed update) has been in consultation but not yet finalised."
        ),
        "full_text_url": _DOH_FOOD_URL,
    },
    "FCD Act 54/1972": {
        "title": "Foodstuffs, Cosmetics and Disinfectants Act 54 of 1972",
        "category": "legislation",
        "adopted": "1972",
        "last_amended": "2018",
        "summary": (
            "Foundational legislation enabling DoH to issue regulations on food labelling, "
            "advertising, safety, and standards in South Africa. "
            "Empowers the Minister of Health to publish regulations including R146/2010."
        ),
        "full_text_url": _GOV_DOCS_URL,
    },
    "R214/2010": {
        "title": "Regulations Relating to the Foodstuffs for Infants and Young Children (R214 of 2010)",
        "category": "regulation",
        "adopted": "2010",
        "summary": (
            "Specific regulations for foods intended for infants and young children, "
            "including restrictions on health claims for these product categories."
        ),
        "full_text_url": _DOH_FOOD_URL,
    },
}

_CLAIM_PROVISIONS: dict[str, list[dict]] = {
    "vitamin c": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "R146/2010 Annexure B: 'Contains Vitamin C' / 'Source of Vitamin C' -- "
                "at least 15% NRV per 100g/100ml or per serving. "
                "'High in Vitamin C' -- at least 30% NRV. "
                "South African NRV for Vitamin C: 60 mg/day. "
                "Claim must not be misleading and must comply with Annexure C if a health function "
                "claim is also made."
            ),
            "instrument": "R146/2010 Annexure B",
            "url": _DOH_FOOD_URL,
            "last_updated": "2010",
        }
    ],
    "vitamin d": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "R146/2010 Annexure B: 'Source of Vitamin D' -- at least 15% NRV per 100g/100ml. "
                "South African NRV for Vitamin D: 5 µg/day. "
                "Health claims linking Vitamin D to bone health must be included in Annexure C "
                "or individually approved by DoH."
            ),
            "instrument": "R146/2010 Annexure B & C",
            "url": _DOH_FOOD_URL,
            "last_updated": "2010",
        }
    ],
    "calcium": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "R146/2010 Annexure B: 'Source of Calcium' -- at least 15% NRV per 100g/100ml. "
                "'High in Calcium' -- at least 30% NRV. South African NRV for Calcium: 800 mg/day. "
                "Annexure C: Calcium health claim ('necessary for healthy bones and teeth') "
                "is permitted when the source/high threshold is met."
            ),
            "instrument": "R146/2010 Annexure B & C",
            "url": _DOH_FOOD_URL,
            "last_updated": "2010",
        }
    ],
    "dietary fibre": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "R146/2010 Annexure B: 'Source of Dietary Fibre' -- at least 3g/100g or 1.5g/100kcal. "
                "'High in Dietary Fibre' -- at least 6g/100g or 3g/100kcal. "
                "Conditions aligned with Codex thresholds."
            ),
            "instrument": "R146/2010 Annexure B",
            "url": _DOH_FOOD_URL,
            "last_updated": "2010",
        }
    ],
    "omega-3": [
        {
            "claim_type": "nutrition_claim",
            "status": "conditional",
            "conditions": (
                "R146/2010 Annexure B includes conditions for omega-3 claims: "
                "'Source of Omega-3' -- at least 0.3g ALA or 40mg EPA+DHA per 100g. "
                "Cardiovascular health claim linking omega-3 to heart health requires "
                "inclusion in Annexure C or individual DoH approval. "
                "Check latest R146 text for current Annexure C status."
            ),
            "instrument": "R146/2010 Annexure B & C",
            "url": _DOH_FOOD_URL,
            "last_updated": "2010",
        }
    ],
}


class ZADoHSource(RegulatorySource):
    """Department of Health data source for South Africa."""

    market = Market.ZA
    BASE_URL = _BASE_URL

    async def search_health_claims(
        self,
        ingredient: str,
        claim_type: str | None = None,
    ) -> list[ClaimResult]:
        normalized = ingredient.lower().strip()
        results: list[ClaimResult] = []

        provisions = _CLAIM_PROVISIONS.get(normalized, [])
        for p in provisions:
            if claim_type is None or claim_type.lower() in p["claim_type"].lower():
                results.append(ClaimResult(
                    market=Market.ZA,
                    ingredient=ingredient,
                    claim_type=p["claim_type"],
                    status=ClaimStatus(p["status"]),
                    conditions=p.get("conditions"),
                    basis=RegulatoryBasis(
                        instrument=p["instrument"],
                        url=p.get("url"),
                        notes="R146/2010 Annexure B & C list permitted nutrition and health claims. Draft R429 update in consultation -- check DoH for latest status.",
                    ),
                    last_updated=p.get("last_updated"),
                    source_url=p.get("url"),
                ))

        if not results:
            results.append(ClaimResult(
                market=Market.ZA,
                ingredient=ingredient,
                claim_type=claim_type or "health_claim",
                status=ClaimStatus.NOT_DEFINED,
                conditions=(
                    f"No pre-indexed South African claim data for '{ingredient}'. "
                    "Refer to R146/2010 Annexure B (nutrition claims) and Annexure C "
                    "(health claims) via the DoH food control page. "
                    "Very limited online structured data; PDF download recommended."
                ),
                basis=RegulatoryBasis(
                    instrument="R146/2010 (FCD Act 54/1972)",
                    url=_DOH_FOOD_URL,
                    notes="Draft R429 proposed update has been in consultation for years; R146/2010 remains in force.",
                ),
                source_url=_DOH_FOOD_URL,
            ))

        return results

    async def get_standard(self, standard_id: str) -> Standard | None:
        upper = standard_id.upper()
        for key, data in _KNOWN_STANDARDS.items():
            if upper in key.upper() or key.upper() in upper:
                return Standard(standard_id=key, market=Market.ZA, **data)
        return None

    async def search_standards(self, query: str) -> list[Standard]:
        q = query.lower()
        return [
            Standard(standard_id=k, market=Market.ZA, **v)
            for k, v in _KNOWN_STANDARDS.items()
            if q in k.lower() or q in v["title"].lower() or q in (v.get("summary") or "").lower()
        ] or [Standard(standard_id=k, market=Market.ZA, **v) for k, v in _KNOWN_STANDARDS.items()]

    async def get_market_overview(self) -> MarketOverview:
        return MarketOverview(
            market=Market.ZA,
            authority_name="Department of Health (DoH) -- Directorate: Food Control",
            authority_url=_DOH_FOOD_URL,
            key_legislation=[
                "Foodstuffs, Cosmetics and Disinfectants Act 54 of 1972 (FCD Act)",
                "R146 of 2010 -- Labelling and Advertising of Foodstuffs",
                "R214 of 2010 -- Foodstuffs for Infants and Young Children",
            ],
            health_claims_framework=(
                "South Africa regulates health claims under R146/2010 issued under the FCD Act 54/1972. "
                "Annexure B lists permitted nutrient content claims with threshold conditions. "
                "Annexure C lists permitted health claims with conditions (very limited list). "
                "Claims not in the Annexures are prohibited unless specifically approved by DoH. "
                "A proposed update (Draft R429) has been in consultation for years without finalisation; "
                "R146/2010 remains the operative regulation. "
                "Very limited structured online data -- DoH website provides PDFs."
            ),
            notes=(
                f"DoH food control portal: {_DOH_FOOD_URL} | "
                f"Official document repository: {_GOV_DOCS_URL}"
            ),
        )
