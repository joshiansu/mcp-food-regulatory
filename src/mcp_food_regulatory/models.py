"""
Shared Pydantic models for regulatory data across all markets.
These are the canonical shapes returned by every tool in the MCP server.
"""

from __future__ import annotations
from enum import Enum
from typing import Literal, Optional
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
    US = "us"       # United States
    JP = "jp"       # Japan
    CA = "ca"       # Canada
    PH = "ph"       # Philippines
    MY = "my"       # Malaysia
    VN = "vn"       # Vietnam
    ID = "id"       # Indonesia
    TH = "th"       # Thailand
    GB = "gb"       # Great Britain (post-Brexit)
    NG = "ng"       # Nigeria
    GH = "gh"       # Ghana
    IN = "in"       # India / FSSAI
    CN = "cn"       # China / NHC + SAMR
    KR = "kr"       # South Korea / MFDS
    BR = "br"       # Brazil / ANVISA
    CO = "co"       # Colombia / INVIMA
    CL = "cl"       # Chile / MINSAL
    MX = "mx"       # Mexico / COFEPRIS
    AE = "ae"       # UAE / ESMA
    SA = "sa"       # Saudi Arabia / SFDA
    ZA = "za"       # South Africa / DoH
    PK = "pk"       # Pakistan / PFA + PSQCA
    BD = "bd"       # Bangladesh / BFSA
    LK = "lk"       # Sri Lanka / FCAU + SLSI
    NP = "np"       # Nepal / DFTQC
    BT = "bt"       # Bhutan / BFDRA
    MV = "mv"       # Maldives / MFDA


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
    data_confidence: Literal["seeded", "live", "official_download"] = Field(
        "seeded", description="Source quality: seeded=hardcoded offline data, live=fetched at call time, official_download=from official bulk download"
    )
    verified_date: Optional[str] = Field(None, description="ISO date this data was last verified against source")
    staleness_warning: bool = Field(True, description="True if data may be outdated and should be cross-checked")


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
    data_confidence: Literal["seeded", "live", "official_download"] = Field(
        "seeded", description="Source quality: seeded=hardcoded offline data, live=fetched at call time, official_download=from official bulk download"
    )
    verified_date: Optional[str] = Field(None, description="ISO date this data was last verified against source")
    staleness_warning: bool = Field(True, description="True if data may be outdated and should be cross-checked")


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


class RegulatoryUpdate(BaseModel):
    """A known regulatory change in a market -- new legislation, amended standards, enforcement shifts."""
    market: Market
    change_type: Literal[
        "new_claim_permitted",
        "claim_prohibited",
        "standard_amended",
        "new_legislation",
        "enforcement_change",
    ]
    summary: str = Field(description="Plain-language description of what changed")
    effective_date: Optional[str] = Field(None, description="ISO date the change took effect")
    instrument: str = Field(description="Regulation, Act, or official document name")
    url: Optional[str] = Field(None, description="Direct link to the instrument or announcement")
    data_confidence: Literal["seeded", "live", "official_download"] = Field("seeded")
    verified_date: Optional[str] = Field(None, description="ISO date this entry was last verified")


class NutrientClaimThreshold(BaseModel):
    """Numeric threshold required to make a nutrient content claim in a market."""
    market: Market
    nutrient: str = Field(description="Nutrient name, e.g. 'protein', 'dietary fibre', 'fat', 'sodium'")
    claim_type: str = Field(description="Claim category: 'source_of', 'high_in', 'low', 'free', 'reduced', 'no_added'")
    claim_wording: str = Field(description="Exact permitted wording on pack")
    threshold_value: str = Field(description="Qualifying threshold, e.g. '≥3g/100g or ≥1.5g/100kcal'")
    threshold_basis: str = Field(description="Basis for measurement: 'per 100g', 'per 100ml', 'per serving', 'per 100kcal'")
    reference_value: Optional[str] = Field(None, description="NRV or DV reference used, where applicable")
    conditions: Optional[str] = Field(None, description="Additional conditions or restrictions")
    governing_instrument: str = Field(description="Regulation or standard, e.g. 'EC 1924/2006 Annex'")
    data_confidence: Literal["seeded", "live", "official_download"] = Field(
        "seeded", description="Source quality of this threshold entry"
    )
    verified_date: Optional[str] = Field(None, description="ISO date this threshold was last verified")
