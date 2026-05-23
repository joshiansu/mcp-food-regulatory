"""
Tests for mcp-food-regulatory sources.

Run with: uv run pytest tests/ -v
"""

import pytest
import pytest_asyncio
import httpx
from unittest.mock import AsyncMock, patch

from mcp_food_regulatory.models import Market, ClaimStatus, NutrientClaimThreshold, RegulatoryUpdate
from mcp_food_regulatory.sources.codex import CodexSource
from mcp_food_regulatory.sources.eu import EUSource
from mcp_food_regulatory.sources.ph_fda import PhFDASource
from mcp_food_regulatory.sources.jp_caa import JPCAASource
from mcp_food_regulatory.sources.us_fda import USFDASource
from mcp_food_regulatory.sources.ca_health_canada import CAHealthCanadaSource
from mcp_food_regulatory.sources.au_fsanz import AUFSANZSource
from mcp_food_regulatory.sources.in_fssai import INFSSAISource
from mcp_food_regulatory.sources.cn_nhc import CNNHCSource
from mcp_food_regulatory.sources.kr_mfds import KRMFDSSource
from mcp_food_regulatory.sources.br_anvisa import BRANVISASource
from mcp_food_regulatory.sources.co_invima import COINVIMASource
from mcp_food_regulatory.sources.cl_minsal import CLMINSALSource
from mcp_food_regulatory.sources.mx_cofepris import MXCOFEPRISSource
from mcp_food_regulatory.sources.ae_esma import AEESMASource
from mcp_food_regulatory.sources.sa_sfda import SASFDASource
from mcp_food_regulatory.sources.za_doh import ZADoHSource
from mcp_food_regulatory.sources.pk_pfa import PKPFASource
from mcp_food_regulatory.sources.bd_bfsa import BDBFSASource
from mcp_food_regulatory.sources.lk_fcau import LKFCAUSource
from mcp_food_regulatory.sources.np_dftqc import NPDFTQCSource
from mcp_food_regulatory.sources.bt_bfdra import BTBFDRASource
from mcp_food_regulatory.sources.mv_mfda import MVMFDASource


@pytest.fixture
def http_client():
    return httpx.AsyncClient()


@pytest.fixture
def codex(http_client):
    return CodexSource(http_client)


@pytest.fixture
def eu(http_client):
    return EUSource(http_client)


@pytest.fixture
def ph(http_client):
    return PhFDASource(http_client)


@pytest.fixture
def jp(http_client):
    return JPCAASource(http_client)


@pytest.fixture
def us(http_client):
    return USFDASource(http_client)


@pytest.fixture
def ca(http_client):
    return CAHealthCanadaSource(http_client)


@pytest.fixture
def au(http_client):
    return AUFSANZSource(http_client)


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


# ------------------------------------------------------------------ #
#  Nutrient claim threshold tests (P2)                               #
# ------------------------------------------------------------------ #

