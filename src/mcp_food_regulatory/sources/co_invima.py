"""
Colombia -- Instituto Nacional de Vigilancia de Medicamentos y Alimentos (INVIMA).

Health claims in Colombia follow Codex CAC/GL 23-1997. INVIMA issues resolutions
as PDFs. The authoritative legal database is SUIN-Juriscol (suin-juriscol.gov.co).

Key regulation: Resolución 2508 de 2012 (general food labelling) and
Decreto 1275 de 2023 (nutritional profile and front-of-pack warnings).

Strategy: seed framework provisions; direct users to SUIN-Juriscol for full texts.
"""

from __future__ import annotations
from mcp_food_regulatory.models import (
    Market, ClaimResult, ClaimStatus, Standard, MarketOverview, RegulatoryBasis
)
from mcp_food_regulatory.sources.base import RegulatorySource

_BASE_URL = "https://www.invima.gov.co"
_SUIN_URL = "https://www.suin-juriscol.gov.co"
_NORMATIVA_URL = "https://www.invima.gov.co/normatividad-vigente"

_KNOWN_STANDARDS: dict[str, dict] = {
    "Resolución 2508/2012": {
        "title": "Resolución 2508 de 2012 -- Rotulado o Etiquetado de Alimentos",
        "category": "resolution",
        "adopted": "2012",
        "summary": (
            "Primary food labelling resolution for Colombia. "
            "Governs mandatory label elements, nutrition information, and permitted claims. "
            "Health and nutrition claims must align with Codex CAC/GL 23-1997. "
            "Claims not consistent with Codex guidelines are prohibited."
        ),
        "full_text_url": _SUIN_URL,
    },
    "Decreto 1275/2023": {
        "title": "Decreto 1275 de 2023 -- Etiquetado Nutricional Frontal",
        "category": "decree",
        "adopted": "2023",
        "summary": (
            "Introduces mandatory front-of-pack nutritional labelling (octagonal warning seals) "
            "for foods high in sodium, sugars, and saturated fat. "
            "Aligns Colombia with regional FOPL trend adopted in Chile, Mexico, and Peru."
        ),
        "full_text_url": _SUIN_URL,
    },
    "Codex CAC/GL 23-1997": {
        "title": "Codex Guidelines for Use of Nutrition and Health Claims (CAC/GL 23-1997)",
        "category": "codex_guideline",
        "adopted": "1997",
        "last_amended": "2013",
        "summary": (
            "International reference standard adopted by Colombia for nutrition and health claims. "
            "Defines conditions for nutrient content claims and disease risk reduction claims."
        ),
        "full_text_url": "https://www.fao.org/fao-who-codexalimentarius/codex-texts/guidelines/en/",
    },
}

_CLAIM_PROVISIONS: dict[str, list[dict]] = {
    "vitamin c": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Codex CAC/GL 23 (adopted by Colombia via Res. 2508/2012): "
                "'Fuente de Vitamina C' (Source) -- at least 15% RDI per 100g/100ml or serving. "
                "'Alto en Vitamina C' (High) -- at least 30% RDI. "
                "Colombian RDI for Vitamin C: 45 mg/day."
            ),
            "instrument": "Resolución 2508/2012 + Codex CAC/GL 23",
            "url": _NORMATIVA_URL,
            "last_updated": "2012",
        }
    ],
    "calcium": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Codex CAC/GL 23: 'Fuente de Calcio' -- at least 15% RDI per 100g/100ml. "
                "'Alto en Calcio' -- at least 30% RDI. Colombian RDI for Calcium: 800 mg/day. "
                "Disease risk reduction claim linking calcium and osteoporosis is permitted "
                "under Codex conditions if scientifically substantiated."
            ),
            "instrument": "Resolución 2508/2012 + Codex CAC/GL 23",
            "url": _NORMATIVA_URL,
            "last_updated": "2012",
        }
    ],
    "dietary fibre": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Codex CAC/GL 23: 'Fuente de Fibra' -- at least 3g/100g or 1.5g/100kcal. "
                "'Alto en Fibra' -- at least 6g/100g or 3g/100kcal. "
                "Aligned with Codex thresholds adopted via Res. 2508/2012."
            ),
            "instrument": "Resolución 2508/2012 + Codex CAC/GL 23",
            "url": _NORMATIVA_URL,
            "last_updated": "2012",
        }
    ],
}


