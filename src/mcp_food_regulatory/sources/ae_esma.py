"""
UAE -- Emirates Authority for Standardisation and Metrology (ESMA) /
Dubai Municipality (DM) / Abu Dhabi Agriculture and Food Safety Authority (ADAFSA).

UAE adopts GCC standards via GSO (Gulf Standardisation Organisation). Health claims
largely reference Codex CAC/GL 23. ESMA databank has UAE standards (some subscription).
Dubai Municipality publishes food safety circulars.

Key standards:
  UAE.S GSO 9/2013 -- Nutrition labelling (adopted GCC standard)
  GSO CAC/GL 23 -- GCC adoption of Codex health claims guidelines
  UAE.S 2055 -- Food labelling general requirements
"""

from __future__ import annotations
from mcp_food_regulatory.models import (
    Market, ClaimResult, ClaimStatus, Standard, MarketOverview, RegulatoryBasis
)
from mcp_food_regulatory.sources.base import RegulatorySource

_BASE_URL = "https://www.esma.gov.ae"
_DM_URL = "https://www.dm.gov.ae/business-in-dubai/food-safety/"
_GSO_URL = "https://www.gso.org.sa"
_ADAFSA_URL = "https://www.adafsa.gov.ae"

_KNOWN_STANDARDS: dict[str, dict] = {
    "UAE.S GSO 9:2013": {
        "title": "UAE.S GSO 9:2013 -- Nutrition Labelling of Prepackaged Foods",
        "category": "uae_standard",
        "adopted": "2013",
        "summary": (
            "GCC/UAE standard for nutrition labelling of prepackaged foods. "
            "Defines mandatory nutrition declaration requirements and nutrient reference "
            "daily intakes (RDI) used as the basis for nutrient content claims in the UAE. "
            "Adopted from GCC GSO standard."
        ),
        "full_text_url": _GSO_URL,
    },
    "GSO CAC/GL 23": {
        "title": "GCC Standard GSO CAC/GL 23 -- Guidelines for Use of Nutrition and Health Claims",
        "category": "gcc_standard",
        "adopted": "2013",
        "summary": (
            "GCC adoption of Codex CAC/GL 23-1997. Defines conditions for nutrition claims "
            "('source of', 'high in', 'low', 'free') and health claims (nutrient function, "
            "disease risk reduction) across GCC states including UAE."
        ),
        "full_text_url": _GSO_URL,
    },
    "UAE.S 2055": {
        "title": "UAE.S 2055 -- General Requirements for Labelling of Prepackaged Food",
        "category": "uae_standard",
        "adopted": "2015",
        "summary": (
            "General food labelling requirements for the UAE. Mandates Arabic on labels. "
            "References GSO CAC/GL 23 for claims and GSO 9 for nutrition labelling."
        ),
        "full_text_url": "https://www.esma.gov.ae/en-us/ESMAServices/Databank",
    },
}

_CLAIM_PROVISIONS: dict[str, list[dict]] = {
    "vitamin c": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "GSO CAC/GL 23 (adopted UAE): 'Source of Vitamin C' -- at least 15% RDI "
                "per 100g/100ml or serving. 'High in Vitamin C' -- at least 30% RDI. "
                "GCC RDI for Vitamin C: 75 mg/day. Arabic must be on label."
            ),
            "instrument": "GSO CAC/GL 23 + UAE.S 2055",
            "url": _GSO_URL,
            "last_updated": "2013",
        }
    ],
    "vitamin d": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "GSO CAC/GL 23: 'Source of Vitamin D' -- at least 15% RDI per 100g/100ml. "
                "GCC RDI for Vitamin D: 5 µg/day. "
                "Health claims linking Vitamin D to bone health subject to DM/ADAFSA review."
            ),
            "instrument": "GSO CAC/GL 23 + UAE.S GSO 9:2013",
            "url": _GSO_URL,
            "last_updated": "2013",
        }
    ],
    "calcium": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "GSO CAC/GL 23: 'Source of Calcium' -- at least 15% RDI per 100g/100ml. "
                "'High in Calcium' -- at least 30% RDI. GCC RDI for Calcium: 800 mg/day. "
                "Disease risk reduction claim for calcium/bone health is conditionally "
                "permitted under Codex-aligned GSO guidelines, subject to ESMA/DM approval."
            ),
            "instrument": "GSO CAC/GL 23 + UAE.S 2055",
            "url": _GSO_URL,
            "last_updated": "2013",
        }
    ],
    "dietary fibre": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "GSO CAC/GL 23: 'Source of Dietary Fibre' -- at least 3g/100g or 1.5g/100kcal. "
                "'High in Dietary Fibre' -- at least 6g/100g or 3g/100kcal. "
                "Conditions aligned with Codex thresholds."
            ),
            "instrument": "GSO CAC/GL 23",
            "url": _GSO_URL,
            "last_updated": "2013",
        }
    ],
    "omega-3": [
        {
            "claim_type": "nutrition_claim",
            "status": "conditional",
            "conditions": (
                "GSO CAC/GL 23 includes omega-3 nutrition claim conditions aligned with Codex. "
                "'Source of Omega-3' -- at least 0.3g ALA or 40mg EPA+DHA per 100g. "
                "Cardiovascular health claims require ESMA/DM approval. "
                "Check Dubai Municipality food safety circulars for latest guidance."
            ),
            "instrument": "GSO CAC/GL 23",
            "url": _DM_URL,
            "last_updated": "2013",
        }
    ],
}