class TestNutrientClaimThresholds:
    """Tests for get_nutrient_claim_thresholds and compare_nutrient_claim_thresholds."""

    # --- Model shape ---

    def test_nutrient_claim_threshold_model_fields(self):
        t = NutrientClaimThreshold(
            market=Market.EU,
            nutrient="dietary fibre",
            claim_type="source_of",
            claim_wording="Source of fibre",
            threshold_value="≥3g/100g",
            threshold_basis="per 100g",
            governing_instrument="EC 1924/2006 Annex",
        )
        assert t.data_confidence == "seeded"
        assert t.verified_date is None
        assert t.market == Market.EU

    def test_claim_result_has_confidence_fields(self):
        from mcp_food_regulatory.models import ClaimResult
        r = ClaimResult(
            market=Market.EU,
            ingredient="caffeine",
            claim_type="health_claim",
            status=ClaimStatus.PERMITTED,
        )
        assert r.data_confidence == "seeded"
        assert r.staleness_warning is True
        assert r.verified_date is None

    def test_standard_has_confidence_fields(self):
        from mcp_food_regulatory.models import Standard
        s = Standard(
            standard_id="EC 1924/2006",
            market=Market.EU,
            title="Test",
        )
        assert s.data_confidence == "seeded"
        assert s.staleness_warning is True

    # --- EU source ---

    @pytest.mark.asyncio
    async def test_eu_thresholds_all_nutrients(self, eu):
        results = await eu.get_nutrient_claim_thresholds()
        assert len(results) >= 10
        assert all(isinstance(t, NutrientClaimThreshold) for t in results)
        assert all(t.market == Market.EU for t in results)

    @pytest.mark.asyncio
    async def test_eu_thresholds_fibre_filter(self, eu):
        results = await eu.get_nutrient_claim_thresholds("dietary fibre")
        assert len(results) >= 2
        assert all("fibre" in t.nutrient.lower() for t in results)
        claim_types = {t.claim_type for t in results}
        assert "source_of" in claim_types
        assert "high_in" in claim_types

    @pytest.mark.asyncio
    async def test_eu_thresholds_protein_filter(self, eu):
        results = await eu.get_nutrient_claim_thresholds("protein")
        assert len(results) >= 2
        assert all("protein" in t.nutrient.lower() for t in results)
        assert any("20%" in t.threshold_value for t in results)

    @pytest.mark.asyncio
    async def test_eu_thresholds_have_governing_instrument(self, eu):
        results = await eu.get_nutrient_claim_thresholds()
        assert all(t.governing_instrument for t in results)
        assert all("1924/2006" in t.governing_instrument for t in results)

    @pytest.mark.asyncio
    async def test_eu_thresholds_no_match_returns_empty(self, eu):
        results = await eu.get_nutrient_claim_thresholds("xylobiose_fictional_xyz")
        assert results == []

    # --- US source ---

    @pytest.mark.asyncio
    async def test_us_thresholds_all_nutrients(self, us):
        results = await us.get_nutrient_claim_thresholds()
        assert len(results) >= 10
        assert all(isinstance(t, NutrientClaimThreshold) for t in results)
        assert all(t.market == Market.US for t in results)

    @pytest.mark.asyncio
    async def test_us_thresholds_fibre_filter(self, us):
        results = await us.get_nutrient_claim_thresholds("dietary fibre")
        assert len(results) >= 2
        claim_types = {t.claim_type for t in results}
        assert "source_of" in claim_types
        assert "high_in" in claim_types

    @pytest.mark.asyncio
    async def test_us_thresholds_sodium_filter(self, us):
        results = await us.get_nutrient_claim_thresholds("sodium")
        assert len(results) >= 3
        assert any("140mg" in t.threshold_value for t in results)

    @pytest.mark.asyncio
    async def test_us_thresholds_have_cfr_instrument(self, us):
        results = await us.get_nutrient_claim_thresholds()
        assert all("21 CFR" in t.governing_instrument for t in results)

    # --- Base class default ---

    @pytest.mark.asyncio
    async def test_base_class_returns_empty_list(self, eu):
        from mcp_food_regulatory.sources.base import RegulatorySource
        # Base implementation (not overridden) should return []
        # We test via a market without override -- use parent directly
        result = await RegulatorySource.get_nutrient_claim_thresholds(eu, "protein")
        assert result == []

    # --- Server tools ---

    @pytest.mark.asyncio
    async def test_server_get_nutrient_claim_thresholds_eu(self):
        from mcp_food_regulatory.server import get_nutrient_claim_thresholds
        result = await get_nutrient_claim_thresholds(["eu"])
        assert "results" in result
        assert "eu" in result["results"]
        assert len(result["results"]["eu"]) >= 10
        assert result["errors"] is None

    @pytest.mark.asyncio
    async def test_server_get_nutrient_claim_thresholds_us(self):
        from mcp_food_regulatory.server import get_nutrient_claim_thresholds
        result = await get_nutrient_claim_thresholds(["us"], nutrient="dietary fibre")
        assert "results" in result
        assert "us" in result["results"]
        assert len(result["results"]["us"]) >= 2

    @pytest.mark.asyncio
    async def test_server_get_nutrient_claim_thresholds_unknown_market(self):
        from mcp_food_regulatory.server import get_nutrient_claim_thresholds
        result = await get_nutrient_claim_thresholds(["mars"])
        assert result["errors"] is not None
        assert "mars" in result["errors"]

    @pytest.mark.asyncio
    async def test_server_compare_nutrient_claim_thresholds_eu_us(self):
        from mcp_food_regulatory.server import compare_nutrient_claim_thresholds
        result = await compare_nutrient_claim_thresholds("dietary fibre", ["eu", "us"])
        assert "per_market" in result
        assert "eu" in result["per_market"]
        assert "us" in result["per_market"]
        assert "comparison_table" in result
        assert len(result["comparison_table"]) >= 2
        assert result["errors"] is None

    @pytest.mark.asyncio
    async def test_server_compare_nutrient_claim_thresholds_unimplemented_market(self):
        from mcp_food_regulatory.server import compare_nutrient_claim_thresholds
        # PH has no threshold data -- should return empty list, not error
        result = await compare_nutrient_claim_thresholds("protein", ["eu", "ph"])
        assert "eu" in result["per_market"]
        assert len(result["per_market"]["eu"]) >= 2
        # PH returns empty list -- not an error
        assert result["per_market"].get("ph") == [] or "ph" not in result["per_market"]

    @pytest.mark.asyncio
    async def test_server_compare_summary_shows_markets_with_data(self):
        from mcp_food_regulatory.server import compare_nutrient_claim_thresholds
        result = await compare_nutrient_claim_thresholds("sodium", ["eu", "us"])
        assert "EU" in result["summary"] or "US" in result["summary"]


