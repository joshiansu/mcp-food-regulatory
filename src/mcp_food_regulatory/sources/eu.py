"""
European Union regulatory data source.

Two data access paths:
1. EUR-Lex SPARQL/REST API — for fetching regulation texts
   Endpoint: https://publications.europa.eu/webapi/rdf/sparql
2. EC Health Claims Register — downloadable Excel (publicly available)
   URL: https://food.ec.europa.eu/food-safety/labelling-and-nutrition/nutrition-and-health-claims/eu-register-health-claims_en

The health claims register is the most useful source for practical queries.
It lists every authorised and non-authorised claim with status, conditions,
and the relevant EFSA opinion.

We cache the register in memory on first fetch; it only updates when the
Commission adopts new decisions, so a 24h TTL is appropriate.
"""

from __future__ import annotations
import re
import httpx
from mcp_food_regulatory.models import (
    Market, ClaimResult, ClaimStatus, Standard, MarketOverview, RegulatoryBasis
)
from mcp_food_regulatory.sources.base import RegulatorySource

# EC Health Claims Register — Excel download (publicly available)
_HC_REGISTER_URL = (
    "https://food.ec.europa.eu/system/files/2024-04/"
    "reg-com_claims_authorised-list_en.xlsx"
)

# EUR-Lex SPARQL endpoint
_EURLEX_SPARQL = "https://publications.europa.eu/webapi/rdf/sparql"

# Key EU regulations relevant to food claims
_EU_KNOWN_STANDARDS: dict[str, dict] = {
    "EC 1924/2006": {
        "title": "Regulation (EC) No 1924/2006 on nutrition and health claims made on foods",
        "category": "regulation",
        "adopted": "2006",
        "last_amended": "2014",
        "summary": (
            "The primary EU framework governing nutrition claims (e.g. 'low fat', 'high fibre') "
            "and health claims (e.g. 'vitamin D supports bone health'). "
            "Article 13(1): Generic function claims — permitted if on the EU Register. "
            "Article 13(5): Individual applications for new function claims. "
            "Article 14: Risk reduction and children's development claims. "
            "Article 1(3): Permits trademark/brand names that reference a permitted claim "
            "('accompanying claim' mechanic) provided the labelling includes the qualifying claim."
        ),
        "full_text_url": "https://eur-lex.europa.eu/eli/reg/2006/1924/oj/eng",
        "key_definitions": {
            "Nutrition claim": "Any representation stating a food has particular nutritional properties.",
            "Health claim": "Any representation that a relationship exists between food/constituent and health.",
            "Article 13(1) claim": "Generic function claim — pre-approved, any operator may use.",
            "Article 14 claim": "Risk reduction or children's development claim — requires individual authorisation.",
        },
    },
    "EU 432/2012": {
        "title": "Commission Regulation (EU) No 432/2012 — list of permitted health claims",
        "category": "regulation",
        "adopted": "2012",
        "last_amended": "2022",
        "summary": (
            "Establishes the positive list of permitted health claims under Article 13(1) "
            "of Regulation (EC) No 1924/2006. Regularly updated with newly authorised claims."
        ),
        "full_text_url": "https://eur-lex.europa.eu/eli/reg/2012/432/oj",
    },
    "EC 178/2002": {
        "title": "Regulation (EC) No 178/2002 — General Food Law",
        "category": "regulation",
        "adopted": "2002",
        "last_amended": "2019",
        "summary": (
            "Lays down general principles and requirements of food law, establishes EFSA, "
            "and sets out procedures for food safety matters. Foundation of EU food law."
        ),
        "full_text_url": "https://eur-lex.europa.eu/eli/reg/2002/178/oj",
    },
}

