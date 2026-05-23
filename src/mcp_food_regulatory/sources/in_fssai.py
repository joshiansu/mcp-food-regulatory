"""
India -- Food Safety and Standards Authority of India (FSSAI).

Key regulations:
  FSS (Advertising and Claims) Regulations 2018 -- Schedule I & II list
  permitted nutrition and health claims. No structured online database;
  the authoritative text is a PDF gazette notification.

Strategy:
  Seed Schedule I (nutrition claims) and Schedule II (health claims) provisions
  for common ingredients. Direct users to FSSAI website for full text.
"""

from __future__ import annotations
from mcp_food_regulatory.models import (
    Market, ClaimResult, ClaimStatus, Standard, MarketOverview, RegulatoryBasis,
    NutrientClaimThreshold,
)
from mcp_food_regulatory.sources.base import RegulatorySource

_BASE_URL = "https://www.fssai.gov.in"
_CLAIMS_REG_URL = (
    "https://www.fssai.gov.in/upload/uploadfiles/files/Regulations/English/"
    "FSSAI_Notf_Regu_Claims_31_08_2018.pdf"
)

_KNOWN_STANDARDS: dict[str, dict] = {
    "FSS Claims 2018": {
        "title": "Food Safety and Standards (Advertising and Claims) Regulations 2018",
        "category": "regulation",
        "adopted": "2018",
        "summary": (
            "Primary regulation governing nutrition and health claims on food labels in India. "
            "Schedule I lists permitted nutrition claims with conditions. "
            "Schedule II lists permitted health claims. "
            "Prohibits misleading claims and sets requirements for substantiation."
        ),
        "full_text_url": _CLAIMS_REG_URL,
    },
    "FSS Act 2006": {
        "title": "Food Safety and Standards Act 2006",
        "category": "legislation",
        "adopted": "2006",
        "last_amended": "2020",
        "summary": (
            "Foundational legislation establishing FSSAI and the framework for food safety "
            "regulation in India. Empowers FSSAI to issue regulations on labelling, "
            "additives, contaminants, and advertising."
        ),
        "full_text_url": "https://www.fssai.gov.in/upload/uploadfiles/files/FSS_Act2006.pdf",
    },
    "FSS Labelling 2020": {
        "title": "Food Safety and Standards (Labelling and Display) Regulations 2020",
        "category": "regulation",
        "adopted": "2020",
        "summary": (
            "Governs mandatory label declarations, font sizes, and display requirements "
            "for packaged foods sold in India. Complements the Claims Regulations 2018."
        ),
        "full_text_url": "https://www.fssai.gov.in/upload/uploadfiles/files/Regulations/English/FSSAI_Reg_Labelling_05_03_2020.pdf",
    },
}

# Seeded provisions from FSS Claims Regulations 2018 Schedule I & II
_CLAIM_PROVISIONS: dict[str, list[dict]] = {
    "vitamin c": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Schedule I nutrition claim: 'Source of Vitamin C' -- product must contain "
                "at least 15% NRV per 100g/100ml or per serving. "
                "'High in Vitamin C' -- at least 30% NRV per 100g/100ml or per serving. "
                "NRV for Vitamin C: 40 mg/day (Indian standard)."
            ),
            "instrument": "FSS Claims 2018 Schedule I",
            "url": _CLAIMS_REG_URL,
            "last_updated": "2018",
        }
    ],
    "vitamin d": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Schedule I: 'Source of Vitamin D' -- at least 15% NRV per 100g/100ml or serving. "
                "'High in Vitamin D' -- at least 30% NRV per 100g/100ml or serving. "
                "NRV for Vitamin D: 5 µg/day."
            ),
            "instrument": "FSS Claims 2018 Schedule I",
            "url": _CLAIMS_REG_URL,
            "last_updated": "2018",
        }
    ],
    "calcium": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Schedule I: 'Source of Calcium' -- at least 15% NRV per 100g/100ml. "
                "'High in Calcium' -- at least 30% NRV. NRV for Calcium: 600 mg/day. "
                "Schedule II health claim: Calcium contributes to normal development and "
                "maintenance of healthy bones and teeth (with qualifying conditions)."
            ),
            "instrument": "FSS Claims 2018 Schedule I & II",
            "url": _CLAIMS_REG_URL,
            "last_updated": "2018",
        }
    ],
    "dietary fibre": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Schedule I: 'Source of Fibre' -- at least 3g/100g or 1.5g/100kcal. "
                "'High in Fibre' -- at least 6g/100g or 3g/100kcal. "
                "Dietary fibre definition per FSSAI: non-digestible carbohydrate polymers "
                "with three or more monomeric units."
            ),
            "instrument": "FSS Claims 2018 Schedule I",
            "url": _CLAIMS_REG_URL,
            "last_updated": "2018",
        }
    ],
    "omega-3": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Schedule I: 'Source of Omega-3 fatty acids' -- at least 0.3g ALA per 100g "
                "or at least 40mg EPA+DHA per 100g. "
                "'High in Omega-3' -- double the source threshold. "
                "Claims about heart health benefits require pre-approval under Schedule II."
            ),
            "instrument": "FSS Claims 2018 Schedule I",
            "url": _CLAIMS_REG_URL,
            "last_updated": "2018",
        }
    ],
}