# ------------------------------------------------------------------ #
#  Regulatory updates tests (P3)                                      #
# ------------------------------------------------------------------ #

class TestRegulatoryUpdates:
    """Tests for get_regulatory_updates tool and RegulatoryUpdate model."""

    # --- Model ---

    def test_regulatory_update_model_fields(self):
        u = RegulatoryUpdate(
            market=Market.US,
            change_type="new_legislation",
            summary="Sesame added as 9th major allergen",
            effective_date="2023-01-01",
            instrument="FASTER Act 2021",
        )
        assert u.data_confidence == "seeded"
        assert u.market == Market.US

    # --- Seed data correctness ---

    @pytest.mark.asyncio
    async def test_us_sesame_mandate_present(self, us):
        updates = await us.get_regulatory_updates()
        summaries = " ".join(u.summary for u in updates).lower()
        assert "sesame" in summaries

    @pytest.mark.asyncio
    async def test_us_updates_have_effective_dates(self, us):
        updates = await us.get_regulatory_updates()
        assert len(updates) >= 2
        dated = [u for u in updates if u.effective_date]
        assert len(dated) >= 2

    @pytest.mark.asyncio
    async def test_eu_titanium_dioxide_ban_present(self, eu):
        updates = await eu.get_regulatory_updates()
        summaries = " ".join(u.summary for u in updates).lower()
        assert "titanium" in summaries or "e171" in summaries

    @pytest.mark.asyncio
    async def test_au_allergen_update_present(self, au):
        updates = await au.get_regulatory_updates()
        summaries = " ".join(u.summary for u in updates).lower()
        assert "allergen" in summaries or "pregnancy" in summaries

    @pytest.mark.asyncio
    async def test_jp_walnut_allergen_present(self, jp):
        updates = await jp.get_regulatory_updates()
        summaries = " ".join(u.summary for u in updates).lower()
        assert "walnut" in summaries or "クルミ" in summaries

    @pytest.mark.asyncio
    async def test_ca_sesame_allergen_present(self, ca):
        updates = await ca.get_regulatory_updates()
        summaries = " ".join(u.summary for u in updates).lower()
        assert "sesame" in summaries

    # --- Date filter ---

    @pytest.mark.asyncio
    async def test_date_filter_excludes_old_changes(self, us):
        all_updates = await us.get_regulatory_updates()
        recent = await us.get_regulatory_updates(since_date="2023-01-01")
        assert len(recent) <= len(all_updates)
        for u in recent:
            if u.effective_date:
                assert u.effective_date >= "2023-01-01"

    @pytest.mark.asyncio
    async def test_date_filter_future_returns_empty(self, us):
        far_future = await us.get_regulatory_updates(since_date="2099-01-01")
        assert far_future == []

    # --- Base class default ---

    @pytest.mark.asyncio
    async def test_base_class_returns_empty(self):
        from mcp_food_regulatory.sources.in_fssai import INFSSAISource
        import httpx
        source = INFSSAISource(httpx.AsyncClient())
        result = await source.get_regulatory_updates()
        assert result == []

    # --- Server tool ---

    @pytest.mark.asyncio
    async def test_server_get_regulatory_updates_us(self):
        from mcp_food_regulatory.server import get_regulatory_updates
        result = await get_regulatory_updates(["us"])
        assert "results" in result
        assert "us" in result["results"]
        assert len(result["results"]["us"]) >= 2

    @pytest.mark.asyncio
    async def test_server_get_regulatory_updates_multi_market(self):
        from mcp_food_regulatory.server import get_regulatory_updates
        result = await get_regulatory_updates(["us", "eu", "au"])
        for m in ["us", "eu", "au"]:
            assert m in result["results"]
            assert len(result["results"][m]) >= 1

    @pytest.mark.asyncio
    async def test_server_get_regulatory_updates_with_since(self):
        from mcp_food_regulatory.server import get_regulatory_updates
        result = await get_regulatory_updates(["us"], since_date="2023-01-01")
        updates = result["results"]["us"]
        for u in updates:
            if u.get("effective_date"):
                assert u["effective_date"] >= "2023-01-01"

    @pytest.mark.asyncio
    async def test_server_get_regulatory_updates_unknown_market(self):
        from mcp_food_regulatory.server import get_regulatory_updates
        result = await get_regulatory_updates(["mars"])
        assert result["errors"] is not None

    @pytest.mark.asyncio
    async def test_server_get_regulatory_updates_market_no_seed_returns_empty(self):
        from mcp_food_regulatory.server import get_regulatory_updates
        result = await get_regulatory_updates(["cn"])
        assert "cn" in result["results"]
        assert result["results"]["cn"] == []

    @pytest.mark.asyncio
    async def test_server_summary_mentions_count(self):
        from mcp_food_regulatory.server import get_regulatory_updates
        result = await get_regulatory_updates(["us", "eu"])
        assert "update" in result["summary"].lower() or "US" in result["summary"]

    @pytest.mark.asyncio
    async def test_server_data_note_present(self):
        from mcp_food_regulatory.server import get_regulatory_updates
        result = await get_regulatory_updates(["us"])
        assert "data_note" in result
        assert "curated" in result["data_note"].lower()


