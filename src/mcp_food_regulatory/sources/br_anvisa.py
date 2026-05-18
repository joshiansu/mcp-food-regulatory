"""
Brazil -- Brazilian Health Regulatory Agency (ANVISA).

Key regulations:
  RDC 429/2020 -- Nutritional Labelling of Packaged Foods (updated requirements)
  RDC 432/2020 -- Complementary Nutritional Labelling (health and nutrition claims)
  RDC 432/2020 Annex I: Permitted nutrition claims with conditions
  RDC 432/2020 Annex II: Permitted health claims with conditions

ANVISA publishes the permitted claims list online and RDC 432/2020 as a PDF.
Good candidate for live scraping of the claims page (Portuguese).

Data source URL:
  https://www.gov.br/anvisa/pt-br/assuntos/alimentos/rotulagem/regime-regulatorio/alegacoes
"""

from __future__ import annotations
from mcp_food_regulatory.models import (
    Market, ClaimResult, ClaimStatus, Standard, MarketOverview, RegulatoryBasis
)
from mcp_food_regulatory.sources.base import RegulatorySource

_BASE_URL = "https://www.gov.br/anvisa/pt-br"
_CLAIMS_URL = (
    "https://www.gov.br/anvisa/pt-br/assuntos/alimentos/rotulagem/regime-regulatorio/alegacoes"
)
_RDC429_URL = "https://www.in.gov.br/en/web/dou/-/resolucao-rdc-n-429-de-8-de-outubro-de-2020"
_RDC432_URL = "https://www.in.gov.br/en/web/dou/-/resolucao-rdc-n-432-de-8-de-outubro-de-2020"

_KNOWN_STANDARDS: dict[str, dict] = {
    "RDC 429/2020": {
        "title": "Resolução RDC nº 429/2020 -- Rotulagem Nutricional de Alimentos Embalados",
        "category": "regulation",
        "adopted": "2020",
        "summary": (
            "Updated mandatory nutrition labelling requirements for packaged foods in Brazil. "
            "Introduces front-of-pack warning labels (high in sodium/sugars/saturated fat). "
            "Replaces RDC 360/2003. Aligned with MERCOSUR Resolution GMC 46/03."
        ),
        "full_text_url": _RDC429_URL,
    },
    "RDC 432/2020": {
        "title": "Resolução RDC nº 432/2020 -- Alegações de Propriedades Nutricionais e de Saúde",
        "category": "regulation",
        "adopted": "2020",
        "summary": (
            "Governs nutrition and health claims for packaged foods in Brazil. "
            "Annex I: Permitted nutrition claims (alegações de propriedades nutricionais). "
            "Annex II: Permitted health claims (alegações de propriedades de saúde) with "
            "conditions. Claims not in the annexes are prohibited unless specifically approved."
        ),
        "full_text_url": _RDC432_URL,
    },
    "MERCOSUR GMC 46/03": {
        "title": "MERCOSUR Resolution GMC 46/03 -- Nutritional Information on Packaged Foods",
        "category": "regional_standard",
        "adopted": "2003",
        "summary": (
            "MERCOSUR regional standard harmonising nutrition labelling across Brazil, "
            "Argentina, Paraguay, and Uruguay. Brazilian RDC 429/2020 aligns with this standard."
        ),
        "full_text_url": "https://www.mercosur.int/",
    },
}

_CLAIM_PROVISIONS: dict[str, list[dict]] = {
    "vitamin c": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "RDC 432/2020 Annex I: 'Fonte de Vitamina C' (Source) -- at least 15% VD "
                "per 100g/100ml or serving. 'Alto conteúdo de Vitamina C' (High) -- at least "
                "30% VD per 100g/100ml or serving. Brazilian VD for Vitamin C: 45 mg."
            ),
            "instrument": "RDC 432/2020 Annex I",
            "url": _CLAIMS_URL,
            "last_updated": "2020",
        }
    ],
    "vitamin d": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "RDC 432/2020 Annex I: 'Fonte de Vitamina D' -- at least 15% VD per 100g/100ml. "
                "'Alto conteúdo de Vitamina D' -- at least 30% VD. Brazilian VD for Vitamin D: 5 µg."
            ),
            "instrument": "RDC 432/2020 Annex I",
            "url": _CLAIMS_URL,
            "last_updated": "2020",
        }
    ],
    "calcium": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "RDC 432/2020 Annex I: 'Fonte de Cálcio' -- at least 15% VD. "
                "'Alto conteúdo de Cálcio' -- at least 30% VD. Brazilian VD for Calcium: 1000 mg. "
                "Annex II health claim: 'O cálcio auxilia no desenvolvimento e manutenção de "
                "ossos e dentes saudáveis' (Calcium aids development and maintenance of healthy "
                "bones and teeth) -- conditions: meets 'source of calcium' threshold."
            ),
            "instrument": "RDC 432/2020 Annex I & II",
            "url": _CLAIMS_URL,
            "last_updated": "2020",
        }
    ],
    "dietary fibre": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "RDC 432/2020 Annex I: 'Fonte de Fibra Alimentar' -- at least 2.5g/100g "
                "or 1.25g/100kcal (solid) or 1.25g/100ml or 0.625g/100kcal (liquid). "
                "'Alto conteúdo de Fibra Alimentar' -- double the source threshold."
            ),
            "instrument": "RDC 432/2020 Annex I",
            "url": _CLAIMS_URL,
            "last_updated": "2020",
        }
    ],
    "omega-3": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "RDC 432/2020 Annex I: 'Fonte de Ômega 3' -- at least 0.3g ALA per 100g "
                "or at least 40mg EPA+DHA per 100g. "
                "Annex II health claim for omega-3 and cardiovascular health may be available "
                "-- check current ANVISA claims register for exact wording and conditions."
            ),
            "instrument": "RDC 432/2020 Annex I",
            "url": _CLAIMS_URL,
            "last_updated": "2020",
        }
    ],
}


