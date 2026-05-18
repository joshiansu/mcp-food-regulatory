"""
Nepal -- Department of Food Technology and Quality Control (DFTQC).

Key regulations:
  Food Act 1966 (2nd Amendment 2017) -- primary legislation
  Food Rules 1970 (amended) -- implementing regulations
  Food Labelling Directive 2074 BS (2017 AD) -- nutrition labelling and claims

DFTQC operates under the Ministry of Agriculture and Livestock Development.
Codex-aligned. Content primarily in Nepali. Very limited structured online data.
"""

from __future__ import annotations
from mcp_food_regulatory.models import (
    Market, ClaimResult, ClaimStatus, Standard, MarketOverview, RegulatoryBasis
)
from mcp_food_regulatory.sources.base import RegulatorySource

_BASE_URL = "http://www.dftqc.gov.np"
_MOALD_URL = "https://www.moald.gov.np"
_NEPALLAW_URL = "https://www.nepallaw.gov.np"

_KNOWN_STANDARDS: dict[str, dict] = {
    "Food Act 1966": {
        "title": "Food Act, 2023 BS (1966 AD) -- 2nd Amendment 2073 BS (2017 AD)",
        "category": "legislation",
        "adopted": "1966",
        "last_amended": "2017",
        "summary": (
            "Primary food legislation in Nepal. Prohibits adulteration, misbranding, and "
            "false/misleading representations on food labels including health claims. "
            "Empowers the Government of Nepal to issue food regulations and standards. "
            "Enforced by DFTQC."
        ),
        "full_text_url": _NEPALLAW_URL,
    },
    "Food Rules 1970": {
        "title": "Food Rules, 2027 BS (1970 AD) -- as amended",
        "category": "regulation",
        "adopted": "1970",
        "last_amended": "2017",
        "summary": (
            "Implementing regulations under the Food Act 1966. Covers food standards, "
            "labelling requirements, and enforcement procedures. "
            "Amended multiple times; current consolidated version maintained by DFTQC."
        ),
        "full_text_url": _BASE_URL,
    },
    "Food Labelling Directive 2074": {
        "title": "Food Labelling and Packaging Directive 2074 BS (2017 AD)",
        "category": "directive",
        "adopted": "2017",
        "summary": (
            "Governs mandatory label elements, nutrition declaration, and conditions for "
            "nutrition and health claims for prepackaged foods in Nepal. "
            "Codex-aligned approach. Claims must be truthful and substantiated. "
            "Published in Nepali; enforced by DFTQC."
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
                "Food Labelling Directive 2074 / Codex-aligned: "
                "'Source of Vitamin C' -- at least 15% RDI per 100g/100ml or per serving. "
                "'High in Vitamin C' -- at least 30% RDI. "
                "Nepali RDI for Vitamin C: 40 mg/day. "
                "Claims must comply with Food Act 1966 misbranding provisions."
            ),
            "instrument": "Food Labelling Directive 2074 + Food Act 1966",
            "url": _BASE_URL,
            "last_updated": "2017",
        }
    ],
    "vitamin d": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Codex-aligned: 'Source of Vitamin D' -- at least 15% RDI per 100g/100ml. "
                "RDI for Vitamin D: 5 µg/day. "
                "Health function claims require DFTQC review and substantiation."
            ),
            "instrument": "Food Labelling Directive 2074",
            "url": _BASE_URL,
            "last_updated": "2017",
        }
    ],
    "calcium": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Codex-aligned: 'Source of Calcium' -- at least 15% RDI per 100g/100ml. "
                "'High in Calcium' -- at least 30% RDI. RDI for Calcium: 800 mg/day. "
                "Disease risk reduction claims require individual DFTQC approval."
            ),
            "instrument": "Food Labelling Directive 2074 + Food Rules 1970",
            "url": _BASE_URL,
            "last_updated": "2017",
        }
    ],
    "dietary fibre": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Codex-aligned: 'Source of Dietary Fibre' -- at least 3g/100g or 1.5g/100kcal. "
                "'High in Dietary Fibre' -- at least 6g/100g. "
                "Per Food Labelling Directive 2074."
            ),
            "instrument": "Food Labelling Directive 2074",
            "url": _BASE_URL,
            "last_updated": "2017",
        }
    ],
}


