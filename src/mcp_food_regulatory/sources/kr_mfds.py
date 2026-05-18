"""
South Korea -- Ministry of Food and Drug Safety (MFDS).

Health Functional Food Act governs health function claims (기능성).
Two pathways:
  1. Standardised (고시형) -- ingredients and function claims listed in
     MFDS Notice on Functional Ingredients; no individual authorisation needed.
  2. Individually recognised (개별인정형) -- proprietary ingredients that have
     received individual MFDS recognition.

General foods may not bear health function claims.

Data sources:
  - MFDS Food Safety Korea portal: foodsafetykorea.go.kr
  - Health Functional Food Information portal: healthyfoodinfo.mfds.go.kr
"""

from __future__ import annotations
from mcp_food_regulatory.models import (
    Market, ClaimResult, ClaimStatus, Standard, MarketOverview, RegulatoryBasis
)
from mcp_food_regulatory.sources.base import RegulatorySource

_BASE_URL = "https://www.foodsafetykorea.go.kr"
_HFF_PORTAL_URL = "https://healthyfoodinfo.mfds.go.kr"
_MFDS_URL = "https://www.mfds.go.kr"

_KNOWN_STANDARDS: dict[str, dict] = {
    "Health Functional Food Act": {
        "title": "Health Functional Food Act (건강기능식품에 관한 법률)",
        "category": "legislation",
        "adopted": "2002",
        "last_amended": "2022",
        "summary": (
            "Foundational legislation for health functional foods (건강기능식품) in Korea. "
            "Distinguishes health functional foods from general foods. "
            "Requires Good Manufacturing Practice (GMP) certification. "
            "Mandates that all function claims be pre-authorised by MFDS."
        ),
        "full_text_url": "https://www.law.go.kr/법령/건강기능식품에관한법률",
    },
    "MFDS HFF Standards": {
        "title": "Standards and Specifications for Health Functional Foods (식품의약품안전처고시)",
        "category": "regulation",
        "adopted": "2004",
        "last_amended": "2023",
        "summary": (
            "MFDS Notice listing all standardised functional ingredients with approved "
            "function claims, intake conditions, and identification/specification requirements. "
            "Ingredients include vitamins, minerals, probiotics, omega-3, red yeast rice, "
            "glucosamine, and many botanical extracts. "
            "Regularly updated as new ingredients receive standardised status."
        ),
        "full_text_url": "https://www.mfds.go.kr/bbs/index.do?catmenu=m03_03_02",
    },
    "Food Sanitation Act": {
        "title": "Food Sanitation Act (식품위생법)",
        "category": "legislation",
        "adopted": "1962",
        "last_amended": "2023",
        "summary": (
            "Governs safety and labelling for general foods in Korea. "
            "General foods may not use health function claim language reserved for "
            "health functional foods."
        ),
        "full_text_url": "https://www.law.go.kr/법령/식품위생법",
    },
}

_CLAIM_PROVISIONS: dict[str, list[dict]] = {
    "vitamin c": [
        {
            "claim_type": "health_function_claim",
            "status": "permitted",
            "conditions": (
                "Standardised ingredient (고시형). Approved function claims: "
                "'Vitamin C is necessary for the formation of connective tissue and "
                "contributes to the absorption of iron.' "
                "'Vitamin C contributes to the protection of cells against oxidative stress.' "
                "Intake: 60--2000 mg/day. Product must meet MFDS HFF Standards specifications."
            ),
            "instrument": "MFDS HFF Standards -- Vitamin C",
            "url": _HFF_PORTAL_URL,
            "last_updated": "2023",
        }
    ],
    "vitamin d": [
        {
            "claim_type": "health_function_claim",
            "status": "permitted",
            "conditions": (
                "Standardised ingredient. Approved function claims: "
                "'Vitamin D is necessary for the absorption of calcium and phosphorus.' "
                "'Vitamin D contributes to the maintenance of normal bones and teeth.' "
                "'Vitamin D contributes to the maintenance of normal muscle function.' "
                "Intake: 1.5--100 µg/day."
            ),
            "instrument": "MFDS HFF Standards -- Vitamin D",
            "url": _HFF_PORTAL_URL,
            "last_updated": "2023",
        }
    ],
    "calcium": [
        {
            "claim_type": "health_function_claim",
            "status": "permitted",
            "conditions": (
                "Standardised ingredient. Approved function claims: "
                "'Calcium is needed for the formation and maintenance of bones and teeth.' "
                "'Calcium contributes to normal blood coagulation.' "
                "Intake: 210--2500 mg/day."
            ),
            "instrument": "MFDS HFF Standards -- Calcium",
            "url": _HFF_PORTAL_URL,
            "last_updated": "2023",
        }
    ],
    "omega-3": [
        {
            "claim_type": "health_function_claim",
            "status": "permitted",
            "conditions": (
                "Standardised ingredient (EPA + DHA, fish oil). Approved function claims: "
                "'EPA and DHA contribute to the maintenance of normal blood triglyceride levels.' "
                "'DHA contributes to the maintenance of normal brain function.' "
                "Intake: EPA+DHA 0.5--2g/day. Must be from approved fish oil or algae sources."
            ),
            "instrument": "MFDS HFF Standards -- Omega-3 Fatty Acids",
            "url": _HFF_PORTAL_URL,
            "last_updated": "2023",
        }
    ],
    "probiotics": [
        {
            "claim_type": "health_function_claim",
            "status": "permitted",
            "conditions": (
                "Standardised ingredient. Approved function claims: "
                "'Probiotics may improve intestinal microflora balance.' "
                "Minimum viable count: 100 million CFU/daily intake. "
                "Must use one of 19 MFDS-approved probiotic strains listed in HFF Standards."
            ),
            "instrument": "MFDS HFF Standards -- Probiotics",
            "url": _HFF_PORTAL_URL,
            "last_updated": "2023",
        }
    ],
    "dietary fibre": [
        {
            "claim_type": "health_function_claim",
            "status": "permitted",
            "conditions": (
                "Multiple standardised fibre ingredients recognised: psyllium husk, "
                "inulin/FOS, beta-glucan (oat/barley), resistant starch, etc. "
                "Typical approved claim: 'May help maintain healthy bowel movements' or "
                "'May contribute to normal blood cholesterol levels' (for beta-glucan). "
                "Conditions vary by fibre type; refer to MFDS HFF Standards."
            ),
            "instrument": "MFDS HFF Standards -- Dietary Fibre",
            "url": _HFF_PORTAL_URL,
            "last_updated": "2023",
        }
    ],
}