# ------------------------------------------------------------------ #
#  Philippines FDA tests                                              #
# ------------------------------------------------------------------ #

class TestPHFDASource:

    @pytest.mark.asyncio
    async def test_market_is_ph(self, ph):
        assert ph.market == Market.PH

    @pytest.mark.asyncio
    async def test_search_vitamin_d_permitted(self, ph):
        results = await ph.search_health_claims("vitamin d")
        assert len(results) >= 1
        assert any(r.status == ClaimStatus.PERMITTED for r in results)
        assert any(r.claim_type == "nutrient_function" for r in results)

    @pytest.mark.asyncio
    async def test_search_moringa_conditional(self, ph):
        results = await ph.search_health_claims("moringa")
        assert len(results) >= 1
        assert any(r.status == ClaimStatus.CONDITIONAL for r in results)

    @pytest.mark.asyncio
    async def test_search_malunggay_alias(self, ph):
        # malunggay is the local name -- alias lookup must work
        results = await ph.search_health_claims("malunggay")
        assert len(results) >= 1
        assert any(r.status == ClaimStatus.CONDITIONAL for r in results)

    @pytest.mark.asyncio
    async def test_search_inulin_not_defined(self, ph):
        results = await ph.search_health_claims("inulin")
        assert len(results) >= 1
        assert any(r.status == ClaimStatus.NOT_DEFINED for r in results)

    @pytest.mark.asyncio
    async def test_search_caffeine_not_defined(self, ph):
        results = await ph.search_health_claims("caffeine")
        assert len(results) >= 1
        assert any(r.status == ClaimStatus.NOT_DEFINED for r in results)

    @pytest.mark.asyncio
    async def test_partial_string_does_not_match(self, ph):
        # "cal" must NOT match calcium -- no bidirectional substring matching
        results = await ph.search_health_claims("cal")
        assert all(r.status == ClaimStatus.NOT_DEFINED for r in results)

    @pytest.mark.asyncio
    async def test_claim_type_filter_exact_match(self, ph):
        # claim_type="nutrient" must NOT match "nutrient_function"
        results = await ph.search_health_claims("vitamin d", claim_type="nutrient")
        # Should return nothing (or NOT_DEFINED fallback) since no entry has claim_type="nutrient"
        assert all(r.status == ClaimStatus.NOT_DEFINED for r in results)

    @pytest.mark.asyncio
    async def test_get_standard_circular_2014_007(self, ph):
        standard = await ph.get_standard("FDA Circular 2014-007")
        assert standard is not None
        assert standard.market == Market.PH
        assert "Health" in standard.title or "Nutrient" in standard.title
        assert standard.key_definitions is not None

    @pytest.mark.asyncio
    async def test_get_standard_ra_3720(self, ph):
        standard = await ph.get_standard("Republic Act 3720")
        assert standard is not None
        assert standard.market == Market.PH

    @pytest.mark.asyncio
    async def test_get_standard_unknown_returns_none(self, ph):
        result = await ph.get_standard("PH 999-9999-UNKNOWN")
        assert result is None

    @pytest.mark.asyncio
    async def test_search_standards_returns_list(self, ph):
        # seeded fallback must work even if live fetch fails
        results = await ph.search_standards("health claims")
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_market_overview(self, ph):
        overview = await ph.get_market_overview()
        assert overview.market == Market.PH
        assert "FDA" in overview.authority_name
        assert len(overview.key_legislation) >= 3

    @pytest.mark.asyncio
    async def test_unknown_ingredient_no_crash(self, ph):
        results = await ph.search_health_claims("xylobiose_fictional_ingredient_xyz")
        assert isinstance(results, list)
        assert len(results) >= 1
        assert results[0].status == ClaimStatus.NOT_DEFINED


