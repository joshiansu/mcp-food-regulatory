"""
China -- National Health Commission (NHC) / State Administration for Market
Regulation (SAMR).

Two pathways for health claims:
  1. Health Foods (保健食品) -- NMPA registration required, must use one of
     27 approved health function claims published by NHC.
  2. General Foods -- may use GB 28050-2011 (National Standard for Nutrition
     Labelling) nutrition claims only; health claims for general foods are
     heavily restricted.

Strategy:
  Seed all 27 NHC-approved health function claims + GB 28050-2011 nutrition
  claim thresholds. Data is primarily in Chinese; authoritative sources at
  NHC and SAMR portals.
"""

from __future__ import annotations
from mcp_food_regulatory.models import (
    Market, ClaimResult, ClaimStatus, Standard, MarketOverview, RegulatoryBasis,
    NutrientClaimThreshold,
)
from mcp_food_regulatory.sources.base import RegulatorySource

_BASE_URL = "https://www.nhc.gov.cn"
_SAMR_URL = "https://www.samr.gov.cn"
_NMPA_URL = "https://www.nmpa.gov.cn"
_GB_STANDARDS_URL = "https://std.samr.gov.cn"

_KNOWN_STANDARDS: dict[str, dict] = {
    "GB 28050-2011": {
        "title": "National Standard for Food Safety -- Nutrition Labelling of Prepackaged Foods",
        "category": "national_standard",
        "adopted": "2011",
        "summary": (
            "Mandatory standard governing nutrition labelling and nutrition claims for "
            "packaged foods in China. Defines 'source of' and 'high in' thresholds for "
            "energy, protein, fat, carbohydrates, dietary fibre, vitamins, and minerals. "
            "Permits a defined list of nutrition claims; health function claims for general "
            "foods are not covered."
        ),
        "full_text_url": "https://std.samr.gov.cn/gb/search/gbDetailed?id=71F772D81850D3A7E05397BE0A0AB82A",
    },
    "Decree 51 Health Food": {
        "title": "Administrative Measures for Health Food Registration and Filing (Decree No. 51)",
        "category": "regulation",
        "adopted": "2016",
        "last_amended": "2022",
        "summary": (
            "Governs registration and filing of health foods (保健食品) in China. "
            "Products must use only one of the 27 approved health function claims. "
            "Registration pathway for novel ingredients; filing pathway for products "
            "using approved vitamins/minerals list. Administered by NMPA."
        ),
        "full_text_url": "https://www.nmpa.gov.cn/yaowen/ypjgyw/20160216160001742.html",
    },
    "GB 16740-2014": {
        "title": "National Standard for Food Safety -- Health Food",
        "category": "national_standard",
        "adopted": "2014",
        "summary": (
            "General standards for health food products, covering quality requirements, "
            "labelling, and testing methods. Complements Decree 51 for health food "
            "products bearing NHC-approved function claims."
        ),
        "full_text_url": "https://std.samr.gov.cn/gb/search/gbDetailed?id=71F772D8385ED3A7E05397BE0A0AB82A",
    },
}

# 27 NHC-approved health function claims for health foods (保健食品)
# Official list published by NHC; all claims must appear exactly as worded
_NHC_27_FUNCTIONS = [
    "有助于增强免疫力",          # 1. Helps enhance immunity
    "有助于抗氧化",               # 2. Helps with antioxidant activity
    "辅助改善记忆",               # 3. Auxiliary improvement of memory
    "缓解视觉疲劳",               # 4. Relief of visual fatigue
    "清咽润喉",                   # 5. Clears the throat
    "有助于改善睡眠",             # 6. Helps improve sleep
    "缓解体力疲劳",               # 7. Relief of physical fatigue
    "耐缺氧",                     # 8. Hypoxia tolerance
    "有助于控制体内脂肪",         # 9. Helps control body fat
    "有助于改善骨密度",           # 10. Helps improve bone density
    "改善缺铁性贫血",             # 11. Improvement of iron-deficiency anemia
    "有助于改善痤疮",             # 12. Helps improve acne
    "有助于改善黄褐斑",           # 13. Helps improve chloasma
    "有助于改善皮肤水分状况",     # 14. Helps improve skin moisture
    "有助于调节肠道菌群",         # 15. Helps regulate intestinal flora
    "有助于消化",                 # 16. Helps digestion
    "有助于润肠通便",             # 17. Helps moisten intestines and relieve constipation
    "辅助保护胃黏膜",             # 18. Auxiliary protection of gastric mucosa
    "有助于维持血脂健康水平",     # 19. Helps maintain healthy blood lipid levels
    "有助于维持血糖健康水平",     # 20. Helps maintain healthy blood glucose levels
    "有助于维持血压健康水平",     # 21. Helps maintain healthy blood pressure levels
    "对化学性肝损伤有辅助保护功能",  # 22. Auxiliary protective function against chemical liver damage
    "对电离辐射危害有辅助保护功能",  # 23. Auxiliary protective function against ionising radiation
    "有助于排铅",                 # 24. Helps excrete lead
    "减少运动后疲劳感",           # 25. Reduces post-exercise fatigue
    "有助于提高运动耐力",         # 26. Helps improve exercise endurance
    "促进泌乳",                   # 27. Promotes lactation
]

