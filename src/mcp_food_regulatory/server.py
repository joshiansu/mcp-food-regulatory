"""
mcp-food-regulatory: MCP server for food regulatory database access.

Exposes 9 tools to AI agents:
  - search_health_claims
  - get_standard
  - search_standards
  - get_additive_status
  - compare_markets
  - get_market_overview
  - get_nutrient_claim_thresholds
  - compare_nutrient_claim_thresholds
  - get_regulatory_updates

Run with:
  uv run mcp-food-regulatory                          # stdio (Claude Desktop)
  uv run mcp-food-regulatory --transport http         # HTTP (agents/remote)
"""

from __future__ import annotations
from typing import Optional
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastmcp import FastMCP

from mcp_food_regulatory.models import Market, NutrientClaimThreshold, RegulatoryUpdate
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

# ------------------------------------------------------------------ #
#  Server init                                                        #
# ------------------------------------------------------------------ #

mcp = FastMCP(
    "food-regulatory",
    instructions=(
        "This server provides access to food regulatory databases across global markets. "
        "Use it to check health claim status, look up regulatory standards, compare "
        "claim permissions across markets, get market regulatory overviews, and look up "
        "nutrient content claim thresholds (e.g. 'high in protein', 'source of fibre', 'low fat'). "
        "Supported markets: codex, eu, ph, jp, us, ca, au, in, cn, kr, br, co, cl, mx, ae, sa, za, pk, bd, lk, np, bt, mv. "
        "Use get_market_overview to explore a market. Use get_nutrient_claim_thresholds or "
        "compare_nutrient_claim_thresholds for label compliance threshold lookups. "
        "Use get_regulatory_updates to check what changed in a market since a given date. "
        "See README for contribution guide."
    ),
)

# Shared HTTP client — reused across all sources for connection pooling
_http_client: httpx.AsyncClient | None = None

def _get_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "mcp-food-regulatory/0.1 "
                    "(github.com/YOUR_USERNAME/mcp-food-regulatory; "
                    "open-source MCP server for food regulatory data)"
                )
            },
        )
    return _http_client


# Registry of implemented sources — add new sources here as they're built
SOURCES = {
    Market.CODEX: CodexSource,
    Market.EU: EUSource,
    Market.PH: PhFDASource,
    Market.JP: JPCAASource,
    Market.US: USFDASource,
    Market.CA: CAHealthCanadaSource,
    Market.AU: AUFSANZSource,
    Market.IN: INFSSAISource,
    Market.CN: CNNHCSource,
    Market.KR: KRMFDSSource,
    Market.BR: BRANVISASource,
    Market.CO: COINVIMASource,
    Market.CL: CLMINSALSource,
    Market.MX: MXCOFEPRISSource,
    Market.AE: AEESMASource,
    Market.SA: SASFDASource,
    Market.ZA: ZADoHSource,
    Market.PK: PKPFASource,
    Market.BD: BDBFSASource,
    Market.LK: LKFCAUSource,
    Market.NP: NPDFTQCSource,
    Market.BT: BTBFDRASource,
    Market.MV: MVMFDASource,
}

def _get_source(market: Market):
    cls = SOURCES.get(market)
    if cls is None:
        raise ValueError(
            f"Market '{market}' is not yet implemented. "
            f"Available markets: {', '.join(m.value for m in SOURCES)}. "
            "See README.md to contribute a new market connector."
        )
    return cls(_get_client())


# ------------------------------------------------------------------ #
#  Call logging -- JSONL + Supabase                                   #
# ------------------------------------------------------------------ #

_LOG_PATH = Path.home() / ".mcp-food-regulatory" / "history.jsonl"

# Lazy Supabase singleton -- None if env vars are absent
_supabase = None

def _get_supabase():
    global _supabase
    if _supabase is not None:
        return _supabase
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        return None
    from supabase import create_client  # imported lazily -- optional dep
    _supabase = create_client(url, key)
    return _supabase


