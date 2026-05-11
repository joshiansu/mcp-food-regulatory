"""
Shared Pydantic models for regulatory data across all markets.
These are the canonical shapes returned by every tool in the MCP server.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ClaimStatus(str, Enum):
    PERMITTED = "permitted"
    PROHIBITED = "prohibited"
    PENDING = "pending"           # Under review / not yet decided
    NOT_DEFINED = "not_defined"   # Market has no specific provision
    CONDITIONAL = "conditional"   # Permitted with conditions


class Market(str, Enum):
    CODEX = "codex"
    EU = "eu"
    AU = "au"       # Australia / FSANZ
    NZ = "nz"       # New Zealand / FSANZ
    PH = "ph"       # Philippines
    MY = "my"       # Malaysia
    VN = "vn"       # Vietnam
    ID = "id"       # Indonesia
    TH = "th"       # Thailand
    GB = "gb"       # Great Britain (post-Brexit)
    NG = "ng"       # Nigeria
    GH = "gh"       # Ghana


class RegulatoryBasis(BaseModel):
    """The legal/regulatory instrument underlying a determination."""
    instrument: str = Field(description="Name or code of the regulation, e.g. 'EC 1924/2006'")
    article: Optional[str] = Field(None, description="Specific article or section, e.g. 'Article 13(1)'")
    url: Optional[str] = Field(None, description="Direct URL to the instrument")
    notes: Optional[str] = Field(None, description="Free-text notes on applicability")


class ClaimResult(BaseModel):
    """Status of a specific claim for a specific ingredient in a specific market."""
    market: Market
    ingredient: str
    claim_type: str
    status: ClaimStatus
    conditions: Optional[str] = Field(None, description="Conditions or restrictions on use")
    basis: Optional[RegulatoryBasis] = Field(None, description="Legal basis for this determination")
    efsa_opinion: Optional[str] = Field(None, description="EFSA or equivalent opinion reference (EU only)")
    last_updated: Optional[str] = Field(None, description="ISO date of last known update")
    source_url: Optional[str] = Field(None, description="Direct source URL")


class Standard(BaseModel):
    """A regulatory standard document."""
    standard_id: str = Field(description="Official identifier, e.g. 'CXG 2-1985' or 'EC 1924/2006'")
    market: Market
    title: str
    category: Optional[str] = Field(None, description="Category e.g. 'guideline', 'standard', 'regulation'")
    adopted: Optional[str] = Field(None, description="Year or date first adopted")
    last_amended: Optional[str] = Field(None, description="Date of most recent amendment")
    summary: Optional[str] = Field(None, description="Brief summary of scope and content")
    full_text_url: Optional[str] = Field(None)
    key_definitions: Optional[dict[str, str]] = Field(
        None, description="Important definitions extracted from the standard"
    )


class AdditiveStatus(BaseModel):
    """Permitted status of a food additive in a market."""
    market: Market
    additive_name: str
    ins_number: Optional[str] = Field(None, description="INS/E-number identifier")
    food_category: str
    permitted: bool
    max_level: Optional[str] = Field(None, description="Maximum permitted level e.g. '500 mg/kg'")
    conditions: Optional[str] = None
    basis: Optional[RegulatoryBasis] = None


class MarketComparison(BaseModel):
    """Side-by-side comparison of claim/ingredient status across multiple markets."""
    ingredient: str
    claim_type: str
    results: list[ClaimResult]
    summary: str = Field(description="Plain-language summary of key differences")


class MarketOverview(BaseModel):
    """High-level overview of a market's food regulatory framework."""
    market: Market
    authority_name: str = Field(description="Name of the primary regulatory authority")
    authority_url: Optional[str] = None
    key_legislation: list[str] = Field(description="List of primary legislation names")
    health_claims_framework: Optional[str] = Field(
        None, description="Summary of how health claims are handled"
    )
    notes: Optional[str] = None