class AEESMASource(RegulatorySource):
    """ESMA/DM data source for the UAE."""

    market = Market.AE
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
                    market=Market.AE,
                    ingredient=ingredient,
                    claim_type=p["claim_type"],
                    status=ClaimStatus(p["status"]),
                    conditions=p.get("conditions"),
                    basis=RegulatoryBasis(
                        instrument=p["instrument"],
                        url=p.get("url"),
                        notes="UAE adopts GCC/GSO standards aligned with Codex. Multiple authorities (ESMA, Dubai Municipality, ADAFSA) have jurisdiction depending on emirate.",
                    ),
                    last_updated=p.get("last_updated"),
                    source_url=p.get("url"),
                ))

        if not results:
            results.append(ClaimResult(
                market=Market.AE,
                ingredient=ingredient,
                claim_type=claim_type or "health_claim",
                status=ClaimStatus.NOT_DEFINED,
                conditions=(
                    f"No pre-indexed UAE claim data for '{ingredient}'. "
                    "UAE follows GCC/GSO standards (based on Codex CAC/GL 23). "
                    "Check ESMA databank (esma.gov.ae) or Dubai Municipality food safety portal. "
                    "Some ESMA standards require subscription access."
                ),
                basis=RegulatoryBasis(
                    instrument="GSO CAC/GL 23 + UAE.S 2055",
                    url=_BASE_URL,
                    notes="UAE adopts GCC standards via GSO. ESMA databank has UAE standards; some may require subscription.",
                ),
                source_url=_BASE_URL,
            ))

        return results

    async def get_standard(self, standard_id: str) -> Standard | None:
        upper = standard_id.upper()
        for key, data in _KNOWN_STANDARDS.items():
            if upper in key.upper() or key.upper() in upper:
                return Standard(standard_id=key, market=Market.AE, **data)
        return None

    async def search_standards(self, query: str) -> list[Standard]:
        q = query.lower()
        return [
            Standard(standard_id=k, market=Market.AE, **v)
            for k, v in _KNOWN_STANDARDS.items()
            if q in k.lower() or q in v["title"].lower() or q in (v.get("summary") or "").lower()
        ] or [Standard(standard_id=k, market=Market.AE, **v) for k, v in _KNOWN_STANDARDS.items()]

    async def get_market_overview(self) -> MarketOverview:
        return MarketOverview(
            market=Market.AE,
            authority_name="Emirates Authority for Standardisation and Metrology (ESMA) / Dubai Municipality / ADAFSA",
            authority_url=_BASE_URL,
            key_legislation=[
                "UAE.S 2055 -- General Food Labelling Requirements",
                "UAE.S GSO 9:2013 -- Nutrition Labelling",
                "GSO CAC/GL 23 -- GCC Guidelines for Nutrition and Health Claims",
                "UAE Federal Law No. 10/2015 on Food Safety",
            ],
            health_claims_framework=(
                "UAE regulates food claims through ESMA standards that adopt GCC/GSO guidelines, "
                "which are broadly aligned with Codex CAC/GL 23-1997. "
                "Nutrition claims ('source of', 'high in', 'low', 'free') must meet GSO 9:2013 thresholds. "
                "Health claims are subject to approval by the relevant emirate authority "
                "(Dubai Municipality for Dubai, ADAFSA for Abu Dhabi, ESMA federally). "
                "All food labels must include Arabic text. ESMA databank contains UAE standards "
                "but some require subscription access."
            ),
            notes=(
                f"Multiple authorities: ESMA (federal) | Dubai Municipality: {_DM_URL} | "
                f"ADAFSA (Abu Dhabi): {_ADAFSA_URL}"
            ),
        )