_CLAIM_PROVISIONS: dict[str, list[dict]] = {
    "vitamin c": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "GB 28050-2011 nutrition claim: 'Contains Vitamin C' -- at least 15% NRV "
                "per 100g/100ml. 'High Vitamin C' -- at least 30% NRV per 100g/100ml. "
                "Chinese NRV for Vitamin C: 100 mg/day. "
                "For health foods: antioxidant function claim (#2 in NHC list) may be "
                "supported if Vitamin C is the active ingredient."
            ),
            "instrument": "GB 28050-2011",
            "url": _GB_STANDARDS_URL,
            "last_updated": "2011",
        }
    ],
    "vitamin d": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "GB 28050-2011: 'Contains Vitamin D' -- at least 15% NRV per 100g/100ml. "
                "Chinese NRV for Vitamin D: 10 µg/day. "
                "Health food bearing bone density claim (#10) may use Vitamin D as active."
            ),
            "instrument": "GB 28050-2011",
            "url": _GB_STANDARDS_URL,
            "last_updated": "2011",
        }
    ],
    "calcium": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "GB 28050-2011: 'Contains Calcium' -- at least 15% NRV per 100g/100ml. "
                "Chinese NRV for Calcium: 800 mg/day. "
                "Health food with bone density claim (#10 in NHC list) is common for "
                "calcium-containing products."
            ),
            "instrument": "GB 28050-2011 + NHC Health Food Function #10",
            "url": _GB_STANDARDS_URL,
            "last_updated": "2014",
        }
    ],
    "dietary fibre": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "GB 28050-2011: 'Contains Dietary Fibre' -- at least 3g/100g or 1.5g/100kcal. "
                "'High in Dietary Fibre' -- at least 6g/100g or 3g/100kcal. "
                "Chinese NRV for dietary fibre: 25g/day. "
                "Gut flora (#15) and digestion (#16) health food claims are available "
                "for qualifying prebiotic fibres under Decree 51."
            ),
            "instrument": "GB 28050-2011",
            "url": _GB_STANDARDS_URL,
            "last_updated": "2011",
        }
    ],
    "omega-3": [
        {
            "claim_type": "health_claim",
            "status": "conditional",
            "conditions": (
                "For general foods: GB 28050-2011 does not include omega-3 in the standard "
                "NRV list; claims about cardiovascular benefit are not permitted. "
                "For health foods registered under Decree 51: blood lipid (#19) or "
                "physical fatigue (#7) function claims may be relevant for EPA/DHA products. "
                "Must go through NMPA registration with clinical substantiation."
            ),
            "instrument": "Decree 51 + NHC Function List",
            "url": _NMPA_URL,
            "last_updated": "2022",
        }
    ],
}