# Seeded EU claim provisions for common queries
# Status values match the EC Register: "authorised", "non-authorised", "on hold"
_EU_CLAIM_PROVISIONS: dict[str, list[dict]] = {
    "caffeine": [
        {
            "claim_type": "health_claim",
            "status": "permitted",
            "conditions": (
                "Authorised Article 13(1) claim: 'Caffeine contributes to an increase in "
                "alertness and improves concentration.' "
                "Conditions: Only for foods providing ≥75mg caffeine per serving. "
                "Must include: 'The beneficial effect is obtained with a daily intake of "
                "75 mg of caffeine from all sources.' "
                "Not suitable for children, pregnant/breastfeeding women. "
                "EU Register ID: see EU 432/2012 Annex."
            ),
            "instrument": "EU 432/2012 + EC 1924/2006 Art.13(1)",
            "article": "Article 13(1)",
            "url": "https://food.ec.europa.eu/food-safety/labelling-and-nutrition/nutrition-and-health-claims/eu-register-health-claims_en",
            "last_updated": "2012",
        }
    ],
    "dietary fibre": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Nutrition claim 'source of fibre': ≥3g/100g or ≥1.5g/100kcal. "
                "Nutrition claim 'high fibre': ≥6g/100g or ≥3g/100kcal. "
                "Definition of dietary fibre in EU: carbohydrate polymers with ≥3 "
                "monomeric units, not digested/absorbed in the human small intestine. "
                "Analytical methods: AOAC 985.29, AOAC 991.43 or equivalent."
            ),
            "instrument": "EU 1169/2011 Annex I + EC 1924/2006 Annex",
            "url": "https://eur-lex.europa.eu/eli/reg/2011/1169/oj",
            "last_updated": "2011",
        }
    ],
    "inulin": [
        {
            "claim_type": "prebiotic",
            "status": "not_defined",
            "conditions": (
                "No specific authorised 'prebiotic' claim exists in the EU Health Claims Register. "
                "The term 'prebiotic' itself is not defined under EU food law. "
                "Inulin may be claimed as a dietary fibre (see fibre conditions above). "
                "Any functional/health claim about gut microbiota effects would require "
                "individual authorisation under Article 13(5) or remain prohibited "
                "as an unauthorised health claim under EC 1924/2006."
            ),
            "instrument": "EC 1924/2006",
            "url": "https://food.ec.europa.eu/food-safety/labelling-and-nutrition/nutrition-and-health-claims/eu-register-health-claims_en",
            "last_updated": "2024",
        },
        {
            "claim_type": "nutrition_claim_fibre",
            "status": "permitted",
            "conditions": (
                "Inulin (DP≥3) is analytically measurable as dietary fibre by AOAC 2009.01 "
                "and qualifies for EU fibre nutrition claims if quantity thresholds are met."
            ),
            "instrument": "EU 1169/2011 + EC 1924/2006 Annex",
            "url": "https://eur-lex.europa.eu/eli/reg/2011/1169/oj",
            "last_updated": "2011",
        },
    ],
    "vitamin d": [
        {
            "claim_type": "health_claim",
            "status": "permitted",
            "conditions": (
                "Multiple authorised Article 13(1) claims including: "
                "'Vitamin D contributes to the normal absorption/utilisation of calcium and phosphorus.' "
                "'Vitamin D contributes to normal blood calcium levels.' "
                "'Vitamin D contributes to the maintenance of normal bones.' "
                "'Vitamin D contributes to the maintenance of normal muscle function.' "
                "Conditions: Claim may be made only for food that is at least a source of "
                "vitamin D as per Annex to EC 1924/2006."
            ),
            "instrument": "EU 432/2012 + EC 1924/2006",
            "article": "Article 13(1)",
            "url": "https://food.ec.europa.eu/food-safety/labelling-and-nutrition/nutrition-and-health-claims/eu-register-health-claims_en",
            "last_updated": "2012",
        }
    ],
    "vitamin c": [
        {
            "claim_type": "health_claim",
            "status": "permitted",
            "conditions": (
                "Authorised claims include: 'Vitamin C contributes to normal collagen formation.' "
                "'Vitamin C contributes to the normal function of the immune system.' "
                "'Vitamin C contributes to the protection of cells from oxidative stress.' "
                "Minimum: food must be at least a 'source of vitamin C' (≥15% NRV per 100g/100ml/serving)."
            ),
            "instrument": "EU 432/2012",
            "article": "Article 13(1)",
            "url": "https://food.ec.europa.eu/food-safety/labelling-and-nutrition/nutrition-and-health-claims/eu-register-health-claims_en",
            "last_updated": "2012",
        }
    ],
}


