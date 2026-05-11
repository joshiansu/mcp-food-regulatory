"""
Abstract base class for regulatory data sources.

Every new market connector (codex.py, eu.py, ph_fda.py, etc.) must subclass
RegulatorySource and implement the abstract methods below.

This ensures a consistent interface across all sources so the MCP server
tools can call any source uniformly.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
import httpx
from mcp_food_regulatory.models import (
    Market, ClaimResult, Standard, AdditiveStatus, MarketOverview
)


class RegulatorySource(ABC):
    """
    Abstract base for a single market's regulatory data source.

    Subclasses wrap web scraping, API calls, or local data to expose
    a consistent interface the MCP server tools can call.
    """

    market: Market  # Must be set as a class attribute in subclasses

    def __init__(self, http_client: httpx.AsyncClient):
        self.client = http_client

    # ------------------------------------------------------------------ #
    #  Required interface — every source must implement these             #
    # ------------------------------------------------------------------ #

    @abstractmethod
    async def search_health_claims(
        self,
        ingredient: str,
        claim_type: str | None = None,
    ) -> list[ClaimResult]:
        """
        Search for health/nutrition claim status for an ingredient.

        Args:
            ingredient: Ingredient name, e.g. "caffeine", "inulin", "vitamin D"
            claim_type: Optional filter e.g. "health_claim", "nutrition_claim",
                        "prebiotic", "probiotic". None returns all types.

        Returns:
            List of ClaimResult objects. Empty list if no data found.
        """
        ...

    @abstractmethod
    async def get_standard(self, standard_id: str) -> Standard | None:
        """
        Retrieve a specific standard by its identifier.

        Args:
            standard_id: Official ID e.g. "CXG 2-1985", "EC 1924/2006"

        Returns:
            Standard object or None if not found.
        """
        ...

    @abstractmethod
    async def search_standards(self, query: str) -> list[Standard]:
        """
        Keyword search across this market's standards.

        Args:
            query: Free-text search string

        Returns:
            List of matching Standard objects (may be empty).
        """
        ...

    @abstractmethod
    async def get_market_overview(self) -> MarketOverview:
        """Return a high-level overview of this market's regulatory framework."""
        ...

    # ------------------------------------------------------------------ #
    #  Optional interface — implement if the market supports it          #
    # ------------------------------------------------------------------ #

    async def get_additive_status(
        self,
        additive: str,
        food_category: str,
    ) -> AdditiveStatus | None:
        """
        Check additive permission in a food category.
        Override in sources that support this (Codex, EU, FSANZ).
        Returns None if not supported or not found.
        """
        return None

    # ------------------------------------------------------------------ #
    #  Shared helpers                                                     #
    # ------------------------------------------------------------------ #

    async def _get(self, url: str, **kwargs) -> httpx.Response:
        """GET with a descriptive user-agent and timeout."""
        headers = kwargs.pop("headers", {})
        headers.setdefault(
            "User-Agent",
            "mcp-food-regulatory/0.1 (github.com/YOUR_USERNAME/mcp-food-regulatory; "
            "open-source MCP server for food regulatory data)"
        )
        return await self.client.get(url, headers=headers, timeout=15.0, **kwargs)
