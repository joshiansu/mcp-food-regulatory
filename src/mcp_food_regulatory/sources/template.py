"""
Placeholder template for future market connectors.

Copy this file, rename it (e.g. ph_fda.py, my_moh.py), and implement
each method. See codex.py and eu.py for reference implementations.

CONTRIBUTING: Each ASEAN market is a separate file implementing RegulatorySource.
This is the highest-value contribution area — see README.md for details.

Markets still needed:
  - ph_fda.py    → Philippines FDA  (pfda.doh.gov.ph)
  - my_moh.py    → Malaysia MOH / MySMERT
  - vn_moh.py    → Vietnam MOH (QCVN standards)
  - id_bpom.py   → Indonesia BPOM
  - th_fda.py    → Thailand FDA
  - au_fsanz.py  → Australia/NZ FSANZ Food Standards Code
  - gb_fsa.py    → Great Britain FSA (post-Brexit)
"""

from __future__ import annotations
from mcp_food_regulatory.models import (
    Market, ClaimResult, Standard, MarketOverview
)
from mcp_food_regulatory.sources.base import RegulatorySource


class TemplateSource(RegulatorySource):
    """
    Template — copy and rename this class for your market.

    Steps:
    1. Set `market` to the correct Market enum value
    2. Set `BASE_URL` to the primary regulatory authority website
    3. Implement `search_health_claims` — find the claims register or search page
    4. Implement `get_standard` — find the standards/legislation library
    5. Implement `search_standards` — keyword search across standards
    6. Implement `get_market_overview` — fill in the authority details
    7. Register in server.py: add to SOURCES dict
    8. Add market to the README table
    9. Add test cases in tests/test_sources.py
    """

    market = Market.PH  # 👈 Change this

    BASE_URL = "https://pfda.doh.gov.ph"  # 👈 Change this

    async def search_health_claims(
        self,
        ingredient: str,
        claim_type: str | None = None,
    ) -> list[ClaimResult]:
        """TODO: implement health claim search for this market."""
        raise NotImplementedError(
            f"search_health_claims not yet implemented for {self.market}. "
            "See CONTRIBUTING.md to add this market."
        )

    async def get_standard(self, standard_id: str) -> Standard | None:
        """TODO: implement standard lookup for this market."""
        raise NotImplementedError(
            f"get_standard not yet implemented for {self.market}."
        )

    async def search_standards(self, query: str) -> list[Standard]:
        """TODO: implement standards search for this market."""
        raise NotImplementedError(
            f"search_standards not yet implemented for {self.market}."
        )

    async def get_market_overview(self) -> MarketOverview:
        """TODO: fill in authority details for this market."""
        return MarketOverview(
            market=self.market,
            authority_name="TODO: fill in authority name",
            authority_url=self.BASE_URL,
            key_legislation=["TODO: list key legislation"],
            health_claims_framework="TODO: describe how health claims work in this market",
        )