class EUSource(RegulatorySource):
    market = Market.EU

    async def search_health_claims(
        self,
        ingredient: str,
        claim_type: str | None = None,
    ) -> list[ClaimResult]:
        """Search EU Health Claims Register for an ingredient."""
        ingredient_lower = ingredient.lower()
        results: list[ClaimResult] = []

        # Check seeded provisions first
        provisions = _EU_CLAIM_PROVISIONS.get(ingredient_lower, [])
        for p in provisions:
            if claim_type is None or claim_type.lower() in p["claim_type"].lower():
                results.append(ClaimResult(
                    market=Market.EU,
                    ingredient=ingredient,
                    claim_type=p["claim_type"],
                    status=ClaimStatus(p["status"]),
                    conditions=p.get("conditions"),
                    basis=RegulatoryBasis(
                        instrument=p["instrument"],
                        article=p.get("article"),
                        url=p.get("url"),
                    ),
                    efsa_opinion=p.get("efsa_opinion"),
                    last_updated=p.get("last_updated"),
                    source_url=p.get("url"),
                ))

        # If not in seed data, direct user to the live register
        if not results:
            results.append(ClaimResult(
                market=Market.EU,
                ingredient=ingredient,
                claim_type=claim_type or "health_claim",
                status=ClaimStatus.NOT_DEFINED,
                conditions=(
                    f"No pre-indexed EU claim data for '{ingredient}'. "
                    "Search the EU Health Claims Register directly or request a PR "
                    "to add this ingredient to the server's seed data."
                ),
                basis=RegulatoryBasis(
                    instrument="EC 1924/2006",
                    url="https://food.ec.europa.eu/food-safety/labelling-and-nutrition/"
                        "nutrition-and-health-claims/eu-register-health-claims_en",
                    notes="Live register available for download as Excel.",
                ),
                source_url=(
                    "https://food.ec.europa.eu/food-safety/labelling-and-nutrition/"
                    "nutrition-and-health-claims/eu-register-health-claims_en"
                ),
            ))

        return results

    async def get_standard(self, standard_id: str) -> Standard | None:
        """Return an EU regulation by identifier."""
        sid = re.sub(r"\s+", " ", standard_id.strip().upper())
        # Normalise common formats: "1924/2006" → "EC 1924/2006"
        if re.match(r"^\d{4}/\d{4}$", sid):
            sid = f"EC {sid}"

        data = _EU_KNOWN_STANDARDS.get(sid)
        if data:
            return Standard(standard_id=sid, market=Market.EU, **data)

        # Try EUR-Lex REST lookup for unknown IDs
        try:
            return await self._fetch_from_eurlex(standard_id)
        except Exception:
            return None

    async def _fetch_from_eurlex(self, standard_id: str) -> Standard | None:
        """
        Fetch regulation metadata from EUR-Lex.
        EUR-Lex provides a CELLAR SPARQL API and direct document URLs.
        """
        # Construct a EUR-Lex search URL for the regulation
        search_url = (
            f"https://eur-lex.europa.eu/search.html?text={standard_id}"
            "&scope=EURLEX&type=quick&lang=en"
        )
        try:
            resp = await self._get(search_url)
            resp.raise_for_status()
        except httpx.HTTPError:
            return None

        soup = __import__("bs4").BeautifulSoup(resp.text, "html.parser")
        result = soup.select_one(".SearchResult, .result-item, .EURLexResult")
        if not result:
            return None

        title_el = result.select_one("a.title, h2 a, .title")
        if not title_el:
            return None

        return Standard(
            standard_id=standard_id,
            market=Market.EU,
            title=title_el.get_text(strip=True),
            category="regulation",
            full_text_url=f"https://eur-lex.europa.eu{title_el.get('href', '')}",
        )

    async def search_standards(self, query: str) -> list[Standard]:
        """Search EU standards by keyword."""
        query_lower = query.lower()
        results = [
            Standard(standard_id=sid, market=Market.EU, **data)
            for sid, data in _EU_KNOWN_STANDARDS.items()
            if query_lower in data["title"].lower()
            or query_lower in data.get("summary", "").lower()
        ]
        return results

    async def get_market_overview(self) -> MarketOverview:
        return MarketOverview(
            market=Market.EU,
            authority_name="European Commission (DG SANTE) + European Food Safety Authority (EFSA)",
            authority_url="https://food.ec.europa.eu/",
            key_legislation=[
                "EC 1924/2006 — Nutrition and Health Claims Regulation",
                "EU 432/2012 — List of permitted health claims (Article 13 list)",
                "EU 1169/2011 — Food Information to Consumers (FIC)",
                "EC 178/2002 — General Food Law",
                "EU 2015/2283 — Novel Foods Regulation",
            ],
            health_claims_framework=(
                "Health claims require pre-authorisation. The EU Register lists all "
                "authorised (Art.13 & Art.14) and non-authorised claims. "
                "Art.13(1) generic function claims: any operator may use if on the Register. "
                "Art.13(5) individual applications: new scientific evidence required. "
                "Art.14 risk reduction/children claims: individual application to EFSA. "
                "Art.1(3): brand/trademark names that constitute or imply a claim must "
                "be accompanied by the corresponding permitted claim on the label."
            ),
            notes=(
                "Post-Brexit, Great Britain (GB) maintains a parallel claims register "
                "under the GB version of EC 1924/2006 retained in UK law, managed by FSA."
            ),
        )
