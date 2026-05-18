"""
Bangladesh -- Bangladesh Food Safety Authority (BFSA) /
Bangladesh Standards and Testing Institution (BSTI).

BFSA established under the Food Safety Act 2013; Food Safety Rules 2021
govern labelling and claims. BSTI publishes BDS (Bangladesh Standard) food
standards. Health claims follow Codex CAC/GL 23 principles.

Very limited structured online data; gazette PDFs in Bangla.
"""

from __future__ import annotations
from mcp_food_regulatory.models import (
    Market, ClaimResult, ClaimStatus, Standard, MarketOverview, RegulatoryBasis
)
from mcp_food_regulatory.sources.base import RegulatorySource

_BASE_URL = "https://bfsa.gov.bd"
_BSTI_URL = "https://www.bsti.gov.bd"
_BDLAWS_URL = "https://bdlaws.minlaw.gov.bd"

_KNOWN_STANDARDS: dict[str, dict] = {
    "Food Safety Act 2013": {
        "title": "Food Safety Act 2013 (Act No. 43 of 2013)",
        "category": "legislation",
        "adopted": "2013",
        "summary": (
            "Establishes the Bangladesh Food Safety Authority (BFSA) and the legal framework "
            "for food safety regulation in Bangladesh. "
            "Empowers BFSA to issue rules on labelling, nutrition, and health claims. "
            "Replaces the Pure Food Ordinance 1959."
        ),
        "full_text_url": _BDLAWS_URL,
    },
    "Food Safety Rules 2021": {
        "title": "Food Safety Rules 2021 (Bangladesh Food Safety Authority)",
        "category": "regulation",
        "adopted": "2021",
        "summary": (
            "Implementing rules under the Food Safety Act 2013. "
            "Covers labelling requirements, nutrition declaration, and conditions for "
            "nutrition and health claims. Aligned with Codex guidelines. "
            "Published in the Bangladesh Gazette."
        ),
        "full_text_url": _BASE_URL,
    },
    "BDS 1: 2018": {
        "title": "Bangladesh Standard BDS 1:2018 -- Labelling of Prepackaged Foods",
        "category": "national_standard",
        "adopted": "2018",
        "summary": (
            "BSTI standard for labelling of prepackaged foods, aligned with Codex STAN 1-1985. "
            "Covers mandatory labelling elements and principles for nutrition and health claims. "
            "Health claims must be scientifically substantiated."
        ),
        "full_text_url": _BSTI_URL,
    },
}

_CLAIM_PROVISIONS: dict[str, list[dict]] = {
    "vitamin c": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Food Safety Rules 2021 / Codex-aligned: 'Contains Vitamin C' -- at least "
                "15% RDI per 100g/100ml or per serving. 'High in Vitamin C' -- 30% RDI. "
                "Bangladesh RDI for Vitamin C: 40 mg/day. "
                "Claims must not be misleading per BDS 1:2018."
            ),
            "instrument": "Food Safety Rules 2021 + BDS 1:2018",
            "url": _BASE_URL,
            "last_updated": "2021",
        }
    ],
    "vitamin d": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Codex-aligned: 'Contains Vitamin D' -- at least 15% RDI per 100g/100ml. "
                "RDI for Vitamin D: 5 µg/day. "
                "Health claims require BFSA substantiation review."
            ),
            "instrument": "Food Safety Rules 2021 + BDS 1:2018",
            "url": _BASE_URL,
            "last_updated": "2021",
        }
    ],
    "calcium": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Codex-aligned: 'Source of Calcium' -- at least 15% RDI per 100g/100ml. "
                "Bangladesh RDI for Calcium: 800 mg/day. "
                "Disease risk reduction claim (calcium/bone health) follows Codex CAC/GL 23 "
                "conditions; requires BFSA review."
            ),
            "instrument": "Food Safety Rules 2021 + BDS 1:2018",
            "url": _BASE_URL,
            "last_updated": "2021",
        }
    ],
    "dietary fibre": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Codex-aligned: 'Source of Dietary Fibre' -- at least 3g/100g or 1.5g/100kcal. "
                "'High in Dietary Fibre' -- at least 6g/100g. "
                "Per Food Safety Rules 2021 and BDS 1:2018."
            ),
            "instrument": "Food Safety Rules 2021",
            "url": _BASE_URL,
            "last_updated": "2021",
        }
    ],
}


