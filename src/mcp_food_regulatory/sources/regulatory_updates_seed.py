"""
Seeded regulatory updates -- curated, human-verified changes for key markets.

This file is intentionally NOT automated. Parsing regulatory announcement feeds
is unreliable. A curated log is more trustworthy than a scraped one.

To add an update:
  1. Verify the change against the official instrument (Act, Regulation, Notice).
  2. Add an entry to the appropriate market list below.
  3. Set verified_date to today's date (YYYY-MM).

Update format:
  market          Market enum value
  change_type     One of: new_claim_permitted | claim_prohibited | standard_amended |
                           new_legislation | enforcement_change
  summary         Plain-language description. Start with the impact, then the instrument.
  effective_date  ISO date (YYYY-MM-DD) or partial (YYYY-MM). None if not yet in force.
  instrument      Regulation name, Act, or official document.
  url             Direct link to primary source (official gazette, authority website).
  verified_date   YYYY-MM when this entry was last confirmed correct.
"""

from mcp_food_regulatory.models import Market, RegulatoryUpdate

_UPDATES_US: list[dict] = [
    {
        "market": Market.US,
        "change_type": "new_legislation",
        "summary": (
            "Sesame added as the 9th major food allergen in the United States. "
            "The FASTER Act of 2021 requires sesame to be declared on food labels "
            "effective 1 January 2023. Any food containing sesame as an ingredient "
            "must now declare it by name in the ingredient list or as 'Contains: Sesame'."
        ),
        "effective_date": "2023-01-01",
        "instrument": "Food Allergy Safety, Treatment, Education, and Research (FASTER) Act of 2021",
        "url": "https://www.fda.gov/food/food-labeling-nutrition/sesame-and-food-allergies",
        "verified_date": "2024-01",
    },
    {
        "market": Market.US,
        "change_type": "standard_amended",
        "summary": (
            "FDA updated the Nutrition Facts label format -- new mandatory 'Added Sugars' line "
            "and updated serving sizes to reflect amounts people actually eat. "
            "Large manufacturers required to comply from January 2020; "
            "small manufacturers from January 2021. "
            "Vitamin D and potassium now mandatory; vitamins A and C now voluntary."
        ),
        "effective_date": "2020-01-01",
        "instrument": "21 CFR Parts 101, 104, 105, 107, 201, 606, 610, 801",
        "url": "https://www.fda.gov/food/food-labeling-nutrition/changes-nutrition-facts-label",
        "verified_date": "2024-01",
    },
    {
        "market": Market.US,
        "change_type": "enforcement_change",
        "summary": (
            "FDA issued final guidance removing partially hydrogenated oils (PHOs) from "
            "the Generally Recognized as Safe (GRAS) list, effectively banning artificial "
            "trans fats in food. Compliance deadline was 18 June 2018 for most uses. "
            "Products made before that date could be distributed until 1 January 2020."
        ),
        "effective_date": "2018-06-18",
        "instrument": "FDA Determination re: Partially Hydrogenated Oils (2015, amended 2018)",
        "url": "https://www.fda.gov/food/food-additives-petitions/trans-fat",
        "verified_date": "2024-01",
    },
]