def _summarise_result(result: dict) -> dict:
    s: dict = {}
    if "error" in result and result["error"]:
        s["error"] = str(result["error"])[:200]
    if "references" in result:
        s["ref_count"] = len(result["references"])
    if "results" in result and isinstance(result["results"], dict):
        s["market_counts"] = {
            k: len(v) if isinstance(v, list) else 1
            for k, v in result["results"].items()
        }
    if "comparison" in result:
        s["comparison_count"] = len(result["comparison"])
    if "summary" in result and isinstance(result["summary"], str):
        s["outcome"] = result["summary"][:300]
    return s


def _write_log(record: dict) -> None:
    """Synchronous worker -- runs in a thread via asyncio.to_thread."""
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _LOG_PATH.open("a") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass

    try:
        sb = _get_supabase()
        if sb:
            sb.table("tool_calls").insert(record).execute()
    except Exception:
        pass


async def _log_call(tool: str, args: dict, result: dict) -> None:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "tool": tool,
        "args": args,
        "ingredient": args.get("ingredient"),
        "markets": args.get("markets") or (
            [args["market"]] if args.get("market") else None
        ),
        "summary": _summarise_result(result),
    }
    await asyncio.to_thread(_write_log, record)


_PREVIEW_LEN = 180

def _extract_refs(items: list) -> list[dict]:
    """Build a deduplicated reference list from ClaimResult / Standard objects.

    Each entry has: label, url, preview (short excerpt), cite (markdown link).
    """
    seen: set[str] = set()
    refs: list[dict] = []

    def _add(label: str, url: str | None, preview: str | None) -> None:
        if not url or url in seen:
            return
        seen.add(url)
        snippet = (preview or "").strip()
        if len(snippet) > _PREVIEW_LEN:
            snippet = snippet[:_PREVIEW_LEN].rstrip() + "..."
        refs.append({
            "label": label,
            "url": url,
            "preview": snippet or None,
            "cite": f"[{label}]({url})",
        })

    for item in items:
        # ClaimResult
        if hasattr(item, "basis") and item.basis:
            b = item.basis
            article_suffix = f", {b.article}" if b.article else ""
            label = f"{b.instrument}{article_suffix}"
            url = b.url or getattr(item, "source_url", None)
            preview = getattr(item, "conditions", None)
            _add(label, url, preview)

        # Standard
        if hasattr(item, "full_text_url"):
            label = f"{item.standard_id} — {item.title}"
            _add(label, item.full_text_url, getattr(item, "summary", None))

    return refs


# ------------------------------------------------------------------ #
#  Tools                                                              #
# ------------------------------------------------------------------ #

@mcp.tool
async def search_health_claims(
    ingredient: str,
    markets: list[str],
    claim_type: Optional[str] = None,
) -> dict:
    """
    Search for health and nutrition claim status for an ingredient across one or more markets.

    Args:
        ingredient: Ingredient name, e.g. "caffeine", "inulin", "vitamin D", "dietary fibre"
        markets: List of market codes. Available: "codex", "eu"
                 Example: ["eu", "codex"] or ["eu"]
        claim_type: Optional filter. Examples: "health_claim", "nutrition_claim",
                    "prebiotic", "function_claim". Omit to return all types.

    Returns:
        Dict keyed by market code, each containing a list of claim results
        with status, conditions, and regulatory basis.

    Example:
        search_health_claims("caffeine", ["eu", "codex"])
        search_health_claims("inulin", ["eu"], claim_type="prebiotic")
    """
    results = {}
    errors = {}
    all_claims = []

    for market_str in markets:
        try:
            market = Market(market_str.lower())
        except ValueError:
            errors[market_str] = f"Unknown market '{market_str}'. Available: {', '.join(m.value for m in SOURCES)}"
            continue

        try:
            source = _get_source(market)
            claims = await source.search_health_claims(ingredient, claim_type)
            all_claims.extend(claims)
            results[market_str] = [c.model_dump() for c in claims]
        except NotImplementedError as e:
            errors[market_str] = str(e)
        except Exception as e:
            errors[market_str] = f"Error fetching data: {e}"

    out = {
        "ingredient": ingredient,
        "claim_type_filter": claim_type,
        "results": results,
        "references": _extract_refs(all_claims),
        "errors": errors if errors else None,
    }
    asyncio.create_task(_log_call(
        "search_health_claims",
        {"ingredient": ingredient, "markets": markets, "claim_type": claim_type},
        out,
    ))
    return out