# ------------------------------------------------------------------ #
#  Japan CAA tests                                                    #
# ------------------------------------------------------------------ #

class TestJPCAASource:

    @pytest.mark.asyncio
    async def test_market_is_jp(self, jp):
        assert jp.market == Market.JP

    @pytest.mark.asyncio
    async def test_search_vitamin_d_permitted(self, jp):
        results = await jp.search_health_claims("vitamin d")
        assert len(results) >= 1
        assert any(r.status == ClaimStatus.PERMITTED for r in results)
        assert any(r.claim_type == "nutrient_function" for r in results)

    @pytest.mark.asyncio
    async def test_search_calcium_permitted(self, jp):
        results = await jp.search_health_claims("calcium")
        assert len(results) >= 1
        assert any(r.status == ClaimStatus.PERMITTED for r in results)

    @pytest.mark.asyncio
    async def test_search_unknown_not_defined(self, jp):
        results = await jp.search_health_claims("xylobiose_fictional_xyz")
        assert isinstance(results, list)
        assert len(results) >= 1
        assert results[0].status == ClaimStatus.NOT_DEFINED

    @pytest.mark.asyncio
    async def test_get_standard_health_promotion_act(self, jp):
        standard = await jp.get_standard("Health Promotion Act 2002")
        assert standard is not None
        assert standard.market == Market.JP

    @pytest.mark.asyncio
    async def test_get_standard_unknown_returns_none(self, jp):
        assert await jp.get_standard("JP 999-UNKNOWN") is None

    @pytest.mark.asyncio
    async def test_search_standards_returns_list(self, jp):
        results = await jp.search_standards("health")
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_market_overview(self, jp):
        overview = await jp.get_market_overview()
        assert overview.market == Market.JP
        assert "CAA" in overview.authority_name or "Consumer" in overview.authority_name
        assert len(overview.key_legislation) >= 2

    @pytest.mark.asyncio
    async def test_two_calls_no_crash(self, jp):
        r1 = await jp.search_health_claims("calcium")
        r2 = await jp.search_health_claims("calcium")
        assert len(r1) == len(r2)