class KRMFDSSource(RegulatorySource):
    """MFDS data source for South Korea."""

    market = Market.KR
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
                    market=Market.KR,
                    ingredient=ingredient,
                    claim_type=p["claim_type"],
                    status=ClaimStatus(p["status"]),
                    conditions=p.get("conditions"),
                    basis=RegulatoryBasis(
                        instrument=p["instrument"],
                        url=p.get("url"),
                        notes="Korea requires all health function claims to be pre-authorised. Standardised (고시형) ingredients may be used without individual approval.",
                    ),
                    last_updated=p.get("last_updated"),
                    source_url=p.get("url"),
                ))

        if not results:
            results.append(ClaimResult(
                market=Market.KR,
                ingredient=ingredient,
                claim_type=claim_type or "health_function_claim",
                status=ClaimStatus.NOT_DEFINED,
                conditions=(
                    f"No pre-indexed MFDS claim data for '{ingredient}'. "
                    "Search the Health Functional Food Information portal or MFDS "
                    "standards database for standardised ingredients. "
                    "Individually recognised ingredients require MFDS review."
                ),
                basis=RegulatoryBasis(
                    instrument="Health Functional Food Act + MFDS HFF Standards",
                    url=_HFF_PORTAL_URL,
                    notes="Korea requires GMP certification and pre-authorised function claims for health functional foods.",
                ),
                source_url=_HFF_PORTAL_URL,
            ))

        return results

    async def get_standard(self, standard_id: str) -> Standard | None:
        upper = standard_id.upper()
        for key, data in _KNOWN_STANDARDS.items():
            if upper in key.upper() or key.upper() in upper:
                return Standard(standard_id=key, market=Market.KR, **data)
        return None

    async def search_standards(self, query: str) -> list[Standard]:
        q = query.lower()
        return [
            Standard(standard_id=k, market=Market.KR, **v)
            for k, v in _KNOWN_STANDARDS.items()
            if q in k.lower() or q in v["title"].lower() or q in (v.get("summary") or "").lower()
        ] or [Standard(standard_id=k, market=Market.KR, **v) for k, v in _KNOWN_STANDARDS.items()]

    async def get_market_overview(self) -> MarketOverview:
        return MarketOverview(
            market=Market.KR,
            authority_name="Ministry of Food and Drug Safety (MFDS / 식품의약품안전처)",
            authority_url=_MFDS_URL,
            key_legislation=[
                "Health Functional Food Act (건강기능식품에 관한 법률, 2002)",
                "Standards and Specifications for Health Functional Foods (MFDS Notice)",
                "Food Sanitation Act (식품위생법)",
            ],
            health_claims_framework=(
                "Korea operates a dedicated Health Functional Food (HFF, 건강기능식품) category. "
                "Only MFDS-authorised function claims may be used, and only on registered HFF products. "
                "Two pathways: standardised (고시형) ingredients listed in MFDS HFF Standards "
                "with pre-approved claims -- no individual approval needed; and individually "
                "recognised (개별인정형) proprietary ingredients requiring MFDS review. "
                "GMP certification is mandatory. General foods cannot bear health function claims."
            ),
            notes=(
                "English summaries available on the MFDS international page. "
                f"Full ingredient database: {_HFF_PORTAL_URL}"
            ),
        )
