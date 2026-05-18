"""
Pakistan -- Pakistan Food Authority (PFA) / Punjab Food Authority /
Pakistan Standards and Quality Control Authority (PSQCA).

Food regulation in Pakistan is fragmented across federal and provincial tiers:
  Federal: PSQCA sets national standards (PS standards); Pure Food Ordinance 1960
  Provincial: Punjab PFA (most active), Sindh Food Authority, KP Food Authority,
              Balochistan Food Authority each enforce locally.

Health claims regulated under provincial food acts and Pure Food Ordinance 1960.
Very limited structured online data; content primarily in Urdu.

Strategy: seed Pure Food Ordinance + PSQCA framework; direct to provincial PFA
portals for enforcement guidance.
"""

from __future__ import annotations
from mcp_food_regulatory.models import (
    Market, ClaimResult, ClaimStatus, Standard, MarketOverview, RegulatoryBasis
)
from mcp_food_regulatory.sources.base import RegulatorySource

_BASE_URL = "https://www.pfa.gop.pk"
_PSQCA_URL = "https://www.psqca.com.pk"
_KP_URL = "https://www.kpfoodauthority.gov.pk"

_KNOWN_STANDARDS: dict[str, dict] = {
    "Pure Food Ordinance 1960": {
        "title": "Pure Food Ordinance 1960 (W.P. Ordinance No. III of 1960)",
        "category": "legislation",
        "adopted": "1960",
        "last_amended": "2002",
        "summary": (
            "Federal framework legislation governing food safety and labelling in Pakistan. "
            "Prohibits adulteration and false/misleading representations on food labels. "
            "Governs nutrient and health claims indirectly through misbranding provisions. "
            "Enforcement delegated to provincial food authorities under 18th Amendment (2010)."
        ),
        "full_text_url": "https://www.psqca.com.pk",
    },
    "Punjab Food Authority Act 2011": {
        "title": "Punjab Food Authority Act 2011 (Punjab Act XIV of 2011)",
        "category": "provincial_legislation",
        "adopted": "2011",
        "last_amended": "2021",
        "summary": (
            "Establishes the Punjab Food Authority as the primary food regulator in Punjab. "
            "Governs labelling, quality, and health claims for food sold in Punjab. "
            "Punjab is Pakistan's most populous province and sets the de facto standard "
            "for food regulation across the country."
        ),
        "full_text_url": _BASE_URL,
    },
    "PS 3662": {
        "title": "PS 3662 -- Pakistan Standard for Food Labelling",
        "category": "national_standard",
        "adopted": "2004",
        "summary": (
            "PSQCA national standard for food labelling aligned with Codex STAN 1-1985. "
            "Sets requirements for mandatory label elements and nutrition labelling. "
            "Health claims must be truthful and not misleading per Codex CAC/GL 23 principles."
        ),
        "full_text_url": _PSQCA_URL,
    },
}

_CLAIM_PROVISIONS: dict[str, list[dict]] = {
    "vitamin c": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "PS 3662 / Codex-aligned: 'Source of Vitamin C' -- at least 15% RDI per "
                "100g/100ml or per serving. 'High in Vitamin C' -- at least 30% RDI. "
                "Pakistani RDI for Vitamin C: 40 mg/day (consistent with South Asian RDI). "
                "Claims must comply with Punjab PFA labelling regulations and not be misleading."
            ),
            "instrument": "PS 3662 + Pure Food Ordinance 1960",
            "url": _PSQCA_URL,
            "last_updated": "2004",
        }
    ],
    "vitamin d": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Codex-aligned (PS 3662): 'Source of Vitamin D' -- at least 15% RDI. "
                "RDI for Vitamin D: 5 µg/day. "
                "Health claims linking Vitamin D to bone health require substantiation "
                "under Punjab PFA or applicable provincial authority guidelines."
            ),
            "instrument": "PS 3662 + Punjab Food Authority Act 2011",
            "url": _BASE_URL,
            "last_updated": "2011",
        }
    ],
    "calcium": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Codex-aligned: 'Source of Calcium' -- at least 15% RDI per 100g/100ml. "
                "'High in Calcium' -- at least 30% RDI. RDI for Calcium: 800 mg/day. "
                "Disease risk reduction claims require scientific substantiation and are "
                "subject to PFA/PSQCA review; no general permitted list exists."
            ),
            "instrument": "PS 3662 + Pure Food Ordinance 1960",
            "url": _PSQCA_URL,
            "last_updated": "2004",
        }
    ],
    "dietary fibre": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Codex-aligned (PS 3662): 'Source of Dietary Fibre' -- at least 3g/100g "
                "or 1.5g/100kcal. 'High in Dietary Fibre' -- at least 6g/100g. "
                "Regulatory enforcement varies by province."
            ),
            "instrument": "PS 3662",
            "url": _PSQCA_URL,
            "last_updated": "2004",
        }
    ],
}