class NPDFTQCSource(RegulatorySource):
    """DFTQC data source for Nepal."""

    market = Market.NP
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
                    market=Market.NP,
                    ingredient=ingredient,
                    claim_type=p["claim_type"],
                    status=ClaimStatus(p["status"]),
                    conditions=p.get("conditions"),
                    basis=RegulatoryBasis(
                        instrument=p["instrument"],
                        url=p.get("url"),
                        notes="Nepal follows Codex CAC/GL 23 principles via Food Labelling Directive 2074. Content primarily in Nepali.",
                    ),
                    last_updated=p.get("last_updated"),
                    source_url=p.get("url"),
                ))

        if not results:
            results.append(ClaimResult(
                market=Market.NP,
                ingredient=ingredient,
                claim_type=claim_type or "health_claim",
                status=ClaimStatus.NOT_DEFINED,
                conditions=(
                    f"No pre-indexed DFTQC claim data for '{ingredient}'. "
                    "Nepal follows Codex CAC/GL 23 principles via the Food Labelling Directive 2074. "
                    "Contact DFTQC (dftqc.gov.np) directly or refer to Nepal Law Commission "
                    "(nepallaw.gov.np) for the Food Act and Rules. Content primarily in Nepali."
                ),
                basis=RegulatoryBasis(
                    instrument="Food Act 1966 + Food Labelling Directive 2074",
                    url=_BASE_URL,
                    notes="Very limited structured online data in English. Codex-aligned framework.",
                ),
                source_url=_BASE_URL,
            ))

        return results

    async def get_standard(self, standard_id: str) -> Standard | None:
        upper = standard_id.upper()
        for key, data in _KNOWN_STANDARDS.items():
            if upper in key.upper() or key.upper() in upper:
                return Standard(standard_id=key, market=Market.NP, **data)
        return None

    async def search_standards(self, query: str) -> list[Standard]:
        q = query.lower()
        return [
            Standard(standard_id=k, market=Market.NP, **v)
            for k, v in _KNOWN_STANDARDS.items()
            if q in k.lower() or q in v["title"].lower() or q in (v.get("summary") or "").lower()
        ] or [Standard(standard_id=k, market=Market.NP, **v) for k, v in _KNOWN_STANDARDS.items()]

    async def get_market_overview(self) -> MarketOverview:
        return MarketOverview(
            market=Market.NP,
            authority_name="Department of Food Technology and Quality Control (DFTQC)",
            authority_url=_BASE_URL,
            key_legislation=[
                "Food Act, 2023 BS / 1966 AD (2nd Amendment 2017)",
                "Food Rules, 2027 BS / 1970 AD (as amended)",
                "Food Labelling and Packaging Directive 2074 BS / 2017 AD",
            ],
            health_claims_framework=(
                "Nepal regulates health claims under the Food Act 1966 and Food Labelling "
                "Directive 2074. DFTQC enforces labelling standards under the Ministry of "
                "Agriculture and Livestock Development. Approach is Codex CAC/GL 23-aligned -- "
                "claims must be truthful, scientifically substantiated, and not misleading. "
                "No comprehensive positive health claims list exists; evaluated case-by-case. "
                "Primary content in Nepali. Nepal uses Bikram Sambat (BS) calendar for dating."
            ),
            notes=(
                f"DFTQC: {_BASE_URL} | "
                f"Ministry of Agriculture: {_MOALD_URL} | "
                f"Nepal Law Commission: {_NEPALLAW_URL}"
            ),
        )
