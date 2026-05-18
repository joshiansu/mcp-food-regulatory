"""
Mexico -- Federal Commission for Protection against Health Risks (COFEPRIS) /
now CONAMER (Comisión Nacional de Mejora Regulatoria).

Key regulations:
  NOM-051-SCFI/SSA1-2010 -- General Specifications for Labelling of Pre-packaged
  Food and Non-Alcoholic Beverages (updated 2020 with front-of-pack seals)
  NOM-086-SSA1-1994 -- Foods and beverages with nutritional modifications

Health claims governed by Normas Oficiales Mexicanas (NOMs). Full texts published
in DOF (Diario Oficial de la Federación). Mexico adopted octagonal warning seals
in 2020 NOM-051 amendment.

Most health claims require individual COFEPRIS/SSA authorisation.
"""

from __future__ import annotations
from mcp_food_regulatory.models import (
    Market, ClaimResult, ClaimStatus, Standard, MarketOverview, RegulatoryBasis
)
from mcp_food_regulatory.sources.base import RegulatorySource

_BASE_URL = "https://www.gob.mx/cofepris"
_DOF_URL = "https://www.dof.gob.mx"
_COFEPRIS_URL = "https://www.gob.mx/cofepris"
_NOM051_URL = (
    "https://www.dof.gob.mx/nota_detalle.php?codigo=5609582&fecha=27/03/2020"
)

_KNOWN_STANDARDS: dict[str, dict] = {
    "NOM-051-SCFI/SSA1-2010": {
        "title": "NOM-051-SCFI/SSA1-2010 -- Especificaciones Generales de Etiquetado para Alimentos y Bebidas",
        "category": "norma_oficial_mexicana",
        "adopted": "2010",
        "last_amended": "2020",
        "summary": (
            "Primary labelling standard for pre-packaged foods and non-alcoholic beverages in Mexico. "
            "2020 amendment introduced mandatory front-of-pack octagonal warning seals (black) "
            "for products exceeding nutrient thresholds (calories, sodium, sugar, saturated fat, "
            "trans fat). Also restricts advertising symbols (cartoon characters) and claims "
            "on products with warning seals. Full text at DOF."
        ),
        "full_text_url": _NOM051_URL,
    },
    "NOM-086-SSA1-1994": {
        "title": "NOM-086-SSA1-1994 -- Alimentos y Bebidas No Alcohólicas con Modificaciones en su Composición",
        "category": "norma_oficial_mexicana",
        "adopted": "1994",
        "summary": (
            "Governs foods with nutritional modifications (e.g. 'reduced fat', 'light', 'enriched'). "
            "Sets conditions for nutrient content claims. Works in conjunction with NOM-051."
        ),
        "full_text_url": _DOF_URL,
    },
    "NOM-218-SSA1-2011": {
        "title": "NOM-218-SSA1-2011 -- Productos y Servicios. Bebidas Saborizadas",
        "category": "norma_oficial_mexicana",
        "adopted": "2011",
        "summary": (
            "Labelling standard for flavoured beverages in Mexico. "
            "Relevant for health claims on functional beverages."
        ),
        "full_text_url": _DOF_URL,
    },
}

_CLAIM_PROVISIONS: dict[str, list[dict]] = {
    "vitamin c": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "NOM-051 / NOM-086: 'Fuente de Vitamina C' -- at least 10-15% VDR per porción. "
                "Mexican VDR for Vitamin C: 60 mg/day (adults). "
                "Products bearing octagonal warning seals may not use health claims in front of pack. "
                "Nutrient content claims permitted on side/back panels."
            ),
            "instrument": "NOM-051-SCFI/SSA1-2010 + NOM-086-SSA1-1994",
            "url": _NOM051_URL,
            "last_updated": "2020",
        }
    ],
    "vitamin d": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "NOM-086: 'Fuente de Vitamina D' when product provides at least 10-15% VDR. "
                "Mexican VDR for Vitamin D: 5 µg/day (200 IU). "
                "Fortified foods must comply with NOM-086 modification requirements."
            ),
            "instrument": "NOM-086-SSA1-1994 + NOM-051",
            "url": _NOM051_URL,
            "last_updated": "2020",
        }
    ],
    "calcium": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "NOM-086: 'Fuente de Calcio' -- at least 10-15% VDR per serving. "
                "Mexican VDR for Calcium: 900 mg/day (adults). "
                "Disease risk reduction claim for calcium/osteoporosis requires individual "
                "COFEPRIS/SSA authorisation -- not part of a general permitted list."
            ),
            "instrument": "NOM-086-SSA1-1994",
            "url": _DOF_URL,
            "last_updated": "1994",
        }
    ],
    "dietary fibre": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "NOM-086: 'Fuente de Fibra' -- at least 3g/100g or 1.5g/100kcal. "
                "'Alto en Fibra' -- at least 6g/100g or 3g/100kcal. "
                "Fibre content claims are among the most straightforward in Mexico."
            ),
            "instrument": "NOM-086-SSA1-1994 + NOM-051",
            "url": _NOM051_URL,
            "last_updated": "2020",
        }
    ],
    "omega-3": [
        {
            "claim_type": "health_claim",
            "status": "conditional",
            "conditions": (
                "No general permitted list for omega-3 health claims in Mexico. "
                "Nutrient content claim 'Fuente de Omega-3' may be used when product meets "
                "Codex-equivalent thresholds (0.3g ALA or 40mg EPA+DHA per 100g). "
                "Cardiovascular health claims require individual COFEPRIS authorisation. "
                "Claims must not appear on front panel if product has an octagonal warning seal."
            ),
            "instrument": "NOM-051 + NOM-086 + COFEPRIS authorisation",
            "url": _COFEPRIS_URL,
            "last_updated": "2020",
        }
    ],
}


