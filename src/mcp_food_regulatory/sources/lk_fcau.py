"""
Sri Lanka -- Food Control Administration Unit (FCAU) /
Sri Lanka Standards Institution (SLSI).

Key regulations:
  Food Act No. 26 of 1980 (amended 1999, 2011) -- primary legislation
  Food (Labelling) Regulations 2005 -- governs nutrition labelling and claims
  SLS 516 -- Sri Lanka Standard for labelling of prepackaged foods

Health claims follow a Codex-aligned approach. Limited positive claim list;
most claims require FCAU review. Full texts available as gazette PDFs.
"""

from __future__ import annotations
from mcp_food_regulatory.models import (
    Market, ClaimResult, ClaimStatus, Standard, MarketOverview, RegulatoryBasis
)
from mcp_food_regulatory.sources.base import RegulatorySource

_BASE_URL = "https://www.health.gov.lk/foodcontrol"
_SLSI_URL = "https://www.slsi.lk"
_DOCS_URL = "https://www.documents.gov.lk"

_KNOWN_STANDARDS: dict[str, dict] = {
    "Food Act No. 26/1980": {
        "title": "Food Act No. 26 of 1980 (as amended)",
        "category": "legislation",
        "adopted": "1980",
        "last_amended": "2011",
        "summary": (
            "Primary legislation governing food safety and labelling in Sri Lanka. "
            "Empowers the Minister of Health to issue food regulations including labelling "
            "and advertising rules. Administered by the Food Control Administration Unit (FCAU) "
            "within the Ministry of Health."
        ),
        "full_text_url": _DOCS_URL,
    },
    "Food Labelling Regulations 2005": {
        "title": "Food (Labelling) Regulations 2005 (Gazette No. 1405/28)",
        "category": "regulation",
        "adopted": "2005",
        "summary": (
            "Governs mandatory label elements, nutrition labelling, and conditions for "
            "nutrition and health claims for prepackaged foods in Sri Lanka. "
            "Claims must be truthful, substantiated, and not misleading. "
            "Codex-aligned approach; no comprehensive positive health claims list."
        ),
        "full_text_url": _BASE_URL,
    },
    "SLS 516": {
        "title": "SLS 516 -- Sri Lanka Standard: Labelling of Prepackaged Foods",
        "category": "national_standard",
        "adopted": "2000",
        "last_amended": "2013",
        "summary": (
            "SLSI standard aligned with Codex STAN 1-1985 for labelling of prepackaged foods. "
            "Covers mandatory declarations, nutrition information panel, and general claim conditions."
        ),
        "full_text_url": _SLSI_URL,
    },
}

_CLAIM_PROVISIONS: dict[str, list[dict]] = {
    "vitamin c": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Food Labelling Regulations 2005 / Codex-aligned: "
                "'Source of Vitamin C' -- at least 15% RDI per 100g/100ml or per serving. "
                "'High in Vitamin C' -- at least 30% RDI. "
                "Sri Lankan RDI for Vitamin C: 40 mg/day. "
                "Claims must comply with SLS 516 and not be misleading."
            ),
            "instrument": "Food Labelling Regulations 2005 + SLS 516",
            "url": _BASE_URL,
            "last_updated": "2005",
        }
    ],
    "vitamin d": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Codex-aligned: 'Source of Vitamin D' -- at least 15% RDI per 100g/100ml. "
                "RDI for Vitamin D: 5 µg/day. "
                "Health claims linking Vitamin D to bone health require FCAU substantiation review."
            ),
            "instrument": "Food Labelling Regulations 2005 + SLS 516",
            "url": _BASE_URL,
            "last_updated": "2005",
        }
    ],
    "calcium": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Codex-aligned: 'Source of Calcium' -- at least 15% RDI per 100g/100ml. "
                "'High in Calcium' -- at least 30% RDI. RDI for Calcium: 800 mg/day. "
                "Disease risk reduction claim (calcium/bone health) is Codex-permitted in principle "
                "but requires individual FCAU review and substantiation in Sri Lanka."
            ),
            "instrument": "Food Labelling Regulations 2005 + SLS 516",
            "url": _BASE_URL,
            "last_updated": "2005",
        }
    ],
    "dietary fibre": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Codex-aligned: 'Source of Dietary Fibre' -- at least 3g/100g or 1.5g/100kcal. "
                "'High in Dietary Fibre' -- at least 6g/100g or 3g/100kcal. "
                "Per Food Labelling Regulations 2005 and SLS 516."
            ),
            "instrument": "Food Labelling Regulations 2005",
            "url": _BASE_URL,
            "last_updated": "2005",
        }
    ],
    "omega-3": [
        {
            "claim_type": "nutrition_claim",
            "status": "conditional",
            "conditions": (
                "Codex-aligned: 'Source of Omega-3' -- at least 0.3g ALA or 40mg EPA+DHA per 100g. "
                "Cardiovascular health claims require FCAU individual review. "
                "No standalone omega-3 health claim in Sri Lanka positive list."
            ),
            "instrument": "Food Labelling Regulations 2005",
            "url": _BASE_URL,
            "last_updated": "2005",
        }
    ],
}