# China nutrient content claim thresholds -- GB 28050-2011 National Standard for
# Nutrition Labelling of Prepackaged Foods, Section 5 (Nutrition Claims)
# Verified against GB 28050-2011 and NHC supplementary guidance (2013)
_CN_CLAIM_THRESHOLDS: list[dict] = [
    # --- Dietary fibre ---
    {"nutrient": "dietary fibre", "claim_type": "source_of", "claim_wording": "含有膳食纤维 (Contains dietary fibre)",
     "threshold_value": "≥3g/100g (solid) or ≥1.5g/100ml (liquid) or ≥3g/serving",
     "threshold_basis": "per 100g, per 100ml, or per serving",
     "governing_instrument": "GB 28050-2011, Appendix C Table C.1", "verified_date": "2024-01"},
    {"nutrient": "dietary fibre", "claim_type": "high_in", "claim_wording": "高膳食纤维 / 富含膳食纤维 (High/rich in dietary fibre)",
     "threshold_value": "≥6g/100g (solid) or ≥3g/100ml (liquid) or ≥6g/serving",
     "threshold_basis": "per 100g, per 100ml, or per serving",
     "governing_instrument": "GB 28050-2011, Appendix C Table C.1", "verified_date": "2024-01"},
    # --- Protein ---
    {"nutrient": "protein", "claim_type": "source_of", "claim_wording": "含有蛋白质 / 蛋白质来源 (Source of protein)",
     "threshold_value": "≥10g/100g (solid) or ≥5g/100ml (liquid) or ≥5g/serving",
     "threshold_basis": "per 100g, per 100ml, or per serving",
     "governing_instrument": "GB 28050-2011, Appendix C Table C.1", "verified_date": "2024-01"},
    {"nutrient": "protein", "claim_type": "high_in", "claim_wording": "高蛋白质 / 富含蛋白质 (High/rich in protein)",
     "threshold_value": "≥20g/100g (solid) or ≥10g/100ml (liquid) or ≥10g/serving",
     "threshold_basis": "per 100g, per 100ml, or per serving",
     "governing_instrument": "GB 28050-2011, Appendix C Table C.1", "verified_date": "2024-01"},
    # --- Fat ---
    {"nutrient": "fat", "claim_type": "low", "claim_wording": "低脂肪 (Low fat)",
     "threshold_value": "≤3g/100g (solid) or ≤1.5g/100ml (liquid)",
     "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "GB 28050-2011, Appendix C Table C.1", "verified_date": "2024-01"},
    {"nutrient": "fat", "claim_type": "free", "claim_wording": "无脂肪 (Fat free)",
     "threshold_value": "≤0.5g/100g or ≤0.5g/100ml", "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "GB 28050-2011, Appendix C Table C.1", "verified_date": "2024-01"},
    {"nutrient": "fat", "claim_type": "reduced", "claim_wording": "减少脂肪 (Reduced fat)",
     "threshold_value": "≥25% less fat than reference food", "threshold_basis": "compared to reference",
     "governing_instrument": "GB 28050-2011, Appendix C Table C.1", "verified_date": "2024-01"},
    # --- Saturated fat ---
    {"nutrient": "saturated fat", "claim_type": "low", "claim_wording": "低饱和脂肪 (Low saturated fat)",
     "threshold_value": "≤1.5g/100g (solid) or ≤0.75g/100ml (liquid)",
     "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "GB 28050-2011, Appendix C Table C.1", "verified_date": "2024-01"},
    {"nutrient": "saturated fat", "claim_type": "free", "claim_wording": "无饱和脂肪 (Saturated fat free)",
     "threshold_value": "≤0.1g/100g or ≤0.1g/100ml", "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "GB 28050-2011, Appendix C Table C.1", "verified_date": "2024-01"},
    # --- Sugars ---
    {"nutrient": "sugars", "claim_type": "low", "claim_wording": "低糖 (Low sugar)",
     "threshold_value": "≤5g/100g (solid) or ≤2.5g/100ml (liquid)",
     "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "GB 28050-2011, Appendix C Table C.1", "verified_date": "2024-01"},
    {"nutrient": "sugars", "claim_type": "free", "claim_wording": "无糖 (Sugar free)",
     "threshold_value": "≤0.5g/100g or ≤0.5g/100ml", "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "GB 28050-2011, Appendix C Table C.1", "verified_date": "2024-01"},
    # --- Sodium ---
    {"nutrient": "sodium", "claim_type": "low", "claim_wording": "低钠 (Low sodium)",
     "threshold_value": "≤120mg/100g or ≤60mg/100ml", "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "GB 28050-2011, Appendix C Table C.1", "verified_date": "2024-01"},
    {"nutrient": "sodium", "claim_type": "free", "claim_wording": "无钠 (Sodium free)",
     "threshold_value": "≤5mg/100g or ≤5mg/100ml", "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "GB 28050-2011, Appendix C Table C.1", "verified_date": "2024-01"},
    {"nutrient": "sodium", "claim_type": "reduced", "claim_wording": "减少钠 (Reduced sodium)",
     "threshold_value": "≥25% less sodium than reference food", "threshold_basis": "compared to reference",
     "governing_instrument": "GB 28050-2011, Appendix C Table C.1", "verified_date": "2024-01"},
    # --- Energy ---
    {"nutrient": "energy", "claim_type": "low", "claim_wording": "低能量 (Low energy / Low calorie)",
     "threshold_value": "≤40kcal/100g (solid) or ≤20kcal/100ml (liquid)",
     "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "GB 28050-2011, Appendix C Table C.1", "verified_date": "2024-01"},
    {"nutrient": "energy", "claim_type": "free", "claim_wording": "无能量 (Energy free / Calorie free)",
     "threshold_value": "≤17kJ/100g or ≤17kJ/100ml (approx ≤4kcal)", "threshold_basis": "per 100g or per 100ml",
     "governing_instrument": "GB 28050-2011, Appendix C Table C.1", "verified_date": "2024-01"},
    {"nutrient": "energy", "claim_type": "reduced", "claim_wording": "减少能量 (Reduced energy)",
     "threshold_value": "≥25% less energy than reference food", "threshold_basis": "compared to reference",
     "governing_instrument": "GB 28050-2011, Appendix C Table C.1", "verified_date": "2024-01"},
]


class CNNHCSource(RegulatorySource):
    """NHC/SAMR data source for China."""

    market = Market.CN
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
                    market=Market.CN,
                    ingredient=ingredient,
                    claim_type=p["claim_type"],
                    status=ClaimStatus(p["status"]),
                    conditions=p.get("conditions"),
                    basis=RegulatoryBasis(
                        instrument=p["instrument"],
                        url=p.get("url"),
                        notes="China uses two pathways: general food nutrition claims (GB 28050-2011) and health food function claims (27 NHC-approved functions, Decree 51).",
                    ),
                    last_updated=p.get("last_updated"),
                    source_url=p.get("url"),
                ))

        if not results:
            results.append(ClaimResult(
                market=Market.CN,
                ingredient=ingredient,
                claim_type=claim_type or "health_claim",
                status=ClaimStatus.NOT_DEFINED,
                conditions=(
                    f"No pre-indexed CN claim data for '{ingredient}'. "
                    "For general foods, refer to GB 28050-2011 for permitted nutrition claims. "
                    "For health foods, consult the 27 NHC-approved function claims and "
                    "NMPA registration portal (spjs.nmpa.gov.cn). "
                    "Note: sources are primarily in Chinese."
                ),
                basis=RegulatoryBasis(
                    instrument="GB 28050-2011 / Decree 51",
                    url=_GB_STANDARDS_URL,
                    notes="27 NHC function claims available for health foods only; NMPA registration required.",
                ),
                source_url=_NMPA_URL,
            ))

        return results

    async def get_standard(self, standard_id: str) -> Standard | None:
        upper = standard_id.upper()
        for key, data in _KNOWN_STANDARDS.items():
            if upper in key.upper() or key.upper() in upper:
                return Standard(standard_id=key, market=Market.CN, **data)
        return None

    async def search_standards(self, query: str) -> list[Standard]:
        q = query.lower()
        return [
            Standard(standard_id=k, market=Market.CN, **v)
            for k, v in _KNOWN_STANDARDS.items()
            if q in k.lower() or q in v["title"].lower() or q in (v.get("summary") or "").lower()
        ] or [Standard(standard_id=k, market=Market.CN, **v) for k, v in _KNOWN_STANDARDS.items()]

    async def get_nutrient_claim_thresholds(
        self,
        nutrient: str | None = None,
    ) -> list[NutrientClaimThreshold]:
        """Return China nutrient content claim thresholds from GB 28050-2011."""
        results = []
        for t in _CN_CLAIM_THRESHOLDS:
            if nutrient is None or nutrient.lower() in t["nutrient"].lower():
                results.append(NutrientClaimThreshold(
                    market=Market.CN,
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
            market=Market.CN,
            authority_name="National Health Commission (NHC) / State Administration for Market Regulation (SAMR) / NMPA",
            authority_url=_BASE_URL,
            key_legislation=[
                "GB 28050-2011 -- Nutrition Labelling of Prepackaged Foods",
                "Administrative Measures for Health Food Registration and Filing (Decree 51, 2016)",
                "GB 16740-2014 -- Health Food National Standard",
                "Food Safety Law of the People's Republic of China (2021 revision)",
            ],
            health_claims_framework=(
                "China distinguishes between general foods and health foods (保健食品). "
                "General foods may only use nutrition claims defined in GB 28050-2011 "
                "(e.g. 'source of', 'high in'). Health function claims are reserved for "
                "registered health food products. "
                "NHC publishes a list of 27 approved health function claims; products may "
                "only claim one function per product. Registration with NMPA is mandatory. "
                "Ingredients must come from the approved catalogue unless novel ingredient "
                "approval is obtained. Most content is in Chinese."
            ),
            notes=(
                f"The 27 approved health function claims cover: immunity, antioxidant, "
                f"memory, vision, throat, sleep, fatigue, hypoxia, body fat, bone density, "
                f"anaemia, acne, skin, gut flora, digestion, bowel, gastric mucosa, "
                f"blood lipids, blood glucose, blood pressure, liver, radiation, lead excretion, "
                f"exercise fatigue, exercise endurance, and lactation. "
                f"NMPA portal: {_NMPA_URL}"
            ),
        )