@mcp.tool
async def get_standard(
    standard_id: str,
    market: str,
) -> dict:
    """
    Retrieve a specific regulatory standard or regulation by its identifier.

    Args:
        standard_id: Official standard/regulation ID.
                     Examples: "CXG 2-1985", "CXG 23-1997", "EC 1924/2006", "EU 432/2012"
        market: Market code. Examples: "codex", "eu"

    Returns:
        Standard metadata including title, category, adoption date, summary,
        key definitions, and full-text URL.

    Example:
        get_standard("CXG 2-1985", "codex")      → Codex dietary fibre guidelines
        get_standard("EC 1924/2006", "eu")        → EU health claims regulation
    """
    try:
        market_enum = Market(market.lower())
    except ValueError:
        return {"error": f"Unknown market '{market}'. Available: {', '.join(m.value for m in SOURCES)}"}

    try:
        source = _get_source(market_enum)
        standard = await source.get_standard(standard_id)
        if standard is None:
            return {
                "found": False,
                "standard_id": standard_id,
                "market": market,
                "message": (
                    f"Standard '{standard_id}' not found in {market} data. "
                    "Check the ID format or search_standards() for a keyword search."
                ),
            }
        out = {"found": True, **standard.model_dump(), "references": _extract_refs([standard])}
        asyncio.create_task(_log_call(
            "get_standard",
            {"standard_id": standard_id, "market": market},
            out,
        ))
        return out
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
async def search_standards(
    query: str,
    markets: list[str],
) -> dict:
    """
    Search for regulatory standards by keyword across one or more markets.

    Args:
        query: Search keywords. Examples: "dietary fibre", "health claims",
               "food additives", "labelling"
        markets: List of market codes. Available: "codex", "eu"

    Returns:
        Dict keyed by market, each containing a list of matching standards
        with titles, categories, and links.

    Example:
        search_standards("dietary fibre", ["codex", "eu"])
        search_standards("health claims", ["eu"])
    """
    results = {}
    all_standards = []

    for market_str in markets:
        try:
            market = Market(market_str.lower())
            source = _get_source(market)
            standards = await source.search_standards(query)
            all_standards.extend(standards)
            results[market_str] = [s.model_dump() for s in standards]
        except (ValueError, NotImplementedError) as e:
            results[market_str] = {"error": str(e)}
        except Exception as e:
            results[market_str] = {"error": f"Search failed: {e}"}

    out = {"query": query, "results": results, "references": _extract_refs(all_standards)}
    asyncio.create_task(_log_call(
        "search_standards",
        {"query": query, "markets": markets},
        out,
    ))
    return out