class PKPFASource(RegulatorySource):
    """PFA/PSQCA data source for Pakistan."""

    market = Market.PK
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
                    market=Market.PK,
                    ingredient=ingredient,
                    claim_type=p["claim_type"],
                    status=ClaimStatus(p["status"]),
                    conditions=p.get("conditions"),
                    basis=RegulatoryBasis(
                        instrument=p["instrument"],
                        url=p.get("url"),
                        notes="Pakistan's food regulation is fragmented: federal PSQCA standards and provincial enforcement (Punjab PFA most active). Claims follow Codex CAC/GL 23 principles.",
                    ),
                    last_updated=p.get("last_updated"),
                    source_url=p.get("url"),
                ))

        if not results:
            results.append(ClaimResult(
                market=Market.PK,
                ingredient=ingredient,
                claim_type=claim_type or "health_claim",
                status=ClaimStatus.NOT_DEFINED,
                conditions=(
                    f"No pre-indexed PFA/PSQCA claim data for '{ingredient}'. "
                    "Pakistan follows Codex CAC/GL 23 principles via PS 3662. "
                    "Check Punjab PFA portal (pfa.gop.pk) or PSQCA (psqca.com.pk) for guidance. "
                    "Provincial enforcement may vary."
                ),
                basis=RegulatoryBasis(
                    instrument="Pure Food Ordinance 1960 + PS 3662",
                    url=_PSQCA_URL,
                    notes="Very limited structured online data. Content primarily in Urdu.",
                ),
                source_url=_BASE_URL,
            ))

        return results

    async def get_standard(self, standard_id: str) -> Standard | None:
        upper = standard_id.upper()
        for key, data in _KNOWN_STANDARDS.items():
            if upper in key.upper() or key.upper() in upper:
                return Standard(standard_id=key, market=Market.PK, **data)
        return None

    async def search_standards(self, query: str) -> list[Standard]:
        q = query.lower()
        return [
            Standard(standard_id=k, market=Market.PK, **v)
            for k, v in _KNOWN_STANDARDS.items()
            if q in k.lower() or q in v["title"].lower() or q in (v.get("summary") or "").lower()
        ] or [Standard(standard_id=k, market=Market.PK, **v) for k, v in _KNOWN_STANDARDS.items()]

    async def get_market_overview(self) -> MarketOverview:
        return MarketOverview(
            market=Market.PK,
            authority_name="Pakistan Food Authority (PFA) / Punjab Food Authority / PSQCA",
            authority_url=_BASE_URL,
            key_legislation=[
                "Pure Food Ordinance 1960 (federal framework)",
                "Punjab Food Authority Act 2011 (Punjab)",
                "Sindh Pure Food Act 1958 (Sindh)",
                "KP Food Authority Act 2014 (Khyber Pakhtunkhwa)",
                "PS 3662 -- PSQCA Food Labelling Standard",
            ],
            health_claims_framework=(
                "Pakistan's food regulation is decentralised following the 18th Constitutional "
                "Amendment (2010), which devolved food safety to provinces. "
                "Federal PSQCA issues national standards (PS standards) aligned with Codex. "
                "Provincial food authorities (Punjab PFA is most active and widely referenced) "
                "enforce labelling and claims. Health claims must comply with Codex CAC/GL 23 "
                "principles -- truthful, not misleading, scientifically substantiated. "
                "No comprehensive national positive health claims list exists; "
                "claims are evaluated case-by-case by provincial authorities."
            ),
            notes=(
                f"Punjab PFA: {_BASE_URL} | PSQCA: {_PSQCA_URL} | "
                f"KP Food Authority: {_KP_URL}. "
                "Content primarily in Urdu. Very limited structured online data."
            ),
        )