class BDBFSASource(RegulatorySource):
    """BFSA data source for Bangladesh."""

    market = Market.BD
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
                    market=Market.BD,
                    ingredient=ingredient,
                    claim_type=p["claim_type"],
                    status=ClaimStatus(p["status"]),
                    conditions=p.get("conditions"),
                    basis=RegulatoryBasis(
                        instrument=p["instrument"],
                        url=p.get("url"),
                        notes="Bangladesh follows Codex CAC/GL 23 principles via Food Safety Rules 2021 and BDS 1:2018. BFSA is the primary authority.",
                    ),
                    last_updated=p.get("last_updated"),
                    source_url=p.get("url"),
                ))

        if not results:
            results.append(ClaimResult(
                market=Market.BD,
                ingredient=ingredient,
                claim_type=claim_type or "health_claim",
                status=ClaimStatus.NOT_DEFINED,
                conditions=(
                    f"No pre-indexed BFSA claim data for '{ingredient}'. "
                    "Bangladesh follows Codex CAC/GL 23 principles. "
                    "Check BFSA portal (bfsa.gov.bd) or BSTI (bsti.gov.bd) for applicable standards. "
                    "Content primarily in Bangla."
                ),
                basis=RegulatoryBasis(
                    instrument="Food Safety Act 2013 + Food Safety Rules 2021",
                    url=_BASE_URL,
                    notes="Very limited structured online data; gazette PDFs in Bangla.",
                ),
                source_url=_BASE_URL,
            ))

        return results

    async def get_standard(self, standard_id: str) -> Standard | None:
        upper = standard_id.upper()
        for key, data in _KNOWN_STANDARDS.items():
            if upper in key.upper() or key.upper() in upper:
                return Standard(standard_id=key, market=Market.BD, **data)
        return None

    async def search_standards(self, query: str) -> list[Standard]:
        q = query.lower()
        return [
            Standard(standard_id=k, market=Market.BD, **v)
            for k, v in _KNOWN_STANDARDS.items()
            if q in k.lower() or q in v["title"].lower() or q in (v.get("summary") or "").lower()
        ] or [Standard(standard_id=k, market=Market.BD, **v) for k, v in _KNOWN_STANDARDS.items()]

    async def get_market_overview(self) -> MarketOverview:
        return MarketOverview(
            market=Market.BD,
            authority_name="Bangladesh Food Safety Authority (BFSA) / Bangladesh Standards and Testing Institution (BSTI)",
            authority_url=_BASE_URL,
            key_legislation=[
                "Food Safety Act 2013 (Act No. 43 of 2013)",
                "Food Safety Rules 2021",
                "BDS 1:2018 -- Labelling of Prepackaged Foods (BSTI)",
            ],
            health_claims_framework=(
                "Bangladesh regulates health claims under the Food Safety Act 2013 and "
                "implementing Food Safety Rules 2021. Claims must follow Codex CAC/GL 23 "
                "principles -- truthful, not misleading, scientifically substantiated. "
                "BSTI publishes BDS standards aligned with Codex STAN 1-1985 for labelling. "
                "No comprehensive positive health claims list; claims evaluated case-by-case. "
                "Content primarily in Bangla; very limited structured online data."
            ),
            notes=(
                f"BFSA: {_BASE_URL} | BSTI: {_BSTI_URL} | "
                f"Bangladesh Laws: {_BDLAWS_URL}"
            ),
        )
