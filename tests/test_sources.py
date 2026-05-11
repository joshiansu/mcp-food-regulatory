"""
Tests for mcp-food-regulatory sources.

Run with: uv run pytest tests/ -v
"""

import pytest
import pytest_asyncio
import httpx
from unittest.mock import AsyncMock, patch

from mcp_food_regulatory.models import Market, ClaimStatus
from mcp_food_regulatory.sources.codex import CodexSource
from mcp_food_regulatory.sources.eu import EUSource


@pytest.fixture
def http_client():
    return httpx.AsyncClient()


@pytest.fixture
def codex(http_client):
    return CodexSource(http_client)


@pytest.fixture
def eu(http_client):
    return EUSource(http_client)


# ------------------------------------------------------------------ #
#  Codex tests                                                        #
# ------------------------------------------------------------------ #

class TestCodexSource:

    @pytest.mark.asyncio
    async def test_market_is_codex(self, codex):
        assert codex.market == Market.CODEX

    @pytest.mark.asyncio
    async def test_search_caffeine_returns_results(self, codex):
        results = await codex.search_health_claims("caffeine")
        assert isinstance(results, list)
        # Seeded data should return at least one result
        assert len(results) >= 1
        assert results[0].market == Market.CODEX
        assert results[0].ingredient == "caffeine"

    @pytest.mark.asyncio
    async def test_search_dietary_fibre_permitted(self, codex):
        results = await codex.search_health_claims("dietary fibre")
        assert any(r.status == ClaimStatus.PERMITTED for r in results)

    @pytest.mark.asyncio
    async def test_search_inulin_fibre_claim(self, codex):
        results = await codex.search_health_claims("inulin")
        assert len(results) >= 1
        # Inulin should have a dietary_fibre claim type
        claim_types = [r.claim_type for r in results]
        assert any("fibre" in ct or "dietary" in ct for ct in claim_types)

    @pytest.mark.asyncio
    async def test_get_standard_cxg2(self, codex):
        standard = await codex.get_standard("CXG 2-1985")
        assert standard is not None
        assert standard.market == Market.CODEX
        assert "Nutrition Labelling" in standard.title
        assert standard.key_definitions is not None
        assert "Dietary fibre" in standard.key_definitions

    @pytest.mark.asyncio
    async def test_get_standard_cxg23(self, codex):
        standard = await codex.get_standard("CXG 23-1997")
        assert standard is not None
        assert "Health Claims" in standard.title or "Nutrition" in standard.title

    @pytest.mark.asyncio
    async def test_get_standard_unknown_returns_none_or_standard(self, codex):
        # Unknown standard should return None (not raise)
        result = await codex.get_standard("CXX 999-9999")
        # May return None or a live result — both are valid
        assert result is None or result.standard_id is not None

    @pytest.mark.asyncio
    async def test_search_standards_dietary_fibre(self, codex):
        results = await codex.search_standards("dietary fibre")
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_market_overview(self, codex):
        overview = await codex.get_market_overview()
        assert overview.market == Market.CODEX
        assert "FAO" in overview.authority_name or "Codex" in overview.authority_name
        assert len(overview.key_legislation) >= 1

    @pytest.mark.asyncio
    async def test_unknown_ingredient_no_crash(self, codex):
        # Should not raise — returns empty or fallback
        results = await codex.search_health_claims("xylobiose_fictional_ingredient_xyz")
        assert isinstance(results, list)


# ------------------------------------------------------------------ #
#  EU tests                                                           #
# ------------------------------------------------------------------ #

class TestEUSource:

    @pytest.mark.asyncio
    async def test_market_is_eu(self, eu):
        assert eu.market == Market.EU

    @pytest.mark.asyncio
    async def test_search_caffeine_permitted(self, eu):
        results = await eu.search_health_claims("caffeine")
        assert len(results) >= 1
        assert any(r.status == ClaimStatus.PERMITTED for r in results)
        # Should reference Article 13(1)
        assert any("13" in (r.basis.article or "") for r in results if r.basis)

    @pytest.mark.asyncio
    async def test_search_inulin_prebiotic_not_defined(self, eu):
        results = await eu.search_health_claims("inulin", claim_type="prebiotic")
        prebiotic_results = [r for r in results if "prebiotic" in r.claim_type]
        assert len(prebiotic_results) >= 1
        assert any(r.status == ClaimStatus.NOT_DEFINED for r in prebiotic_results)

    @pytest.mark.asyncio
    async def test_search_inulin_fibre_permitted(self, eu):
        results = await eu.search_health_claims("inulin")
        fibre_results = [r for r in results if "fibre" in r.claim_type or "fibre" in (r.conditions or "").lower()]
        assert len(fibre_results) >= 1

    @pytest.mark.asyncio
    async def test_get_standard_ec1924(self, eu):
        standard = await eu.get_standard("EC 1924/2006")
        assert standard is not None
        assert "1924" in standard.title
        assert standard.key_definitions is not None

    @pytest.mark.asyncio
    async def test_get_standard_normalises_id(self, eu):
        # "1924/2006" without "EC" prefix should still work
        standard = await eu.get_standard("1924/2006")
        assert standard is not None

    @pytest.mark.asyncio
    async def test_search_standards_health_claims(self, eu):
        results = await eu.search_standards("health claims")
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_market_overview(self, eu):
        overview = await eu.get_market_overview()
        assert overview.market == Market.EU
        assert "EFSA" in overview.authority_name or "Commission" in overview.authority_name
        assert any("1924" in leg for leg in overview.key_legislation)

    @pytest.mark.asyncio
    async def test_vitamin_d_claims(self, eu):
        results = await eu.search_health_claims("vitamin d")
        assert len(results) >= 1
        assert any(r.status == ClaimStatus.PERMITTED for r in results)

    @pytest.mark.asyncio
    async def test_unknown_ingredient_fallback(self, eu):
        results = await eu.search_health_claims("xylobiose_fictional_xyz")
        assert isinstance(results, list)
        assert len(results) >= 1  # Should return a "not found" guidance result
        assert results[0].status == ClaimStatus.NOT_DEFINED


# ------------------------------------------------------------------ #
#  Server tool tests (integration-style)                             #
# ------------------------------------------------------------------ #

class TestServerTools:
    """Test the MCP tool functions directly."""

    @pytest.mark.asyncio
    async def test_compare_markets_caffeine(self):
        from mcp_food_regulatory.server import compare_markets
        result = await compare_markets(
            ingredient="caffeine",
            claim_type="health_claim",
            markets=["eu", "codex"],
        )
        assert "comparison" in result
        assert "summary" in result
        assert len(result["comparison"]) >= 1

    @pytest.mark.asyncio
    async def test_list_markets(self):
        from mcp_food_regulatory.server import list_markets
        result = await list_markets()
        assert "implemented" in result
        assert "eu" in result["implemented"]
        assert "codex" in result["implemented"]
        assert "planned_contributions_welcome" in result

    @pytest.mark.asyncio
    async def test_get_standard_codex(self):
        from mcp_food_regulatory.server import get_standard
        result = await get_standard("CXG 2-1985", "codex")
        assert result.get("found") is True
        assert "Nutrition" in result["title"]

    @pytest.mark.asyncio
    async def test_unknown_market_returns_error(self):
        from mcp_food_regulatory.server import get_market_overview
        result = await get_market_overview("mars")
        assert "error" in result
