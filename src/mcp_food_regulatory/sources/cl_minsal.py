"""
Chile -- Ministry of Health (MINSAL) / Public Health Institute (ISP).

Key regulations:
  Decreto Supremo 977/96 (RSA) -- Reglamento Sanitario de los Alimentos
  Articles 110-115 govern health claims.
  Ley 20.606 (2012) -- Introduced mandatory octagonal warning labels
  (high in calories, sodium, sugar, saturated fat).

BCN (Biblioteca del Congreso Nacional) has full consolidated RSA text.
Very limited positive claim list; most health claims are restricted.

Strategy: seed RSA Articles 110-115 provisions; note that Chile's framework
is primarily restrictive rather than a positive list.
"""

from __future__ import annotations
from mcp_food_regulatory.models import (
    Market, ClaimResult, ClaimStatus, Standard, MarketOverview, RegulatoryBasis
)
from mcp_food_regulatory.sources.base import RegulatorySource

_BASE_URL = "https://www.ispch.cl"
_MINSAL_URL = "https://www.minsal.cl"
_BCN_RSA_URL = "https://www.bcn.cl/leychile/navegar?idNorma=71271"
_ISP_NORMATIVA_URL = "https://www.ispch.cl/normativa/"

_KNOWN_STANDARDS: dict[str, dict] = {
    "DS 977/96 RSA": {
        "title": "Decreto Supremo 977/96 -- Reglamento Sanitario de los Alimentos (RSA)",
        "category": "supreme_decree",
        "adopted": "1996",
        "last_amended": "2023",
        "summary": (
            "Primary food sanitary regulations for Chile. Articles 110-115 govern health "
            "and nutrition claims. The RSA is regularly amended via MINSAL decrees. "
            "Consolidated text available at BCN (Biblioteca del Congreso Nacional). "
            "Claims must be truthful, not misleading, and consistent with the RSA provisions."
        ),
        "full_text_url": _BCN_RSA_URL,
    },
    "Ley 20.606": {
        "title": "Ley 20.606 sobre Composición Nutricional de los Alimentos y su Publicidad",
        "category": "law",
        "adopted": "2012",
        "summary": (
            "Introduced mandatory octagonal front-of-pack warning labels for foods high in "
            "calories, sodium, total sugar, or saturated fat. Chile was the first country "
            "to implement this system, later adopted by Mexico, Peru, and others. "
            "Advertising restrictions apply to products with warning seals, especially "
            "when directed at children."
        ),
        "full_text_url": "https://www.bcn.cl/leychile/navegar?idNorma=1041570",
    },
    "DS 13/2015": {
        "title": "Decreto Supremo 13/2015 -- Reglamento de la Ley 20.606",
        "category": "supreme_decree",
        "adopted": "2015",
        "last_amended": "2019",
        "summary": (
            "Implementing regulation for Ley 20.606 setting the nutrient thresholds "
            "for octagonal warning seals and the advertising restrictions applicable "
            "to products bearing warnings."
        ),
        "full_text_url": _BCN_RSA_URL,
    },
}

_CLAIM_PROVISIONS: dict[str, list[dict]] = {
    "vitamin c": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "RSA Art. 110-115: Nutrition claims for vitamins must meet minimum content "
                "thresholds. 'Fuente de Vitamina C' -- at least 15% VDR per 100g/100ml or serving. "
                "'Buena fuente de Vitamina C' -- at least 30% VDR. "
                "Chilean VDR for Vitamin C: 45 mg/day. "
                "Product must not bear an octagonal warning seal that would restrict health claims."
            ),
            "instrument": "DS 977/96 RSA Art. 110-115",
            "url": _BCN_RSA_URL,
            "last_updated": "2023",
        }
    ],
    "calcium": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "RSA Art. 110-115: 'Fuente de Calcio' -- at least 15% VDR per 100g/100ml. "
                "'Buena fuente de Calcio' -- at least 30% VDR. VDR for Calcium: 800 mg/day. "
                "Health claim linking calcium to bone health may be permitted if scientifically "
                "substantiated and approved by MINSAL/ISP under RSA provisions."
            ),
            "instrument": "DS 977/96 RSA Art. 110-115",
            "url": _BCN_RSA_URL,
            "last_updated": "2023",
        }
    ],
    "dietary fibre": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "RSA Art. 110-115: 'Fuente de Fibra Dietética' -- at least 3g/100g solid "
                "or 1.5g/100ml liquid. 'Buena fuente de Fibra' -- at least 6g/100g. "
                "Products cannot simultaneously bear a dietary fibre claim and an octagonal "
                "warning seal for high sugar/sodium content without adequate context."
            ),
            "instrument": "DS 977/96 RSA Art. 110-115",
            "url": _BCN_RSA_URL,
            "last_updated": "2023",
        }
    ],
}