class MXCOFEPRISSource(RegulatorySource):
    """COFEPRIS data source for Mexico."""

    market = Market.MX
    BASE_URL = _COFEPRIS_URL

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
                    market=Market.MX,
                    ingredient=ingredient,
                    claim_type=p["claim_type"],
                    status=ClaimStatus(p["status"]),
                    conditions=p.get("conditions"),
                    basis=RegulatoryBasis(
                        instrument=p["instrument"],
                        url=p.get("url"),
                        notes="Mexico regulates claims via NOMs. NOM-051 2020 amendment introduced octagonal warning seals. Most health claims require individual COFEPRIS authorisation.",
                    ),
                    last_updated=p.get("last_updated"),
                    source_url=p.get("url"),
                ))

        if not results:
            results.append(ClaimResult(
                market=Market.MX,
                ingredient=ingredient,
                claim_type=claim_type or "health_claim",
                status=ClaimStatus.NOT_DEFINED,
                conditions=(
                    f"No pre-indexed COFEPRIS claim data for '{ingredient}'. "
                    "Mexico has a limited positive health claims list. "
                    "Most claims require individual COFEPRIS/SSA authorisation. "
                    "Check DOF (dof.gob.mx) for NOM texts or COFEPRIS portal for authorisation procedures."
                ),
                basis=RegulatoryBasis(
                    instrument="NOM-051-SCFI/SSA1-2010 + NOM-086-SSA1-1994",
                    url=_NOM051_URL,
                    notes="Full NOM texts available at DOF (Diario Oficial de la Federación). Spanish language.",
                ),
                source_url=_COFEPRIS_URL,
            ))

        return results

    async def get_standard(self, standard_id: str) -> Standard | None:
        upper = standard_id.upper()
        for key, data in _KNOWN_STANDARDS.items():
            if upper in key.upper() or key.upper() in upper:
                return Standard(standard_id=key, market=Market.MX, **data)
        return None

    async def search_standards(self, query: str) -> list[Standard]:
        q = query.lower()
        return [
            Standard(standard_id=k, market=Market.MX, **v)
            for k, v in _KNOWN_STANDARDS.items()
            if q in k.lower() or q in v["title"].lower() or q in (v.get("summary") or "").lower()
        ] or [Standard(standard_id=k, market=Market.MX, **v) for k, v in _KNOWN_STANDARDS.items()]

    async def get_market_overview(self) -> MarketOverview:
        return MarketOverview(
            market=Market.MX,
            authority_name="Comisión Federal para la Protección contra Riesgos Sanitarios (COFEPRIS) / SSA",
            authority_url=_COFEPRIS_URL,
            key_legislation=[
                "NOM-051-SCFI/SSA1-2010 -- Food and Beverage Labelling (amended 2020)",
                "NOM-086-SSA1-1994 -- Modified-Composition Foods",
                "Ley General de Salud (General Health Law)",
                "Reglamento de Control Sanitario de Productos y Servicios",
            ],
            health_claims_framework=(
                "Mexico governs food claims through Normas Oficiales Mexicanas (NOMs). "
                "NOM-086 permits nutrient content claims with specified thresholds. "
                "Health claims (disease risk reduction) have a limited pre-approved list; "
                "most require individual COFEPRIS/SSA authorisation. "
                "NOM-051 (2020 amendment) introduced mandatory black octagonal warning seals "
                "for products high in calories, sodium, sugars, saturated fat, or trans fat. "
                "Products bearing seals cannot display health or nutrition claims on the front panel "
                "or use advertising characters appealing to children."
            ),
            notes=(
                f"DOF (Diario Oficial): {_DOF_URL} -- official source for NOM full texts. "
                "All regulations in Spanish."
            ),
        )
