"""
Bhutan -- Bhutan Food and Drug Regulatory Authority (BFDRA).

Key regulations:
  Food Safety and Quality Act of Bhutan 2005
  Food Safety Rules and Regulations 2016

BFDRA established 2010; regulates food, drugs, cosmetics, and medical devices.
Follows WHO/Codex guidelines. Very small market with limited health-claim-specific
regulations published online. Strategy: Codex-equivalent framework seeded.
"""

from __future__ import annotations
from mcp_food_regulatory.models import (
    Market, ClaimResult, ClaimStatus, Standard, MarketOverview, RegulatoryBasis
)
from mcp_food_regulatory.sources.base import RegulatorySource

_BASE_URL = "https://www.bfdra.gov.bt"
_NAB_URL = "https://www.nab.gov.bt"

_KNOWN_STANDARDS: dict[str, dict] = {
    "Food Safety and Quality Act 2005": {
        "title": "Food Safety and Quality Act of Bhutan 2005",
        "category": "legislation",
        "adopted": "2005",
        "summary": (
            "Primary food safety legislation in Bhutan. Establishes the legal framework "
            "for food control, prohibits adulteration and misrepresentation (including "
            "false health claims), and empowers the competent authority to issue food "
            "safety regulations. Administered by BFDRA."
        ),
        "full_text_url": _BASE_URL,
    },
    "Food Safety Rules 2016": {
        "title": "Food Safety Rules and Regulations of Bhutan 2016",
        "category": "regulation",
        "adopted": "2016",
        "summary": (
            "Implementing regulations under the Food Safety and Quality Act 2005. "
            "Covers labelling requirements, food standards, and general conditions for "
            "nutrition and health claims aligned with WHO/Codex guidelines. "
            "Bhutan is a very small market; detailed claim-specific provisions are limited."
        ),
        "full_text_url": _BASE_URL,
    },
}

_CLAIM_PROVISIONS: dict[str, list[dict]] = {
    "vitamin c": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Codex-aligned (Food Safety Rules 2016): 'Source of Vitamin C' -- "
                "at least 15% RDI per 100g/100ml or per serving. 'High in Vitamin C' -- 30% RDI. "
                "Claims must be truthful and not misleading per Food Safety and Quality Act 2005."
            ),
            "instrument": "Food Safety Rules 2016 (Codex CAC/GL 23-aligned)",
            "url": _BASE_URL,
            "last_updated": "2016",
        }
    ],
    "calcium": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Codex-aligned: 'Source of Calcium' -- at least 15% RDI per 100g/100ml. "
                "Health claims beyond nutrient content require BFDRA review."
            ),
            "instrument": "Food Safety Rules 2016",
            "url": _BASE_URL,
            "last_updated": "2016",
        }
    ],
    "dietary fibre": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Codex-aligned: 'Source of Dietary Fibre' -- at least 3g/100g or 1.5g/100kcal. "
                "'High in Dietary Fibre' -- at least 6g/100g."
            ),
            "instrument": "Food Safety Rules 2016",
            "url": _BASE_URL,
            "last_updated": "2016",
        }
    ],
}


class BTBFDRASource(RegulatorySource):
    """BFDRA data source for Bhutan."""

    market = Market.BT
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
                    market=Market.BT,
                    ingredient=ingredient,
                    claim_type=p["claim_type"],
                    status=ClaimStatus(p["status"]),
                    conditions=p.get("conditions"),
                    basis=RegulatoryBasis(
                        instrument=p["instrument"],
                        url=p.get("url"),
                        notes="Bhutan follows WHO/Codex guidelines. Very small market with limited health-claim-specific published regulations.",
                    ),
                    last_updated=p.get("last_updated"),
                    source_url=p.get("url"),
                ))

        if not results:
            results.append(ClaimResult(
                market=Market.BT,
                ingredient=ingredient,
                claim_type=claim_type or "health_claim",
                status=ClaimStatus.NOT_DEFINED,
                conditions=(
                    f"No pre-indexed BFDRA claim data for '{ingredient}'. "
                    "Bhutan follows WHO/Codex guidelines under the Food Safety and Quality Act 2005. "
                    "Contact BFDRA (bfdra.gov.bt) directly for specific claim guidance. "
                    "Very small market with minimal published health-claim regulations."
                ),
                basis=RegulatoryBasis(
                    instrument="Food Safety and Quality Act 2005 + Food Safety Rules 2016",
                    url=_BASE_URL,
                    notes="Very limited online regulatory data for health claims. Codex-aligned framework.",
                ),
                source_url=_BASE_URL,
            ))

        return results

    async def get_standard(self, standard_id: str) -> Standard | None:
        upper = standard_id.upper()
        for key, data in _KNOWN_STANDARDS.items():
            if upper in key.upper() or key.upper() in upper:
                return Standard(standard_id=key, market=Market.BT, **data)
        return None

    async def search_standards(self, query: str) -> list[Standard]:
        q = query.lower()
        return [
            Standard(standard_id=k, market=Market.BT, **v)
            for k, v in _KNOWN_STANDARDS.items()
            if q in k.lower() or q in v["title"].lower() or q in (v.get("summary") or "").lower()
        ] or [Standard(standard_id=k, market=Market.BT, **v) for k, v in _KNOWN_STANDARDS.items()]

    async def get_market_overview(self) -> MarketOverview:
        return MarketOverview(
            market=Market.BT,
            authority_name="Bhutan Food and Drug Regulatory Authority (BFDRA)",
            authority_url=_BASE_URL,
            key_legislation=[
                "Food Safety and Quality Act of Bhutan 2005",
                "Food Safety Rules and Regulations of Bhutan 2016",
            ],
            health_claims_framework=(
                "Bhutan regulates health claims under the Food Safety and Quality Act 2005 "
                "and Food Safety Rules 2016. BFDRA (established 2010) follows WHO/Codex guidelines. "
                "Very small market; health-claim-specific regulations are limited. "
                "Claims must be truthful and not misleading. "
                "No published positive health claims list; all non-trivial claims require BFDRA review."
            ),
            notes=(
                f"BFDRA: {_BASE_URL} | "
                f"National Assembly of Bhutan: {_NAB_URL}"
            ),
        )
