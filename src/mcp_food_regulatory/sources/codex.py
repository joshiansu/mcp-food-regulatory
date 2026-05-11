"""
Codex Alimentarius data source.

Wraps the FAO/WHO Codex website:
  - Standards list:  https://www.fao.org/fao-who-codexalimentarius/codex-texts/list-standards/en/
  - Standards search: https://www.fao.org/fao-who-codexalimentarius/search/en/
  - Food additives DB: https://www.fao.org/food/food-safety-quality/scientific-advice/jecfa/jecfa-food-additives/en/

Codex doesn't have a public JSON API, so we use structured HTML parsing.
Results are TTL-cached to avoid hammering the FAO servers.
"""

from __future__ import annotations
import re
from urllib.parse import urlencode
import httpx
from bs4 import BeautifulSoup
from mcp_food_regulatory.models import (
    Market, ClaimResult, ClaimStatus, Standard, MarketOverview, RegulatoryBasis
)
from mcp_food_regulatory.sources.base import RegulatorySource

# Codex standard categories we care about for food/nutrition claims
_NUTRITION_KEYWORDS = {
    "dietary fibre", "fibre", "fiber", "health claim", "nutrition claim",
    "prebiotic", "probiotic", "vitamin", "mineral", "protein", "fat",
    "energy", "carbohydrate", "sugar", "salt", "sodium", "caffeine",
    "fortification", "supplement", "food additive", "contaminant",
}

# Known Codex standards relevant to health/nutrition claims — seeded for
# get_standard() fast-path without a network round-trip.
_KNOWN_STANDARDS: dict[str, dict] = {
    "CXG 2-1985": {
        "title": "Guidelines on Nutrition Labelling",
        "category": "guideline",
        "adopted": "1985",
        "last_amended": "2021",
        "summary": (
            "Establishes principles for nutrition labelling including the definition "
            "of dietary fibre. The 2021 revision incorporated AOAC 2022.01 method "
            "recognition and updated the dietary fibre definition to include "
            "non-digestible carbohydrates with DP≥3."
        ),
        "full_text_url": "https://www.fao.org/fao-who-codexalimentarius/sh-proxy/en/?lnk=1&url=https%3A%2F%2Fworkspace.fao.org%2Fsites%2Fcodex%2FStandards%2FCXG%202-1985%2FCXG_002e.pdf",
        "key_definitions": {
            "Dietary fibre": (
                "Carbohydrate polymers with ten or more monomeric units, which are not "
                "hydrolysed by the endogenous enzymes in the small intestine of humans "
                "and belong to the following categories: (a) edible carbohydrate polymers "
                "naturally occurring in the food as consumed; (b) carbohydrate polymers "
                "obtained from food raw material by physical, enzymatic or chemical means; "
                "(c) synthetic carbohydrate polymers."
            )
        },
    },
    "CXG 23-1997": {
        "title": "Guidelines for Use of Nutrition and Health Claims",
        "category": "guideline",
        "adopted": "1997",
        "last_amended": "2013",
        "summary": (
            "Defines conditions under which nutrition claims (e.g. 'low fat', 'high fibre') "
            "and health claims may be made. Distinguishes nutrient function claims, "
            "other function claims, and reduction of disease risk claims."
        ),
        "full_text_url": "https://www.fao.org/fao-who-codexalimentarius/sh-proxy/en/?lnk=1&url=https%3A%2F%2Fworkspace.fao.org%2Fsites%2Fcodex%2FStandards%2FCXG%2023-1997%2FCXG_023e.pdf",
        "key_definitions": {
            "Nutrition claim": "Any representation which states, suggests or implies that a food has particular nutritional properties.",
            "Health claim": "Any representation that states, suggests, or implies that a relationship exists between a food or a constituent of that food and health.",
            "Nutrient function claim": "A nutrition claim that describes the physiological role of the nutrient in growth, development and normal functions of the body.",
        },
    },
    "GSFA": {
        "title": "General Standard for Food Additives (GSFA)",
        "category": "standard",
        "adopted": "1995",
        "last_amended": "2023",
        "summary": (
            "Establishes conditions under which approved food additives may be used "
            "in all foods. Includes maximum use levels by food category and INS numbers."
        ),
        "full_text_url": "https://www.fao.org/gsfaonline/index.html",
    },
}