class LKFCAUSource(RegulatorySource):
    """FCAU/SLSI data source for Sri Lanka."""

    market = Market.LK
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
                    market=Market.LK,
                    ingredient=ingredient,
                    claim_type=p["claim_type"],
                    status=ClaimStatus(p["status"]),
                    conditions=p.get("conditions"),
                    basis=RegulatoryBasis(
                        instrument=p["instrument"],
                        url=p.get("url"),
                        notes="Sri Lanka follows Codex CAC/GL 23 principles via Food Labelling Regulations 2005 and SLS 516. FCAU reviews claims case-by-case.",
                    ),
                    last_updated=p.get("last_updated"),
                    source_url=p.get("url"),
                ))

        if not results:
            results.append(ClaimResult(
                market=Market.LK,
                ingredient=ingredient,
                claim_type=claim_type or "health_claim",
                status=ClaimStatus.NOT_DEFINED,
                conditions=(
                    f"No pre-indexed FCAU/SLSI claim data for '{ingredient}'. "
                    "Sri Lanka follows Codex CAC/GL 23 principles. "
                    "Refer to Food Labelling Regulations 2005 via the Ministry of Health "
                    "food control page or SLSI (slsi.lk) for applicable standards."
                ),
                basis=RegulatoryBasis(
                    instrument="Food Act No. 26/1980 + Food Labelling Regulations 2005",
                    url=_BASE_URL,
                    notes="Limited positive claim list; most health claims require individual FCAU review.",
                ),
                source_url=_BASE_URL,
            ))

        return results

    async def get_standard(self, standard_id: str) -> Standard | None:
        upper = standard_id.upper()
        for key, data in _KNOWN_STANDARDS.items():
            if upper in key.upper() or key.upper() in upper:
                return Standard(standard_id=key, market=Market.LK, **data)
        return None

    async def search_standards(self, query: str) -> list[Standard]:
        q = query.lower()
        return [
            Standard(standard_id=k, market=Market.LK, **v)
            for k, v in _KNOWN_STANDARDS.items()
            if q in k.lower() or q in v["title"].lower() or q in (v.get("summary") or "").lower()
        ] or [Standard(standard_id=k, market=Market.LK, **v) for k, v in _KNOWN_STANDARDS.items()]

    async def get_market_overview(self) -> MarketOverview:
        return MarketOverview(
            market=Market.LK,
            authority_name="Food Control Administration Unit (FCAU) / Sri Lanka Standards Institution (SLSI)",
            authority_url=_BASE_URL,
            key_legislation=[
                "Food Act No. 26 of 1980 (as amended 1999, 2011)",
                "Food (Labelling) Regulations 2005 (Gazette No. 1405/28)",
                "SLS 516 -- Labelling of Prepackaged Foods (SLSI)",
            ],
            health_claims_framework=(
                "Sri Lanka regulates health claims under the Food Act 1980 and Food Labelling "
                "Regulations 2005. Claims must be truthful, not misleading, and scientifically "
                "substantiated. Approach follows Codex CAC/GL 23 principles. "
                "SLSI publishes SLS standards aligned with Codex STAN 1-1985 for labelling. "
                "No comprehensive positive health claims list; claims evaluated case-by-case by FCAU. "
                "Full texts available as gazette PDFs from the Department of Government Printing."
            ),
            notes=(
                f"FCAU (Ministry of Health): {_BASE_URL} | "
                f"SLSI: {_SLSI_URL} | "
                f"Government documents: {_DOCS_URL}"
            ),
        )