# ------------------------------------------------------------------ #
#  US FDA tests                                                       #
# ------------------------------------------------------------------ #

class TestUSFDASource:

    @pytest.mark.asyncio
    async def test_market_is_us(self, us):
        assert us.market == Market.US

    @pytest.mark.asyncio
    async def test_search_calcium_returns_results(self, us):
        results = await us.search_health_claims("calcium")
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_folic_acid_returns_results(self, us):
        results = await us.search_health_claims("folic acid")
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_unknown_not_defined(self, us):
        results = await us.search_health_claims("xylobiose_fictional_xyz")
        assert len(results) >= 1
        assert results[0].status == ClaimStatus.NOT_DEFINED

    @pytest.mark.asyncio
    async def test_get_standard_21_cfr(self, us):
        standard = await us.get_standard("21 CFR Part 101")
        assert standard is not None
        assert standard.market == Market.US

    @pytest.mark.asyncio
    async def test_get_standard_unknown_returns_none(self, us):
        assert await us.get_standard("US 999-UNKNOWN") is None

    @pytest.mark.asyncio
    async def test_search_standards_returns_list(self, us):
        results = await us.search_standards("labeling")
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_market_overview(self, us):
        overview = await us.get_market_overview()
        assert overview.market == Market.US
        assert "FDA" in overview.authority_name
        assert len(overview.key_legislation) >= 2

    @pytest.mark.asyncio
    async def test_two_calls_no_crash(self, us):
        r1 = await us.search_health_claims("calcium")
        r2 = await us.search_health_claims("calcium")
        assert len(r1) == len(r2)


# ------------------------------------------------------------------ #
#  Canada Health Canada tests                                         #
# ------------------------------------------------------------------ #

class TestCAHealthCanadaSource:

    @pytest.mark.asyncio
    async def test_market_is_ca(self, ca):
        assert ca.market == Market.CA

    @pytest.mark.asyncio
    async def test_search_calcium_returns_results(self, ca):
        results = await ca.search_health_claims("calcium")
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_vitamin_c_returns_results(self, ca):
        results = await ca.search_health_claims("vitamin c")
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_unknown_not_defined(self, ca):
        results = await ca.search_health_claims("xylobiose_fictional_xyz")
        assert len(results) >= 1
        assert results[0].status == ClaimStatus.NOT_DEFINED

    @pytest.mark.asyncio
    async def test_get_standard_fdr_b01603(self, ca):
        standard = await ca.get_standard("FDR B.01.603")
        assert standard is not None
        assert standard.market == Market.CA

    @pytest.mark.asyncio
    async def test_get_standard_unknown_returns_none(self, ca):
        assert await ca.get_standard("CA 999-UNKNOWN") is None

    @pytest.mark.asyncio
    async def test_search_standards_returns_list(self, ca):
        results = await ca.search_standards("health claims")
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_market_overview(self, ca):
        overview = await ca.get_market_overview()
        assert overview.market == Market.CA
        assert "Health Canada" in overview.authority_name
        assert len(overview.key_legislation) >= 2

    @pytest.mark.asyncio
    async def test_two_calls_no_crash(self, ca):
        r1 = await ca.search_health_claims("vitamin c")
        r2 = await ca.search_health_claims("vitamin c")
        assert len(r1) == len(r2)


# ------------------------------------------------------------------ #
#  Australia FSANZ tests                                              #
# ------------------------------------------------------------------ #