@mcp.tool
async def compare_markets(
    ingredient: str,
    claim_type: str,
    markets: list[str],
) -> dict:
    """
    Compare claim/ingredient regulatory status side-by-side across multiple markets.

    This is the primary tool for multi-market regulatory gap analysis.

    Args:
        ingredient: Ingredient name, e.g. "inulin", "caffeine", "vitamin D"
        claim_type: Type of claim to compare, e.g. "prebiotic", "health_claim",
                    "nutrition_claim", "dietary_fibre"
        markets: List of market codes to compare. Available: "codex", "eu"
                 Example: ["eu", "codex"]

    Returns:
        Side-by-side comparison with per-market status, conditions, and a
        plain-language summary of key differences.

    Example:
        compare_markets("inulin", "prebiotic", ["eu", "codex"])
        compare_markets("caffeine", "health_claim", ["eu", "codex"])
    """
    all_results = []
    errors = {}

    for market_str in markets:
        try:
            market = Market(market_str.lower())
            source = _get_source(market)
            claims = await source.search_health_claims(ingredient, claim_type)
            all_results.extend(claims)
        except (ValueError, NotImplementedError) as e:
            errors[market_str] = str(e)
        except Exception as e:
            errors[market_str] = f"Error: {e}"

    # Build summary
    statuses = {r.market.value: r.status.value for r in all_results}
    summary_parts = []
    for market_str, status in statuses.items():
        summary_parts.append(f"{market_str.upper()}: {status}")

    permitted = [m for m, s in statuses.items() if s == "permitted"]
    prohibited = [m for m, s in statuses.items() if s == "prohibited"]
    not_defined = [m for m, s in statuses.items() if s == "not_defined"]

    summary_lines = []
    if permitted:
        summary_lines.append(f"Permitted in: {', '.join(permitted).upper()}")
    if prohibited:
        summary_lines.append(f"Prohibited in: {', '.join(prohibited).upper()}")
    if not_defined:
        summary_lines.append(f"No specific provision in: {', '.join(not_defined).upper()}")
    if errors:
        summary_lines.append(f"Data unavailable for: {', '.join(errors.keys()).upper()}")

    out = {
        "ingredient": ingredient,
        "claim_type": claim_type,
        "comparison": [r.model_dump() for r in all_results],
        "summary": " | ".join(summary_lines) or "No data found.",
        "references": _extract_refs(all_results),
        "errors": errors if errors else None,
    }
    asyncio.create_task(_log_call(
        "compare_markets",
        {"ingredient": ingredient, "claim_type": claim_type, "markets": markets},
        out,
    ))
    return out


