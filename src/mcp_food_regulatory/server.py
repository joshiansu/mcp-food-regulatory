"""
mcp-food-regulatory: MCP server for food regulatory database access.

Exposes 6 tools to AI agents:
  - search_health_claims
  - get_standard
  - search_standards
  - get_additive_status
  - compare_markets
  - get_market_overview

Run with:
  uv run mcp-food-regulatory                          # stdio (Claude Desktop)
  uv run mcp-food-regulatory --transport http         # HTTP (agents/remote)
"""

from __future__ import annotations
from typing import Optional
import httpx
from fastmcp import FastMCP

from mcp_food_regulatory.models import Market
from mcp_food_regulatory.sources.codex import CodexSource
from mcp_food_regulatory.sources.eu import EUSource
from mcp_food_regulatory.sources.ph_fda import PhFDASource

# ------------------------------------------------------------------ #
#  Server init                                                        #
# ------------------------------------------------------------------ #

mcp = FastMCP(
    "food-regulatory",
    instructions=(
        "This server provides access to food regulatory databases across global markets. "
        "Use it to check health claim status, look up regulatory standards, compare "
        "claim permissions across markets, and get market regulatory overviews. "
        "Supported markets: codex (Codex Alimentarius), eu (European Union), ph (Philippines FDA). "
        "More ASEAN markets coming — see README for contribution guide."
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

    for market_str in markets:
        try:
            market = Market(market_str.lower())
        except ValueError:
            errors[market_str] = f"Unknown market '{market_str}'. Available: {', '.join(m.value for m in SOURCES)}"
            continue

        try:
            source = _get_source(market)
            claims = await source.search_health_claims(ingredient, claim_type)
            results[market_str] = [c.model_dump() for c in claims]
        except NotImplementedError as e:
            errors[market_str] = str(e)
        except Exception as e:
            errors[market_str] = f"Error fetching data: {e}"

    return {
        "ingredient": ingredient,
        "claim_type_filter": claim_type,
        "results": results,
        "errors": errors if errors else None,
    }


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
        return {"found": True, **standard.model_dump()}
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

    for market_str in markets:
        try:
            market = Market(market_str.lower())
            source = _get_source(market)
            standards = await source.search_standards(query)
            results[market_str] = [s.model_dump() for s in standards]
        except (ValueError, NotImplementedError) as e:
            results[market_str] = {"error": str(e)}
        except Exception as e:
            results[market_str] = {"error": f"Search failed: {e}"}

    return {"query": query, "results": results}


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

    return {
        "ingredient": ingredient,
        "claim_type": claim_type,
        "comparison": [r.model_dump() for r in all_results],
        "summary": " | ".join(summary_lines) or "No data found.",
        "errors": errors if errors else None,
    }


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
        return overview.model_dump()
    except ValueError:
        return {
            "error": f"Unknown market '{market}'.",
            "available_markets": [m.value for m in SOURCES],
        }
    except Exception as e:
        return {"error": str(e)}


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
    }
    planned = {
        "au": "Food Standards Australia New Zealand (FSANZ)",
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