class TestAUFSANZSource:

    @pytest.mark.asyncio
    async def test_market_is_au(self, au):
        assert au.market == Market.AU

    @pytest.mark.asyncio
    async def test_search_calcium_returns_results(self, au):
        results = await au.search_health_claims("calcium")
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_folate_returns_results(self, au):
        results = await au.search_health_claims("folate")
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_unknown_not_defined(self, au):
        results = await au.search_health_claims("xylobiose_fictional_xyz")
        assert len(results) >= 1
        assert results[0].status == ClaimStatus.NOT_DEFINED

    @pytest.mark.asyncio
    async def test_get_standard_127(self, au):
        standard = await au.get_standard("Standard 1.2.7")
        assert standard is not None
        assert standard.market == Market.AU
        assert standard.key_definitions is not None

    @pytest.mark.asyncio
    async def test_get_standard_unknown_returns_none(self, au):
        assert await au.get_standard("AU 999-UNKNOWN") is None

    @pytest.mark.asyncio
    async def test_search_standards_returns_list(self, au):
        results = await au.search_standards("nutrition")
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_market_overview(self, au):
        overview = await au.get_market_overview()
        assert overview.market == Market.AU
        assert "FSANZ" in overview.authority_name
        assert len(overview.key_legislation) >= 2

    @pytest.mark.asyncio
    async def test_two_calls_no_crash(self, au):
        r1 = await au.search_health_claims("calcium")
        r2 = await au.search_health_claims("calcium")
        assert len(r1) == len(r2)


# ------------------------------------------------------------------ #
#  Parametrized smoke tests for Batch 2 + 3 + South Asia markets     #
# ------------------------------------------------------------------ #

# (source_class, market_enum, known_standard_id)
_BATCH_MARKETS = [
    (INFSSAISource,   Market.IN,  "FSS Claims 2018"),
    (CNNHCSource,     Market.CN,  "GB 28050-2011"),
    (KRMFDSSource,    Market.KR,  "Health Functional Food Act"),
    (BRANVISASource,  Market.BR,  "RDC 429/2020"),
    (COINVIMASource,  Market.CO,  "Resolución 2508/2012"),
    (CLMINSALSource,  Market.CL,  "DS 977/96 RSA"),
    (MXCOFEPRISSource, Market.MX, "NOM-051-SCFI/SSA1-2010"),
    (AEESMASource,    Market.AE,  "UAE.S GSO 9:2013"),
    (SASFDASource,    Market.SA,  "SFDA.FD 9001:2017"),
    (ZADoHSource,     Market.ZA,  "R146/2010"),
    (PKPFASource,     Market.PK,  "Pure Food Ordinance 1960"),
    (BDBFSASource,    Market.BD,  "Food Safety Act 2013"),
    (LKFCAUSource,    Market.LK,  "Food Act No. 26/1980"),
    (NPDFTQCSource,   Market.NP,  "Food Act 1966"),
    (BTBFDRASource,   Market.BT,  "Food Safety and Quality Act 2005"),
    (MVMFDASource,    Market.MV,  "Food Safety Act 2019"),
]

_market_ids = [m[1].value for m in _BATCH_MARKETS]


@pytest.mark.parametrize("source_cls,market_enum,known_std", _BATCH_MARKETS, ids=_market_ids)
class TestBatchMarketSmoke:
    """Five smoke assertions run against every Batch 2/3/South-Asia connector."""

    @pytest.mark.asyncio
    async def test_market_overview_non_empty(self, source_cls, market_enum, known_std):
        client = httpx.AsyncClient()
        source = source_cls(client)
        overview = await source.get_market_overview()
        assert overview is not None
        assert overview.market == market_enum
        assert overview.authority_name
        assert len(overview.key_legislation) >= 1

    @pytest.mark.asyncio
    async def test_search_calcium_returns_results(self, source_cls, market_enum, known_std):
        client = httpx.AsyncClient()
        source = source_cls(client)
        results = await source.search_health_claims("calcium")
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_standards_non_empty(self, source_cls, market_enum, known_std):
        client = httpx.AsyncClient()
        source = source_cls(client)
        results = await source.search_standards("")
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_get_known_standard(self, source_cls, market_enum, known_std):
        client = httpx.AsyncClient()
        source = source_cls(client)
        standard = await source.get_standard(known_std)
        assert standard is not None
        assert standard.market == market_enum
        assert standard.title

    @pytest.mark.asyncio
    async def test_unknown_ingredient_no_crash(self, source_cls, market_enum, known_std):
        client = httpx.AsyncClient()
        source = source_cls(client)
        results = await source.search_health_claims("xylobiose_fictional_ingredient_xyz")
        assert isinstance(results, list)