class COINVIMASource(RegulatorySource):
    """INVIMA data source for Colombia."""

    market = Market.CO
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
                    market=Market.CO,
                    ingredient=ingredient,
                    claim_type=p["claim_type"],
                    status=ClaimStatus(p["status"]),
                    conditions=p.get("conditions"),
                    basis=RegulatoryBasis(
                        instrument=p["instrument"],
                        url=p.get("url"),
                        notes="Colombia follows Codex CAC/GL 23-1997. INVIMA publishes resolutions as PDFs; SUIN-Juriscol is the official legal database.",
                    ),
                    last_updated=p.get("last_updated"),
                    source_url=p.get("url"),
                ))

        if not results:
            results.append(ClaimResult(
                market=Market.CO,
                ingredient=ingredient,
                claim_type=claim_type or "health_claim",
                status=ClaimStatus.NOT_DEFINED,
                conditions=(
                    f"No pre-indexed INVIMA claim data for '{ingredient}'. "
                    "Colombia follows Codex CAC/GL 23-1997 for health claims. "
                    "Search SUIN-Juriscol for applicable resolutions or INVIMA normatividad page."
                ),
                basis=RegulatoryBasis(
                    instrument="Resolución 2508/2012 + Codex CAC/GL 23",
                    url=_NORMATIVA_URL,
                    notes="Claims embedded in labelling resolutions published as PDFs. Spanish language primary.",
                ),
                source_url=_NORMATIVA_URL,
            ))

        return results

    async def get_standard(self, standard_id: str) -> Standard | None:
        upper = standard_id.upper()
        for key, data in _KNOWN_STANDARDS.items():
            if upper in key.upper() or key.upper() in upper:
                return Standard(standard_id=key, market=Market.CO, **data)
        return None

    async def search_standards(self, query: str) -> list[Standard]:
        q = query.lower()
        return [
            Standard(standard_id=k, market=Market.CO, **v)
            for k, v in _KNOWN_STANDARDS.items()
            if q in k.lower() or q in v["title"].lower() or q in (v.get("summary") or "").lower()
        ] or [Standard(standard_id=k, market=Market.CO, **v) for k, v in _KNOWN_STANDARDS.items()]

    async def get_market_overview(self) -> MarketOverview:
        return MarketOverview(
            market=Market.CO,
            authority_name="Instituto Nacional de Vigilancia de Medicamentos y Alimentos (INVIMA)",
            authority_url=_BASE_URL,
            key_legislation=[
                "Resolución 2508 de 2012 -- Food Labelling",
                "Decreto 1275 de 2023 -- Front-of-Pack Nutritional Labelling",
                "Decreto 60 de 2002 -- Good Manufacturing Practice",
                "Codex CAC/GL 23-1997 -- Nutrition and Health Claims (reference)",
            ],
            health_claims_framework=(
                "Colombia requires health claims to be consistent with Codex CAC/GL 23-1997. "
                "Specific nutrition content claims follow Codex thresholds. "
                "Disease risk reduction claims must be scientifically substantiated. "
                "INVIMA issues resolutions as PDFs; no structured online claims database. "
                "Decreto 1275/2023 introduced front-of-pack octagonal warning labels. "
                "All claims and labels must be in Spanish."
            ),
            notes=(
                f"SUIN-Juriscol ({_SUIN_URL}) is the authoritative legal database for Colombian regulations."
            ),
        )