class CodexSource(RegulatorySource):
    market = Market.CODEX

    BASE_URL = "https://www.fao.org/fao-who-codexalimentarius"
    STANDARDS_URL = f"{BASE_URL}/codex-texts/list-standards/en/"
    SEARCH_URL = f"{BASE_URL}/search/en/"

    async def search_health_claims(
        self,
        ingredient: str,
        claim_type: str | None = None,
    ) -> list[ClaimResult]:
        """
        Search Codex guidelines for claim provisions relating to the ingredient.

        Codex doesn't have a structured claims register like the EU, so this
        searches guideline text and returns structured results based on known
        provisions + live search fallback.
        """
        ingredient_lower = ingredient.lower()
        results: list[ClaimResult] = []

        # Known provisions seeded directly — avoids network for common queries
        known = _CODEX_CLAIM_PROVISIONS.get(ingredient_lower)
        if known:
            for provision in known:
                if claim_type is None or claim_type.lower() in provision["claim_type"].lower():
                    results.append(ClaimResult(
                        market=Market.CODEX,
                        ingredient=ingredient,
                        claim_type=provision["claim_type"],
                        status=ClaimStatus(provision["status"]),
                        conditions=provision.get("conditions"),
                        basis=RegulatoryBasis(
                            instrument=provision["instrument"],
                            article=provision.get("article"),
                            url=provision.get("url"),
                        ),
                        last_updated=provision.get("last_updated"),
                        source_url=provision.get("url"),
                    ))

        # Live search fallback for ingredients not in the seed data
        if not results:
            try:
                live_results = await self._live_search_claims(ingredient, claim_type)
                results.extend(live_results)
            except Exception:
                pass  # Network failures shouldn't crash the tool

        return results

    async def _live_search_claims(
        self,
        ingredient: str,
        claim_type: str | None,
    ) -> list[ClaimResult]:
        """Hit the Codex search endpoint and parse results."""
        params = {"q": f"{ingredient} health claim nutrition claim", "lang": "en"}
        url = f"{self.SEARCH_URL}?{urlencode(params)}"
        try:
            resp = await self._get(url)
            resp.raise_for_status()
        except httpx.HTTPError:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []

        # Codex search returns result cards — extract titles + links
        for card in soup.select(".search-result, .result-item, article")[:5]:
            title_el = card.select_one("h2, h3, .title, a")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            link = title_el.get("href", "") if title_el.name == "a" else ""
            if link and not link.startswith("http"):
                link = f"https://www.fao.org{link}"

            # Only include results plausibly related to claims
            if not any(kw in title.lower() for kw in ["guideline", "claim", "nutrition", "label"]):
                continue

            results.append(ClaimResult(
                market=Market.CODEX,
                ingredient=ingredient,
                claim_type=claim_type or "general",
                status=ClaimStatus.NOT_DEFINED,
                conditions="See Codex text for specific provisions.",
                basis=RegulatoryBasis(
                    instrument=title,
                    url=link or None,
                    notes="Retrieved via Codex search — verify against primary text.",
                ),
                source_url=link or self.STANDARDS_URL,
            ))

        return results

    async def get_standard(self, standard_id: str) -> Standard | None:
        """Return a Codex standard by ID. Uses seed data for known standards."""
        # Normalise — strip extra spaces, uppercase
        sid = re.sub(r"\s+", " ", standard_id.strip().upper())

        # Fast path: seeded data
        data = _KNOWN_STANDARDS.get(sid)
        if data:
            return Standard(
                standard_id=sid,
                market=Market.CODEX,
                **data,
            )

        # Slow path: try fetching from Codex standards list
        try:
            return await self._fetch_standard_from_web(sid)
        except Exception:
            return None

    async def _fetch_standard_from_web(self, standard_id: str) -> Standard | None:
        """Attempt to find a standard on the Codex website."""
        resp = await self._get(self.STANDARDS_URL)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Codex standards list is a table — find row matching the ID
        for row in soup.select("table tr"):
            cells = row.find_all("td")
            if not cells:
                continue
            row_text = " ".join(c.get_text(strip=True) for c in cells)
            if standard_id.replace(" ", "").upper() in row_text.replace(" ", "").upper():
                link = row.find("a")
                url = link["href"] if link else None
                if url and not url.startswith("http"):
                    url = f"https://www.fao.org{url}"
                title_cell = cells[1] if len(cells) > 1 else cells[0]
                return Standard(
                    standard_id=standard_id,
                    market=Market.CODEX,
                    title=title_cell.get_text(strip=True),
                    category="standard",
                    full_text_url=url,
                )
        return None

    async def search_standards(self, query: str) -> list[Standard]:
        """Search Codex standards by keyword."""
        # First check seeded data
        query_lower = query.lower()
        seeded = [
            Standard(standard_id=sid, market=Market.CODEX, **data)
            for sid, data in _KNOWN_STANDARDS.items()
            if query_lower in data["title"].lower()
            or query_lower in data.get("summary", "").lower()
        ]
        if seeded:
            return seeded

        # Live search
        try:
            params = {"q": query, "lang": "en", "type": "standards"}
            resp = await self._get(f"{self.SEARCH_URL}?{urlencode(params)}")
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            results = []
            for card in soup.select(".search-result, article")[:8]:
                title_el = card.select_one("h2, h3, .title, a")
                if not title_el:
                    continue
                link_el = card.select_one("a")
                url = link_el["href"] if link_el else ""
                if url and not url.startswith("http"):
                    url = f"https://www.fao.org{url}"
                results.append(Standard(
                    standard_id="",  # Can't reliably extract from search page
                    market=Market.CODEX,
                    title=title_el.get_text(strip=True),
                    full_text_url=url or None,
                ))
            return results
        except Exception:
            return []

    async def get_market_overview(self) -> MarketOverview:
        return MarketOverview(
            market=Market.CODEX,
            authority_name="Codex Alimentarius Commission (CAC) — Joint FAO/WHO Food Standards Programme",
            authority_url="https://www.fao.org/fao-who-codexalimentarius/en/",
            key_legislation=[
                "CXG 2-1985 — Guidelines on Nutrition Labelling",
                "CXG 23-1997 — Guidelines for Use of Nutrition and Health Claims",
                "GSFA — General Standard for Food Additives",
                "CXS 192-1995 — General Standard for Contaminants",
            ],
            health_claims_framework=(
                "Codex provides non-binding international reference standards. "
                "CXG 23-1997 sets conditions for nutrition and health claims. "
                "Member states may adopt Codex standards into national law. "
                "Health claims are categorised as: nutrient function claims, "
                "other function claims, and reduction of disease risk claims."
            ),
            notes=(
                "Codex standards are reference points, not enforceable law unless "
                "incorporated by a member state. WTO/SPS Agreement uses Codex as "
                "the international benchmark for food safety measures."
            ),
        )