class BRANVISASource(RegulatorySource):
    """ANVISA data source for Brazil."""

    market = Market.BR
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
                    market=Market.BR,
                    ingredient=ingredient,
                    claim_type=p["claim_type"],
                    status=ClaimStatus(p["status"]),
                    conditions=p.get("conditions"),
                    basis=RegulatoryBasis(
                        instrument=p["instrument"],
                        url=p.get("url"),
                        notes="ANVISA RDC 432/2020 governs nutrition (Annex I) and health (Annex II) claims in Brazil. Portuguese language.",
                    ),
                    last_updated=p.get("last_updated"),
                    source_url=p.get("url"),
                ))

        if not results:
            results.append(ClaimResult(
                market=Market.BR,
                ingredient=ingredient,
                claim_type=claim_type or "health_claim",
                status=ClaimStatus.NOT_DEFINED,
                conditions=(
                    f"No pre-indexed ANVISA claim data for '{ingredient}'. "
                    "Check the ANVISA claims register (alegações) online or download "
                    "RDC 432/2020 Annex I & II for the full permitted claims list."
                ),
                basis=RegulatoryBasis(
                    instrument="RDC 432/2020",
                    url=_CLAIMS_URL,
                    notes="ANVISA publishes the permitted claims list online. Content primarily in Portuguese.",
                ),
                source_url=_CLAIMS_URL,
            ))

        return results

    async def get_standard(self, standard_id: str) -> Standard | None:
        upper = standard_id.upper()
        for key, data in _KNOWN_STANDARDS.items():
            if upper in key.upper() or key.upper() in upper:
                return Standard(standard_id=key, market=Market.BR, **data)
        return None

    async def search_standards(self, query: str) -> list[Standard]:
        q = query.lower()
        return [
            Standard(standard_id=k, market=Market.BR, **v)
            for k, v in _KNOWN_STANDARDS.items()
            if q in k.lower() or q in v["title"].lower() or q in (v.get("summary") or "").lower()
        ] or [Standard(standard_id=k, market=Market.BR, **v) for k, v in _KNOWN_STANDARDS.items()]

    async def get_market_overview(self) -> MarketOverview:
        return MarketOverview(
            market=Market.BR,
            authority_name="Agência Nacional de Vigilância Sanitária (ANVISA)",
            authority_url=_BASE_URL,
            key_legislation=[
                "RDC 429/2020 -- Nutritional Labelling of Packaged Foods",
                "RDC 432/2020 -- Nutrition and Health Claims",
                "MERCOSUR GMC Resolution 46/03 -- Harmonised Nutrition Information",
                "Lei nº 6.437/1977 -- Sanitary Infractions and Penalties",
            ],
            health_claims_framework=(
                "Brazil requires all nutrition and health claims to comply with RDC 432/2020. "
                "Annex I permits specific nutrition claims (e.g. 'source of', 'light', 'reduced') "
                "when quantitative thresholds are met. Annex II permits specific health claims "
                "linking food/nutrient to a health function. Claims not listed in the annexes "
                "are prohibited. Front-of-pack warning labels (high in sodium/sugars/saturated fat) "
                "introduced by RDC 429/2020 are mandatory when thresholds are exceeded."
            ),
            notes=(
                "ANVISA Consultas portal is searchable for regulatory texts. "
                f"Live claims register: {_CLAIMS_URL} (Portuguese)."
            ),
        )