_UPDATES_EU: list[dict] = [
    {
        "market": Market.EU,
        "change_type": "new_legislation",
        "summary": (
            "EU Novel Food Regulation 2015/2283 replaced Regulation (EC) No 258/97. "
            "All novel foods marketed in the EU for the first time after 15 May 1997 "
            "require pre-market authorisation. Key changes: new category for traditional "
            "foods from third countries (traditional food status route), Union list of "
            "authorised novel foods published and maintained online."
        ),
        "effective_date": "2018-01-01",
        "instrument": "Regulation (EU) 2015/2283 on Novel Foods",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32015R2283",
        "verified_date": "2024-01",
    },
    {
        "market": Market.EU,
        "change_type": "standard_amended",
        "summary": (
            "EU health claims on-hold list cleared -- 9 botanical/herbal health claims "
            "that had been 'on hold' since 2010 were reviewed. The European Commission "
            "confirmed they remain on hold pending further evaluation by EFSA. "
            "Products using these claims must display them as-is; no new authorisation "
            "has been granted. This affects claims for saw palmetto, St John's wort, "
            "ginkgo biloba, and similar botanicals."
        ),
        "effective_date": "2022-01-01",
        "instrument": "EC Health Claims Register (botanical claims, on-hold status)",
        "url": "https://food.ec.europa.eu/food-safety/labelling-and-nutrition/nutrition-and-health-claims/eu-register-health-claims_en",
        "verified_date": "2024-01",
    },
    {
        "market": Market.EU,
        "change_type": "enforcement_change",
        "summary": (
            "European Commission published draft Regulation proposing mandatory NutriScore "
            "front-of-pack nutrition labelling across all EU member states. "
            "Currently voluntary; France, Germany, Belgium, Netherlands, Luxembourg, "
            "and Spain have adopted NutriScore voluntarily. Mandatory adoption is under "
            "political negotiation as of 2024 -- no binding decision yet."
        ),
        "effective_date": None,
        "instrument": "EC Farm to Fork Strategy -- FoPNL proposal (2022, pending)",
        "url": "https://food.ec.europa.eu/horizontal-topics/farm-fork-strategy_en",
        "verified_date": "2024-01",
    },
    {
        "market": Market.EU,
        "change_type": "standard_amended",
        "summary": (
            "Titanium dioxide (E171) banned as a food additive in the EU. "
            "The ban followed an EFSA opinion that E171 could not be considered safe "
            "as a food additive due to genotoxicity concerns. "
            "Full compliance required from 7 August 2022."
        ),
        "effective_date": "2022-08-07",
        "instrument": "Commission Regulation (EU) 2022/63 amending Annexes II and III to Regulation (EC) No 1333/2008",
        "url": "https://eur-lex.europa.eu/eli/reg/2022/63/oj",
        "verified_date": "2024-01",
    },
]

_UPDATES_AU: list[dict] = [
    {
        "market": Market.AU,
        "change_type": "new_legislation",
        "summary": (
            "Mandatory pregnancy warning labels for alcoholic beverages in Australia and "
            "New Zealand. All packaged alcohol must display a graphic pregnancy warning "
            "label under FSANZ Standard 2.7.1. "
            "Phase-in period: products made before 31 July 2023 could be sold until "
            "stocks exhausted; full mandatory compliance from 31 July 2023."
        ),
        "effective_date": "2023-07-31",
        "instrument": "FSANZ Standard 2.7.1 -- Labelling of alcoholic beverages (Amendment 195, 2021)",
        "url": "https://www.foodstandards.gov.au/consumer/alcohol/Pages/default.aspx",
        "verified_date": "2024-01",
    },
    {
        "market": Market.AU,
        "change_type": "standard_amended",
        "summary": (
            "FSANZ updated allergen labelling requirements under Standard 1.2.3. "
            "Tree nuts (almonds, Brazil nuts, cashews, hazelnuts, macadamias, pecans, "
            "pine nuts, pistachios, walnuts) must now be declared individually by their "
            "specific common name -- 'tree nuts' as a collective term is no longer sufficient. "
            "Mandatory from 25 February 2024."
        ),
        "effective_date": "2024-02-25",
        "instrument": "FSANZ Standard 1.2.3 -- Mandatory warnings, advisory statements and declarations (Amendment 183)",
        "url": "https://www.foodstandards.gov.au/industry/labelling/allergens/Pages/default.aspx",
        "verified_date": "2024-01",
    },
    {
        "market": Market.AU,
        "change_type": "standard_amended",
        "summary": (
            "FSANZ updated the Health Star Rating system (HSR) calculator to Version 5. "
            "Key change: added a 'capping' mechanism for added sugar -- products with very "
            "high added sugar content cannot score above 2.5 stars regardless of other nutrients. "
            "Applies to the voluntary HSR front-of-pack scheme."
        ),
        "effective_date": "2022-06-01",
        "instrument": "Health Star Rating System -- Calculator Version 5 (2022)",
        "url": "https://www.healthstarrating.gov.au/internet/healthstarrating/publishing.nsf/content/home",
        "verified_date": "2024-01",
    },
]