# India nutrient content claim thresholds -- FSSAI (Advertising and Claims) Regulations 2018
# Schedule I (nutrition claims) + FSS (Labelling and Display) Regulations 2020, Annexure A
# Verified against FSSAI gazette notifications (2018, 2020)
_IN_CLAIM_THRESHOLDS: list[dict] = [
    # --- Dietary fibre ---
    {"nutrient": "dietary fibre", "claim_type": "source_of", "claim_wording": "Good source of fibre / Contains fibre",
     "threshold_value": "≥3g/100g (solid) or ≥1.5g/100ml (liquid) or ≥3g/serving",
     "threshold_basis": "per 100g, per 100ml, or per serving",
     "governing_instrument": "FSSAI Claims Regulations 2018 Schedule I", "verified_date": "2024-01"},
    {"nutrient": "dietary fibre", "claim_type": "high_in", "claim_wording": "High in fibre",
     "threshold_value": "≥6g/100g (solid) or ≥3g/100ml (liquid) or ≥6g/serving",
     "threshold_basis": "per 100g, per 100ml, or per serving",
     "governing_instrument": "FSSAI Claims Regulations 2018 Schedule I", "verified_date": "2024-01"},
    # --- Protein ---
    {"nutrient": "protein", "claim_type": "source_of", "claim_wording": "Good source of protein",
     "threshold_value": "≥10g/100g (solid) or ≥5g/100ml (liquid)",
     "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "FSSAI Claims Regulations 2018 Schedule I", "verified_date": "2024-01"},
    {"nutrient": "protein", "claim_type": "high_in", "claim_wording": "High in protein",
     "threshold_value": "≥20g/100g (solid) or ≥10g/100ml (liquid)",
     "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "FSSAI Claims Regulations 2018 Schedule I", "verified_date": "2024-01"},
    # --- Fat ---
    {"nutrient": "fat", "claim_type": "low", "claim_wording": "Low fat",
     "threshold_value": "≤3g/100g (solid) or ≤1.5g/100ml (liquid)",
     "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "FSSAI Claims Regulations 2018 Schedule I", "verified_date": "2024-01"},
    {"nutrient": "fat", "claim_type": "free", "claim_wording": "Fat free",
     "threshold_value": "≤0.5g/100g or ≤0.5g/100ml", "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "FSSAI Claims Regulations 2018 Schedule I", "verified_date": "2024-01"},
    {"nutrient": "fat", "claim_type": "reduced", "claim_wording": "Reduced fat",
     "threshold_value": "≥25% less fat than comparable product", "threshold_basis": "compared to reference",
     "governing_instrument": "FSSAI Claims Regulations 2018 Schedule I", "verified_date": "2024-01"},
    # --- Saturated fat ---
    {"nutrient": "saturated fat", "claim_type": "low", "claim_wording": "Low saturated fat",
     "threshold_value": "≤1.5g/100g (solid) or ≤0.75g/100ml (liquid)",
     "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "FSSAI Claims Regulations 2018 Schedule I", "verified_date": "2024-01"},
    {"nutrient": "saturated fat", "claim_type": "free", "claim_wording": "Saturated fat free",
     "threshold_value": "≤0.1g/100g or ≤0.1g/100ml", "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "FSSAI Claims Regulations 2018 Schedule I", "verified_date": "2024-01"},
    # --- Sugars ---
    {"nutrient": "sugars", "claim_type": "low", "claim_wording": "Low sugar",
     "threshold_value": "≤5g/100g (solid) or ≤2.5g/100ml (liquid)",
     "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "FSSAI Claims Regulations 2018 Schedule I", "verified_date": "2024-01"},
    {"nutrient": "sugars", "claim_type": "free", "claim_wording": "Sugar free",
     "threshold_value": "≤0.5g/100g or ≤0.5g/100ml", "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "FSSAI Claims Regulations 2018 Schedule I", "verified_date": "2024-01"},
    {"nutrient": "sugars", "claim_type": "no_added", "claim_wording": "No added sugar",
     "threshold_value": "No added sugars including honey, syrups, malt extract, or fruit concentrates",
     "threshold_basis": "n/a",
     "governing_instrument": "FSSAI Claims Regulations 2018 Schedule I", "verified_date": "2024-01"},
    # --- Sodium ---
    {"nutrient": "sodium", "claim_type": "low", "claim_wording": "Low sodium",
     "threshold_value": "≤120mg/100g", "threshold_basis": "per 100g",
     "governing_instrument": "FSSAI Claims Regulations 2018 Schedule I", "verified_date": "2024-01"},
    {"nutrient": "sodium", "claim_type": "free", "claim_wording": "Sodium free / Salt free",
     "threshold_value": "≤5mg/100g", "threshold_basis": "per 100g",
     "governing_instrument": "FSSAI Claims Regulations 2018 Schedule I", "verified_date": "2024-01"},
    {"nutrient": "sodium", "claim_type": "reduced", "claim_wording": "Reduced sodium",
     "threshold_value": "≥25% less sodium than comparable product", "threshold_basis": "compared to reference",
     "governing_instrument": "FSSAI Claims Regulations 2018 Schedule I", "verified_date": "2024-01"},
    # --- Energy ---
    {"nutrient": "energy", "claim_type": "low", "claim_wording": "Low energy / Low calorie",
     "threshold_value": "≤40kcal/100g (solid) or ≤20kcal/100ml (liquid)",
     "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "FSSAI Claims Regulations 2018 Schedule I", "verified_date": "2024-01"},
    {"nutrient": "energy", "claim_type": "free", "claim_wording": "Energy free / Calorie free",
     "threshold_value": "≤4kcal/100ml (liquids only)", "threshold_basis": "per 100ml",
     "governing_instrument": "FSSAI Claims Regulations 2018 Schedule I", "verified_date": "2024-01"},
    {"nutrient": "energy", "claim_type": "reduced", "claim_wording": "Reduced energy",
     "threshold_value": "≥25% less energy than comparable product", "threshold_basis": "compared to reference",
     "governing_instrument": "FSSAI Claims Regulations 2018 Schedule I", "verified_date": "2024-01"},
    # --- Vitamins and minerals ---
    {"nutrient": "vitamins_minerals", "claim_type": "source_of",
     "claim_wording": "Source of / Good source of [vitamin/mineral]",
     "threshold_value": "≥15% RDA per 100g or per serving", "threshold_basis": "per 100g or per serving",
     "reference_value": "RDA per ICMR-NIN 2020 Dietary Reference Values",
     "governing_instrument": "FSSAI Claims Regulations 2018 Schedule I", "verified_date": "2024-01"},
    {"nutrient": "vitamins_minerals", "claim_type": "high_in",
     "claim_wording": "High in [vitamin/mineral] / Rich in [vitamin/mineral]",
     "threshold_value": "≥30% RDA per 100g or per serving", "threshold_basis": "per 100g or per serving",
     "reference_value": "RDA per ICMR-NIN 2020 Dietary Reference Values",
     "governing_instrument": "FSSAI Claims Regulations 2018 Schedule I", "verified_date": "2024-01"},
]


class INFSSAISource(RegulatorySource):
    """FSSAI data source for India."""

    market = Market.IN
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
                    market=Market.IN,
                    ingredient=ingredient,
                    claim_type=p["claim_type"],
                    status=ClaimStatus(p["status"]),
                    conditions=p.get("conditions"),
                    basis=RegulatoryBasis(
                        instrument=p["instrument"],
                        url=p.get("url"),
                        notes="FSS Claims Regulations 2018 -- Schedule I (nutrition) and Schedule II (health).",
                    ),
                    last_updated=p.get("last_updated"),
                    source_url=p.get("url"),
                ))

        if not results:
            results.append(ClaimResult(
                market=Market.IN,
                ingredient=ingredient,
                claim_type=claim_type or "health_claim",
                status=ClaimStatus.NOT_DEFINED,
                conditions=(
                    f"No pre-indexed FSSAI claim data for '{ingredient}'. "
                    "Refer to FSS (Advertising and Claims) Regulations 2018 Schedule I & II, "
                    "or the FSSAI website for circulars and amendments."
                ),
                basis=RegulatoryBasis(
                    instrument="FSS Claims 2018",
                    url=_CLAIMS_REG_URL,
                    notes="No structured online database; full text available as PDF gazette.",
                ),
                source_url=_BASE_URL,
            ))

        return results

    async def get_standard(self, standard_id: str) -> Standard | None:
        upper = standard_id.upper()
        for key, data in _KNOWN_STANDARDS.items():
            if upper in key.upper() or key.upper() in upper:
                return Standard(standard_id=key, market=Market.IN, **data)
        return None

    async def search_standards(self, query: str) -> list[Standard]:
        q = query.lower()
        return [
            Standard(standard_id=k, market=Market.IN, **v)
            for k, v in _KNOWN_STANDARDS.items()
            if q in k.lower() or q in v["title"].lower() or q in (v.get("summary") or "").lower()
        ] or [Standard(standard_id=k, market=Market.IN, **v) for k, v in _KNOWN_STANDARDS.items()]

    async def get_nutrient_claim_thresholds(
        self,
        nutrient: str | None = None,
    ) -> list[NutrientClaimThreshold]:
        """Return India nutrient content claim thresholds from FSSAI Claims Regulations 2018."""
        results = []
        for t in _IN_CLAIM_THRESHOLDS:
            if nutrient is None or nutrient.lower() in t["nutrient"].lower():
                results.append(NutrientClaimThreshold(
                    market=Market.IN,
                    nutrient=t["nutrient"],
                    claim_type=t["claim_type"],
                    claim_wording=t["claim_wording"],
                    threshold_value=t["threshold_value"],
                    threshold_basis=t["threshold_basis"],
                    reference_value=t.get("reference_value"),
                    conditions=t.get("conditions"),
                    governing_instrument=t["governing_instrument"],
                    data_confidence="seeded",
                    verified_date=t.get("verified_date"),
                ))
        return results

    async def get_market_overview(self) -> MarketOverview:
        return MarketOverview(
            market=Market.IN,
            authority_name="Food Safety and Standards Authority of India (FSSAI)",
            authority_url=_BASE_URL,
            key_legislation=[
                "Food Safety and Standards Act 2006",
                "FSS (Advertising and Claims) Regulations 2018",
                "FSS (Labelling and Display) Regulations 2020",
                "FSS (Food Products Standards and Food Additives) Regulations 2011",
            ],
            health_claims_framework=(
                "Health and nutrition claims in India are governed by the FSS (Advertising "
                "and Claims) Regulations 2018. Schedule I lists permitted nutrition claims "
                "(e.g. 'source of', 'high in') with threshold conditions. Schedule II lists "
                "permitted health claims linking diet to health outcomes. "
                "No general pre-market approval is required for Schedule I/II claims if "
                "conditions are met. Novel claims not in Schedule I/II require FSSAI approval. "
                "Claims must not be misleading, and traditional medicine references are restricted."
            ),
            notes=(
                "FSSAI publishes circulars and guidance on its website. "
                "egazette.gov.in is the authoritative source for gazette notifications."
            ),
        )