class CLMINSALSource(RegulatorySource):
    """MINSAL/ISP data source for Chile."""

    market = Market.CL
    BASE_URL = _MINSAL_URL

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
                    market=Market.CL,
                    ingredient=ingredient,
                    claim_type=p["claim_type"],
                    status=ClaimStatus(p["status"]),
                    conditions=p.get("conditions"),
                    basis=RegulatoryBasis(
                        instrument=p["instrument"],
                        url=p.get("url"),
                        notes="Chile's RSA Articles 110-115 govern health claims. Ley 20.606 octagonal warnings may restrict certain claims. Spanish language primary.",
                    ),
                    last_updated=p.get("last_updated"),
                    source_url=p.get("url"),
                ))

        if not results:
            results.append(ClaimResult(
                market=Market.CL,
                ingredient=ingredient,
                claim_type=claim_type or "health_claim",
                status=ClaimStatus.NOT_DEFINED,
                conditions=(
                    f"No pre-indexed MINSAL/ISP claim data for '{ingredient}'. "
                    "Chile has a limited positive claims list under RSA DS 977/96. "
                    "Check RSA Articles 110-115 via BCN (bcn.cl) or ISP normativa page."
                ),
                basis=RegulatoryBasis(
                    instrument="DS 977/96 RSA Art. 110-115",
                    url=_BCN_RSA_URL,
                    notes="Very limited positive claim list. Most health claims require individual MINSAL/ISP approval.",
                ),
                source_url=_BCN_RSA_URL,
            ))

        return results

    async def get_standard(self, standard_id: str) -> Standard | None:
        upper = standard_id.upper()
        for key, data in _KNOWN_STANDARDS.items():
            if upper in key.upper() or key.upper() in upper:
                return Standard(standard_id=key, market=Market.CL, **data)
        return None

    async def search_standards(self, query: str) -> list[Standard]:
        q = query.lower()
        return [
            Standard(standard_id=k, market=Market.CL, **v)
            for k, v in _KNOWN_STANDARDS.items()
            if q in k.lower() or q in v["title"].lower() or q in (v.get("summary") or "").lower()
        ] or [Standard(standard_id=k, market=Market.CL, **v) for k, v in _KNOWN_STANDARDS.items()]

    async def get_market_overview(self) -> MarketOverview:
        return MarketOverview(
            market=Market.CL,
            authority_name="Ministerio de Salud (MINSAL) / Instituto de Salud Pública (ISP)",
            authority_url=_MINSAL_URL,
            key_legislation=[
                "Decreto Supremo 977/96 -- Reglamento Sanitario de los Alimentos (RSA)",
                "Ley 20.606 -- Nutritional Composition and Advertising Law (2012)",
                "Decreto Supremo 13/2015 -- Implementing Regulation for Ley 20.606",
            ],
            health_claims_framework=(
                "Chile's health claims are governed by DS 977/96 (RSA) Articles 110-115. "
                "The positive claims list is very limited; most health claims require individual "
                "MINSAL/ISP approval. Ley 20.606 (2012) introduced mandatory octagonal 'HIGH IN' "
                "front-of-pack warning seals for foods exceeding nutrient thresholds for calories, "
                "sodium, sugars, and saturated fat -- Chile was the first country to implement this system. "
                "Products bearing octagonal warnings face advertising restrictions, especially "
                "targeting children. The RSA is consolidated on BCN (bcn.cl)."
            ),
            notes=(
                "BCN maintains the authoritative consolidated text of the RSA at: "
                f"{_BCN_RSA_URL}"
            ),
        )