# ------------------------------------------------------------------ #
#  Seeded claim provisions for common queries                        #
#  Extend this dict as more provisions are researched               #
# ------------------------------------------------------------------ #
_CODEX_CLAIM_PROVISIONS: dict[str, list[dict]] = {
    "caffeine": [
        {
            "claim_type": "general guidance",
            "status": "not_defined",
            "conditions": (
                "Codex does not have a specific health claim provision for caffeine. "
                "Refer to national frameworks. CXG 23-1997 general principles apply."
            ),
            "instrument": "CXG 23-1997",
            "article": "Section 3",
            "url": "https://www.fao.org/fao-who-codexalimentarius/sh-proxy/en/?lnk=1&url=https%3A%2F%2Fworkspace.fao.org%2Fsites%2Fcodex%2FStandards%2FCXG%2023-1997%2FCXG_023e.pdf",
            "last_updated": "2013",
        }
    ],
    "dietary fibre": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "A food may bear a claim 'source of fibre' if it contains at least 3g/100g "
                "or 1.5g/100kcal. 'High fibre' requires at least 6g/100g or 3g/100kcal. "
                "Dietary fibre is defined per CXG 2-1985 (2021 revision): carbohydrate "
                "polymers with DP≥3 not hydrolysed by endogenous small intestine enzymes."
            ),
            "instrument": "CXG 2-1985",
            "article": "Section 3 & Annex",
            "url": "https://www.fao.org/fao-who-codexalimentarius/sh-proxy/en/?lnk=1&url=https%3A%2F%2Fworkspace.fao.org%2Fsites%2Fcodex%2FStandards%2FCXG%202-1985%2FCXG_002e.pdf",
            "last_updated": "2021",
        }
    ],
    "inulin": [
        {
            "claim_type": "dietary_fibre",
            "status": "permitted",
            "conditions": (
                "Inulin (DP≥3) qualifies as dietary fibre under CXG 2-1985 (2021) "
                "if analytically verified by AOAC 2009.01 or AOAC 2022.01. "
                "No specific prebiotic claim provision exists in Codex — "
                "prebiotic claims fall under 'other function claims' in CXG 23-1997 "
                "and require substantiation."
            ),
            "instrument": "CXG 2-1985 + CXG 23-1997",
            "url": "https://www.fao.org/fao-who-codexalimentarius/sh-proxy/en/?lnk=1&url=https%3A%2F%2Fworkspace.fao.org%2Fsites%2Fcodex%2FStandards%2FCXG%202-1985%2FCXG_002e.pdf",
            "last_updated": "2021",
        }
    ],
    "vitamin d": [
        {
            "claim_type": "nutrient_function_claim",
            "status": "permitted",
            "conditions": (
                "Vitamin D nutrient function claims are permitted under CXG 23-1997. "
                "Example: 'Vitamin D contributes to normal bone development.' "
                "Must meet minimum quantity thresholds for 'source of' claims."
            ),
            "instrument": "CXG 23-1997",
            "article": "Section 5",
            "url": "https://www.fao.org/fao-who-codexalimentarius/sh-proxy/en/?lnk=1&url=https%3A%2F%2Fworkspace.fao.org%2Fsites%2Fcodex%2FStandards%2FCXG%2023-1997%2FCXG_023e.pdf",
            "last_updated": "2013",
        }
    ],
}