_UPDATES_JP: list[dict] = [
    {
        "market": Market.JP,
        "change_type": "standard_amended",
        "summary": (
            "Japan updated the mandatory allergen list to add walnut (クルミ). "
            "Walnut was upgraded from 'recommended' to 'mandatory' declaration status "
            "effective 1 September 2023. Japan now has 8 mandatory allergens: "
            "egg, milk, wheat, buckwheat, peanut, shrimp, crab, and walnut."
        ),
        "effective_date": "2023-09-01",
        "instrument": "Food Labelling Standards -- Cabinet Office Order No. 10, Amendment (2022)",
        "url": "https://www.caa.go.jp/policies/policy/food_labeling/food_labeling_act/assets/food_labeling_cms101_220614_01.pdf",
        "verified_date": "2024-01",
    },
    {
        "market": Market.JP,
        "change_type": "standard_amended",
        "summary": (
            "Japan's Food with Function Claims (FFC / 機能性表示食品) system expanded -- "
            "CAA updated guidance to allow certain processed foods and supplements to "
            "file function claims based on systematic review evidence. "
            "The notification system now covers a broader range of health-related function claims "
            "than the original 2015 framework."
        ),
        "effective_date": "2019-04-01",
        "instrument": "CAA Guidelines for Foods with Function Claims (revised 2019)",
        "url": "https://www.caa.go.jp/policies/policy/food_labeling/foods_with_function_claims/",
        "verified_date": "2024-01",
    },
]

_UPDATES_CA: list[dict] = [
    {
        "market": Market.CA,
        "change_type": "standard_amended",
        "summary": (
            "Health Canada updated the Nutrition Facts Table format for all prepackaged foods. "
            "Key changes: new mandatory 'Added Sugars' line, revised Daily Values (DVs) based "
            "on updated dietary reference intakes, new serving sizes for certain categories, "
            "and simplified format for small packages. "
            "Large manufacturers from 14 December 2021; small manufacturers from 14 December 2022."
        ),
        "effective_date": "2021-12-14",
        "instrument": "Food and Drug Regulations -- Part B Division 1 (Amendments, 2016 SOR/2016-305)",
        "url": "https://www.canada.ca/en/health-canada/services/food-nutrition/food-labelling/nutrition-labelling/nutrition-facts-table.html",
        "verified_date": "2024-01",
    },
    {
        "market": Market.CA,
        "change_type": "new_legislation",
        "summary": (
            "Canada added sesame to the priority food allergen list under the Food and Drug "
            "Regulations. Sesame became a Priority Food Allergen effective 16 August 2021, "
            "requiring mandatory declaration by common name in the ingredient list or "
            "in a 'Contains' statement. This aligns Canada with the US FASTER Act."
        ),
        "effective_date": "2021-08-16",
        "instrument": "Food and Drug Regulations -- Priority Food Allergen labelling (SOR/2021-143)",
        "url": "https://www.canada.ca/en/health-canada/services/food-nutrition/food-labelling/labelling-changes-food-allergens-gluten-sulphites.html",
        "verified_date": "2024-01",
    },
]

# Map market to its update list for easy lookup
_ALL_UPDATES: dict[Market, list[dict]] = {
    Market.US: _UPDATES_US,
    Market.EU: _UPDATES_EU,
    Market.AU: _UPDATES_AU,
    Market.JP: _UPDATES_JP,
    Market.CA: _UPDATES_CA,
}


def get_seeded_updates(
    market: Market,
    since_date: str | None = None,
) -> list[RegulatoryUpdate]:
    """
    Return seeded regulatory updates for a market, optionally filtered by date.

    since_date: ISO date string YYYY-MM-DD or YYYY-MM. Only returns updates with
                effective_date >= since_date. If since_date is None, returns all.
    """
    raw = _ALL_UPDATES.get(market, [])
    results = []
    for u in raw:
        eff = u.get("effective_date")
        if since_date and eff:
            # Truncate both to the length of the shorter for comparison
            compare_eff = eff[: len(since_date)]
            compare_since = since_date[: len(eff)]
            if compare_eff < compare_since:
                continue
        results.append(RegulatoryUpdate(
            market=u["market"],
            change_type=u["change_type"],
            summary=u["summary"],
            effective_date=eff,
            instrument=u["instrument"],
            url=u.get("url"),
            data_confidence="seeded",
            verified_date=u.get("verified_date"),
        ))
    return results