@mcp.tool
async def get_market_overview(market: str) -> dict:
    """
    Get a high-level overview of a market's food regulatory framework.

    Args:
        market: Market code. Available: "codex", "eu"

    Returns:
        Authority name and URL, key legislation, health claims framework summary.

    Example:
        get_market_overview("eu")
        get_market_overview("codex")
    """
    try:
        market_enum = Market(market.lower())
        source = _get_source(market_enum)
        overview = await source.get_market_overview()
        refs = []
        if overview.authority_url:
            refs.append({
                "label": overview.authority_name,
                "url": overview.authority_url,
                "preview": overview.health_claims_framework[:_PREVIEW_LEN].rstrip() + "..."
                    if overview.health_claims_framework and len(overview.health_claims_framework) > _PREVIEW_LEN
                    else overview.health_claims_framework,
                "cite": f"[{overview.authority_name}]({overview.authority_url})",
            })
        out = {**overview.model_dump(), "references": refs}
        asyncio.create_task(_log_call(
            "get_market_overview",
            {"market": market},
            out,
        ))
        return out
    except ValueError:
        return {
            "error": f"Unknown market '{market}'.",
            "available_markets": [m.value for m in SOURCES],
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
async def get_regulatory_updates(
    markets: list[str],
    since_date: Optional[str] = None,
) -> dict:
    """
    Get known regulatory changes for one or more markets since a given date.

    Answers the question "did something change that affects my product?" -- covering
    new allergen mandates, banned additives, amended labelling standards, and new legislation.

    Args:
        markets: List of market codes. Examples: ["us", "eu", "au", "jp", "ca"]
        since_date: ISO date string (YYYY-MM-DD or YYYY-MM). Only returns changes on or
                    after this date. Omit to return all known changes.
                    Examples: "2023-01-01", "2022-06"

    Returns:
        Dict keyed by market, each containing a list of regulatory updates with:
        change_type, summary, effective_date, instrument, url.

    Example:
        get_regulatory_updates(["us"], since_date="2023-01-01")
        get_regulatory_updates(["eu", "au", "jp"])
    """
    results: dict[str, list] = {}
    errors: dict[str, str] = {}
    all_updates: list[RegulatoryUpdate] = []

    for market_str in markets:
        try:
            market = Market(market_str.lower())
        except ValueError:
            errors[market_str] = f"Unknown market '{market_str}'. Available: {', '.join(m.value for m in SOURCES)}"
            continue
        try:
            source = _get_source(market)
            updates = await source.get_regulatory_updates(since_date)
            all_updates.extend(updates)
            results[market_str] = [u.model_dump() for u in updates]
        except Exception as e:
            errors[market_str] = f"Error: {e}"

    markets_with_data = [m for m in markets if results.get(m)]
    markets_no_data = [m for m in markets if m in results and not results[m]]
    summary_parts = []
    total = sum(len(v) for v in results.values())
    if total:
        summary_parts.append(f"{total} update(s) found across: {', '.join(markets_with_data).upper()}")
    if markets_no_data:
        summary_parts.append(f"No updates seeded yet for: {', '.join(markets_no_data).upper()}")
    if errors:
        summary_parts.append(f"Errors: {', '.join(errors.keys()).upper()}")

    out = {
        "since_date": since_date,
        "results": results,
        "summary": " | ".join(summary_parts) or "No data found.",
        "errors": errors if errors else None,
        "data_note": (
            "Updates are curated manually from verified official sources. "
            "Coverage is not exhaustive -- always check the authority website for the latest."
        ),
    }
    asyncio.create_task(_log_call(
        "get_regulatory_updates",
        {"markets": markets, "since_date": since_date},
        out,
    ))
    return out


@mcp.tool
async def get_nutrient_claim_thresholds(
    markets: list[str],
    nutrient: Optional[str] = None,
) -> dict:
    """
    Get numeric thresholds required to make a nutrient content claim in one or more markets.

    Returns the qualifying threshold (e.g. ≥3g/100g) for claims like 'source of fibre',
    'high in protein', 'low fat', 'sugar free', 'no added sugars', 'reduced sodium'.

    Args:
        markets: List of market codes. Examples: ["eu", "us", "au"]
        nutrient: Optional nutrient filter. Examples: "dietary fibre", "protein", "fat",
                  "saturated fat", "sugars", "sodium", "energy", "vitamins_minerals".
                  Omit to return all nutrients for the market.

    Returns:
        Dict keyed by market, each containing a list of threshold objects with
        claim wording, threshold values, basis, and governing instrument.

    Example:
        get_nutrient_claim_thresholds(["eu", "us"], "dietary fibre")
        get_nutrient_claim_thresholds(["eu"], "protein")
    """
    results: dict[str, list] = {}
    errors: dict[str, str] = {}
    all_thresholds: list[NutrientClaimThreshold] = []

    for market_str in markets:
        try:
            market = Market(market_str.lower())
        except ValueError:
            errors[market_str] = f"Unknown market '{market_str}'. Available: {', '.join(m.value for m in SOURCES)}"
            continue
        try:
            source = _get_source(market)
            thresholds = await source.get_nutrient_claim_thresholds(nutrient)
            all_thresholds.extend(thresholds)
            results[market_str] = [t.model_dump() for t in thresholds]
        except Exception as e:
            errors[market_str] = f"Error: {e}"

    out = {
        "nutrient_filter": nutrient,
        "results": results,
        "errors": errors if errors else None,
        "data_note": (
            "Thresholds are seeded from official regulation text and verified periodically. "
            "Always confirm against the current regulation before making label claims."
        ),
    }
    asyncio.create_task(_log_call(
        "get_nutrient_claim_thresholds",
        {"markets": markets, "nutrient": nutrient},
        out,
    ))
    return out


@mcp.tool
async def compare_nutrient_claim_thresholds(
    nutrient: str,
    markets: list[str],
) -> dict:
    """
    Compare nutrient content claim thresholds side-by-side across multiple markets.

    Shows how the same nutrient claim (e.g. 'high in protein') is defined differently
    in each market -- useful for multi-market product development and label compliance.

    Args:
        nutrient: Nutrient to compare. Examples: "dietary fibre", "protein", "fat",
                  "saturated fat", "sugars", "sodium", "energy"
        markets: List of market codes to compare. Examples: ["eu", "us", "au"]

    Returns:
        Side-by-side comparison of thresholds per market per claim type,
        with a plain-language summary of key differences.

    Example:
        compare_nutrient_claim_thresholds("dietary fibre", ["eu", "us"])
        compare_nutrient_claim_thresholds("protein", ["eu", "us", "au"])
    """
    per_market: dict[str, list] = {}
    errors: dict[str, str] = {}
    all_thresholds: list[NutrientClaimThreshold] = []

    for market_str in markets:
        try:
            market = Market(market_str.lower())
        except ValueError:
            errors[market_str] = f"Unknown market '{market_str}'"
            continue
        try:
            source = _get_source(market)
            thresholds = await source.get_nutrient_claim_thresholds(nutrient)
            all_thresholds.extend(thresholds)
            per_market[market_str] = [t.model_dump() for t in thresholds]
        except Exception as e:
            errors[market_str] = f"Error: {e}"

    # Build comparison summary
    comparison: list[dict] = []
    claim_types: set[str] = {t.claim_type for t in all_thresholds}
    for ct in sorted(claim_types):
        row: dict = {"claim_type": ct}
        for market_str in markets:
            entries = [t for t in all_thresholds if t.market.value == market_str and t.claim_type == ct]
            if entries:
                row[market_str] = entries[0].threshold_value
            else:
                row[market_str] = "not defined"
        comparison.append(row)

    markets_with_data = [m for m in markets if per_market.get(m)]
    markets_without = [m for m in markets if not per_market.get(m) and m not in errors]
    summary_parts = []
    if markets_with_data:
        summary_parts.append(f"Thresholds found in: {', '.join(markets_with_data).upper()}")
    if markets_without:
        summary_parts.append(f"No threshold data yet for: {', '.join(markets_without).upper()}")
    if errors:
        summary_parts.append(f"Errors: {', '.join(errors.keys()).upper()}")

    out = {
        "nutrient": nutrient,
        "per_market": per_market,
        "comparison_table": comparison,
        "summary": " | ".join(summary_parts) or "No data found.",
        "errors": errors if errors else None,
        "data_note": (
            "Thresholds are seeded from official regulation text. "
            "Always confirm against the current regulation before making label claims."
        ),
    }
    asyncio.create_task(_log_call(
        "compare_nutrient_claim_thresholds",
        {"nutrient": nutrient, "markets": markets},
        out,
    ))
    return out


@mcp.tool
async def list_markets() -> dict:
    """
    List all available markets and their implementation status.

    Returns:
        Dict of market codes with their status (implemented / planned)
        and the regulatory authority for each.
    """
    implemented = {
        "codex": "Codex Alimentarius Commission (FAO/WHO)",
        "eu": "European Commission / EFSA",
        "ph": "Philippines Food and Drug Administration (FDA)",
        "jp": "Consumer Affairs Agency Japan (CAA)",
        "us": "Food and Drug Administration (US FDA)",
        "ca": "Health Canada / CFIA",
        "au": "Food Standards Australia New Zealand (FSANZ)",
        "in": "Food Safety and Standards Authority of India (FSSAI)",
        "cn": "National Health Commission / SAMR (China)",
        "kr": "Korea Ministry of Food and Drug Safety (MFDS)",
        "br": "Brazil ANVISA",
        "co": "INVIMA (Colombia)",
        "cl": "MINSAL / ISP (Chile)",
        "mx": "COFEPRIS / SSA (Mexico)",
        "ae": "ESMA / Dubai Municipality / ADAFSA (UAE)",
        "sa": "Saudi Food and Drug Authority (SFDA)",
        "za": "Department of Health (South Africa)",
    }
    planned = {
        "my": "Malaysia Ministry of Health",
        "vn": "Vietnam Ministry of Health",
        "id": "Indonesia BPOM",
        "th": "Thailand FDA",
        "gb": "UK Food Standards Agency",
        "ng": "Nigeria NAFDAC",
        "gh": "Ghana FDA",
    }
    return {
        "implemented": implemented,
        "planned_contributions_welcome": planned,
        "contribute": "https://github.com/YOUR_USERNAME/mcp-food-regulatory/blob/main/README.md#contributing",
    }


# ------------------------------------------------------------------ #
#  Entrypoint                                                         #
# ------------------------------------------------------------------ #

def main():
    import argparse
    parser = argparse.ArgumentParser(description="mcp-food-regulatory server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="Transport mode (default: stdio for Claude Desktop)",
    )
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.transport == "streamable-http":
        mcp.run(transport="streamable-http", port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
