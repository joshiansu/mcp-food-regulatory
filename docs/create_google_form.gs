/**
 * Paste this entire file into script.google.com → New project → Run → createForm
 * The shareable link is logged in the Execution log.
 */
function createForm() {
  var form = FormApp.create('Regulatory Generalist Input -- mcp-food-regulatory');
  form.setDescription(
    'Your input shapes which domains get built first and how the tool is structured. ' +
    'Answers can be as brief or detailed as you like -- even partial answers help.'
  );
  form.setCollectEmail(false);
  form.setAllowResponseEdits(true);

  // ── Section 1: Work context ──────────────────────────────────────────────
  form.addSectionHeaderItem()
    .setTitle('Section 1 -- Your work context');

  form.addMultipleChoiceItem()
    .setTitle('Q1. What is your primary role?')
    .setChoiceValues([
      'In-house regulatory affairs at a food company',
      'Regulatory consultant / independent advisor',
      'Regulatory affairs at an ingredient supplier',
      'Other'
    ])
    .showOtherOption(true)
    .setRequired(true);

  form.addCheckboxItem()
    .setTitle('Q2. What product categories do you work with most? (tick all that apply)')
    .setChoiceValues([
      'Beverages (carbonated, juice, functional drinks, plant-based)',
      'Supplements / nutraceuticals / health foods',
      'Dairy and dairy alternatives',
      'Snacks (confectionery, savoury, cereal bars)',
      'Infant formula / baby food',
      'Bakery / cereals',
      'Meat and meat alternatives',
      'Condiments / sauces'
    ])
    .showOtherOption(true)
    .setRequired(true);

  form.addParagraphTextItem()
    .setTitle('Q3. Which markets do you encounter most frequently? (list your top 5 if possible)')
    .setHelpText('e.g. EU, US, Australia, India, China')
    .setRequired(true);

  // ── Section 2: Product classification ───────────────────────────────────
  form.addSectionHeaderItem()
    .setTitle('Section 2 -- Product classification');

  form.addMultipleChoiceItem()
    .setTitle('Q4. When you assess a new product, do you already know its regulatory category going in, or does figuring out the classification take significant time?')
    .setHelpText('e.g. "Is this a food supplement or a novel food in the EU?"')
    .setChoiceValues([
      'I always know the category before I start',
      'I usually know but sometimes need to verify',
      'Classification takes significant time -- it\'s often the hardest question',
      'It depends on the market'
    ])
    .setRequired(true);

  form.addParagraphTextItem()
    .setTitle('Q5. Which product-category situations cause the most confusion or risk in your work?')
    .setHelpText(
      'e.g. "Is this a food supplement or a novel food in the EU?", ' +
      '"Does this fall under DSHEA or conventional food in the US?", ' +
      '"Is this FOSHU-eligible in Japan?"'
    )
    .setRequired(false);

  // ── Section 3: Health and nutrient content claims ────────────────────────
  form.addSectionHeaderItem()
    .setTitle('Section 3 -- Health and nutrient content claims');

  form.addCheckboxItem()
    .setTitle('Q6. When you check claims, what is the typical starting question? (tick all that apply)')
    .setChoiceValues([
      'Is this claim type (health / nutrition) permitted in this market at all?',
      'What nutrient level does my product need to qualify for this claim?',
      'What exact wording is permitted / required?',
      'What substantiation does the regulator require?'
    ])
    .showOtherOption(true)
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('Q7. For nutrient content claims, do you typically work from the nutrient upward or the claim downward?')
    .setChoiceValues([
      'Nutrient up -- my product has X% protein, what can I say?',
      'Claim down -- I want to say "high in protein", what does the product need?',
      'Both equally'
    ])
    .setRequired(true);

  form.addParagraphTextItem()
    .setTitle('Q8. Which nutrients or claim categories create the most complexity for you across markets?')
    .setHelpText('e.g. protein, omega-3, probiotics, polyphenols, vitamins/minerals, sugar-free, low-sodium')
    .setRequired(false);

  // ── Section 4: FOPNL ─────────────────────────────────────────────────────
  form.addSectionHeaderItem()
    .setTitle('Section 4 -- Front of pack nutritional labelling (FOPNL)');

  form.addCheckboxItem()
    .setTitle('Q9. Which FOPNL schemes do you encounter in your work? (tick all that apply)')
    .setChoiceValues([
      'NutriScore (EU / France / Germany / Belgium / Netherlands / Spain / Switzerland)',
      'Multiple Traffic Light / GDA (UK)',
      'Health Star Rating (Australia / New Zealand)',
      'Octagonal warning labels (Chile / Mexico / Colombia / Peru / Ecuador)',
      'Lupa warnings (Brazil)',
      'Warning labels (India -- FSSAI draft)',
      'Healthier Choice logo (Thailand / Singapore)',
      "I don't work with FOPNL markets currently"
    ])
    .showOtherOption(true)
    .setRequired(true);

  form.addParagraphTextItem()
    .setTitle('Q10. Has FOPNL ever blocked or changed a claims decision for you? If yes, which market and what was the situation?')
    .setRequired(false);

  form.addMultipleChoiceItem()
    .setTitle('Q11. Do you need the tool to calculate whether a specific product would receive a warning label (given nutrition per 100g), or just tell you the scheme and thresholds?')
    .setChoiceValues([
      'Just the framework -- I can do the maths myself',
      'I need it to calculate the result given product nutrition data',
      'Both'
    ])
    .setRequired(true);

  // ── Section 5: SSB tax and sodium tax ───────────────────────────────────
  form.addSectionHeaderItem()
    .setTitle('Section 5 -- SSB tax and sodium tax');

  form.addCheckboxItem()
    .setTitle('Q12. Does SSB tax or sodium tax come up in your regulatory work? (tick all that apply)')
    .setChoiceValues([
      'Yes -- clients ask me to advise on which tax tier their product falls into',
      'Yes -- reformulation decisions (to get under a tax threshold) affect my label review work',
      'Occasionally -- I need to know if a tax exists in a market but not the detailed rates',
      'No -- this is handled by a different team (finance / commercial) and does not reach me',
      'Not yet, but it is growing'
    ])
    .setRequired(true);

  form.addParagraphTextItem()
    .setTitle('Q13. If you do work with SSB/sodium tax, which markets? Do you need it to map sugar content to a specific levy rate, or just confirm whether a levy exists?')
    .setRequired(false);

  // ── Section 6: Workflow and format ───────────────────────────────────────
  form.addSectionHeaderItem()
    .setTitle('Section 6 -- Workflow and format');

  form.addCheckboxItem()
    .setTitle('Q14. At what stage in product development do you typically check regulatory compliance? (tick all that apply)')
    .setChoiceValues([
      'Early concept / ideation (before formulation is fixed)',
      'Formulation stage (when NPD is testing recipes)',
      'Pre-launch (product is finalised, checking artwork and claims)',
      'Post-launch / continuous monitoring (watching for regulatory changes)'
    ])
    .setRequired(true);

  form.addCheckboxItem()
    .setTitle('Q15. When you use a tool like this, what output format is most useful? (tick all that apply)')
    .setChoiceValues([
      'Structured verdict with pass / fail / warning per domain',
      'Plain-language summary I can paste into a client memo',
      'Regulation references I can check myself',
      'Side-by-side market comparison table'
    ])
    .showOtherOption(true)
    .setRequired(true);

  form.addParagraphTextItem()
    .setTitle('Q16. What is the single biggest time sink in your regulatory review work today that this tool could realistically help with?')
    .setRequired(true);

  // ── Section 7: Open questions ─────────────────────────────────────────────
  form.addSectionHeaderItem()
    .setTitle('Section 7 -- Open questions');

  form.addParagraphTextItem()
    .setTitle('Q17. Are there regulatory domains not mentioned above that you encounter regularly?')
    .setHelpText(
      'e.g. novel food approval tracking, organic certification, country-of-origin rules, ' +
      'packaging migration, halal/kosher interface with claims'
    )
    .setRequired(false);

  form.addParagraphTextItem()
    .setTitle('Q18. Are there specific markets where regulatory information is particularly hard to find or unreliable?')
    .setRequired(false);

  form.addParagraphTextItem()
    .setTitle('Q19. What would make you trust a regulatory tool\'s answer enough to use it as a starting point in a client memo?')
    .setHelpText(
      'e.g. citation to the specific regulation, a date it was last verified, ' +
      'a confidence level, links to the official source'
    )
    .setRequired(false);

  // ── Publish and log links ─────────────────────────────────────────────────
  var publishedUrl = form.getPublishedUrl();
  var editUrl      = form.getEditUrl();

  Logger.log('=== FORM CREATED ===');
  Logger.log('Shareable (fill-in) link: ' + publishedUrl);
  Logger.log('Edit link (keep private): ' + editUrl);

  // Also shows as a popup so you don't have to open the log
  var ui = SpreadsheetApp.getUi ? SpreadsheetApp.getUi() : null;
  if (!ui) {
    // Running from script.google.com directly -- log is sufficient
    Logger.log('Done. Copy the shareable link above.');
  }
}
