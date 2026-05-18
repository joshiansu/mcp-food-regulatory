"""
India -- Food Safety and Standards Authority of India (FSSAI).

Key regulations:
  FSS (Advertising and Claims) Regulations 2018 -- Schedule I & II list
  permitted nutrition and health claims. No structured online database;
  the authoritative text is a PDF gazette notification.

Strategy:
  Seed Schedule I (nutrition claims) and Schedule II (health claims) provisions
  for common ingredients. Direct users to FSSAI website for full text.
"""

from __future__ import annotations
from mcp_food_regulatory.models import (
    Market, ClaimResult, ClaimStatus, Standard, MarketOverview, RegulatoryBasis
)
from mcp_food_regulatory.sources.base import RegulatorySource

_BASE_URL = "https://www.fssai.gov.in"
_CLAIMS_REG_URL = (
    "https://www.fssai.gov.in/upload/uploadfiles/files/Regulations/English/"
    "FSSAI_Notf_Regu_Claims_31_08_2018.pdf"
)

_KNOWN_STANDARDS: dict[str, dict] = {
    "FSS Claims 2018": {
        "title": "Food Safety and Standards (Advertising and Claims) Regulations 2018",
        "category": "regulation",
        "adopted": "2018",
        "summary": (
            "Primary regulation governing nutrition and health claims on food labels in India. "
            "Schedule I lists permitted nutrition claims with conditions. "
            "Schedule II lists permitted health claims. "
            "Prohibits misleading claims and sets requirements for substantiation."
        ),
        "full_text_url": _CLAIMS_REG_URL,
    },
    "FSS Act 2006": {
        "title": "Food Safety and Standards Act 2006",
        "category": "legislation",
        "adopted": "2006",
        "last_amended": "2020",
        "summary": (
            "Foundational legislation establishing FSSAI and the framework for food safety "
            "regulation in India. Empowers FSSAI to issue regulations on labelling, "
            "additives, contaminants, and advertising."
        ),
        "full_text_url": "https://www.fssai.gov.in/upload/uploadfiles/files/FSS_Act2006.pdf",
    },
    "FSS Labelling 2020": {
        "title": "Food Safety and Standards (Labelling and Display) Regulations 2020",
        "category": "regulation",
        "adopted": "2020",
        "summary": (
            "Governs mandatory label declarations, font sizes, and display requirements "
            "for packaged foods sold in India. Complements the Claims Regulations 2018."
        ),
        "full_text_url": "https://www.fssai.gov.in/upload/uploadfiles/files/Regulations/English/FSSAI_Reg_Labelling_05_03_2020.pdf",
    },
}

# Seeded provisions from FSS Claims Regulations 2018 Schedule I & II
_CLAIM_PROVISIONS: dict[str, list[dict]] = {
    "vitamin c": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Schedule I nutrition claim: 'Source of Vitamin C' -- product must contain "
                "at least 15% NRV per 100g/100ml or per serving. "
                "'High in Vitamin C' -- at least 30% NRV per 100g/100ml or per serving. "
                "NRV for Vitamin C: 40 mg/day (Indian standard)."
            ),
            "instrument": "FSS Claims 2018 Schedule I",
            "url": _CLAIMS_REG_URL,
            "last_updated": "2018",
        }
    ],
    "vitamin d": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Schedule I: 'Source of Vitamin D' -- at least 15% NRV per 100g/100ml or serving. "
                "'High in Vitamin D' -- at least 30% NRV per 100g/100ml or serving. "
                "NRV for Vitamin D: 5 µg/day."
            ),
            "instrument": "FSS Claims 2018 Schedule I",
            "url": _CLAIMS_REG_URL,
            "last_updated": "2018",
        }
    ],
    "calcium": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Schedule I: 'Source of Calcium' -- at least 15% NRV per 100g/100ml. "
                "'High in Calcium' -- at least 30% NRV. NRV for Calcium: 600 mg/day. "
                "Schedule II health claim: Calcium contributes to normal development and "
                "maintenance of healthy bones and teeth (with qualifying conditions)."
            ),
            "instrument": "FSS Claims 2018 Schedule I & II",
            "url": _CLAIMS_REG_URL,
            "last_updated": "2018",
        }
    ],
    "dietary fibre": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Schedule I: 'Source of Fibre' -- at least 3g/100g or 1.5g/100kcal. "
                "'High in Fibre' -- at least 6g/100g or 3g/100kcal. "
                "Dietary fibre definition per FSSAI: non-digestible carbohydrate polymers "
                "with three or more monomeric units."
            ),
            "instrument": "FSS Claims 2018 Schedule I",
            "url": _CLAIMS_REG_URL,
            "last_updated": "2018",
        }
    ],
    "omega-3": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Schedule I: 'Source of Omega-3 fatty acids' -- at least 0.3g ALA per 100g "
                "or at least 40mg EPA+DHA per 100g. "
                "'High in Omega-3' -- double the source threshold. "
                "Claims about heart health benefits require pre-approval under Schedule II."
            ),
            "instrument": "FSS Claims 2018 Schedule I",
            "url": _CLAIMS_REG_URL,
            "last_updated": "2018",
        }
    ],
}


class INFSSAISource(RegulatorySource):
    """FSSAI data source for India."""

    market = Market.IN
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
                    market=Market.IN,
                    ingredient=ingredient,
                    claim_type=p["claim_type"],
                    status=ClaimStatus(p["status"]),
                    conditions=p.get("conditions"),
                    basis=RegulatoryBasis(
                        instrument=p["instrument"],
                        url=p.get("url"),
                        notes="FSS Claims Regulations 2018 -- Schedule I (nutrition) and Schedule II (health).",
                    ),
                    last_updated=p.get("last_updated"),
                    source_url=p.get("url"),
                ))

        if not results:
            results.append(ClaimResult(
                market=Market.IN,
                ingredient=ingredient,
                claim_type=claim_type or "health_claim",
                status=ClaimStatus.NOT_DEFINED,
                conditions=(
                    f"No pre-indexed FSSAI claim data for '{ingredient}'. "
                    "Refer to FSS (Advertising and Claims) Regulations 2018 Schedule I & II, "
                    "or the FSSAI website for circulars and amendments."
                ),
                basis=RegulatoryBasis(
                    instrument="FSS Claims 2018",
                    url=_CLAIMS_REG_URL,
                    notes="No structured online database; full text available as PDF gazette.",
                ),
                source_url=_BASE_URL,
            ))

        return results

    async def get_standard(self, standard_id: str) -> Standard | None:
        upper = standard_id.upper()
        for key, data in _KNOWN_STANDARDS.items():
            if upper in key.upper() or key.upper() in upper:
                return Standard(standard_id=key, market=Market.IN, **data)
        return None

    async def search_standards(self, query: str) -> list[Standard]:
        q = query.lower()
        return [
            Standard(standard_id=k, market=Market.IN, **v)
            for k, v in _KNOWN_STANDARDS.items()
            if q in k.lower() or q in v["title"].lower() or q in (v.get("summary") or "").lower()
        ] or [Standard(standard_id=k, market=Market.IN, **v) for k, v in _KNOWN_STANDARDS.items()]

    async def get_market_overview(self) -> MarketOverview:
        return MarketOverview(
            market=Market.IN,
            authority_name="Food Safety and Standards Authority of India (FSSAI)",
            authority_url=_BASE_URL,
            key_legislation=[
                "Food Safety and Standards Act 2006",
                "FSS (Advertising and Claims) Regulations 2018",
                "FSS (Labelling and Display) Regulations 2020",
                "FSS (Food Products Standards and Food Additives) Regulations 2011",
            ],
            health_claims_framework=(
                "Health and nutrition claims in India are governed by the FSS (Advertising "
                "and Claims) Regulations 2018. Schedule I lists permitted nutrition claims "
                "(e.g. 'source of', 'high in') with threshold conditions. Schedule II lists "
                "permitted health claims linking diet to health outcomes. "
                "No general pre-market approval is required for Schedule I/II claims if "
                "conditions are met. Novel claims not in Schedule I/II require FSSAI approval. "
                "Claims must not be misleading, and traditional medicine references are restricted."
            ),
            notes=(
                "FSSAI publishes circulars and guidance on its website. "
                "egazette.gov.in is the authoritative source for gazette notifications."
            ),
        )
