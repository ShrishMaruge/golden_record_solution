# AI Usage Log

## 1. Where did you use AI?

I used AI to help understand the task brief, design the project structure, and draft the first version of the Python pipeline.

The AI helped with:

- summarizing the DOCX task requirements
- identifying the required deliverables
- designing the project layout
- drafting normalization functions for names, domains, countries, industries, and employee-size bands
- drafting the entity-matching strategy
- drafting the field-level conflict-resolution policy
- drafting the JSON provenance structure
- drafting the reconciliation report format
- reviewing generated outputs for obvious quality issues

I did not use AI to hand-edit the source data. All cleaning and reconciliation are done through code.

## 2. What did I NOT understand at first, and how did I resolve it?

At first, I was unsure whether the newest source should always win when sources disagreed.

I resolved this by separating freshness from trustworthiness. The web source is often freshest, but it is also coarse and can contain scraped errors. The vendor source is more trustworthy for structured firmographics such as domain, employees, industry, revenue band, and founded year. The CRM source is more useful for contact-oriented fields such as email and city.

I also initially underestimated how important quarantine would be. After reviewing the generated output, I found that a junk web row such as `Untitled Page` could become a golden record if the quarantine rules were too weak. I added explicit junk-page quarantine logic.

## 3. One decision I made against what the AI suggested

The initial AI-generated version allowed some questionable domains to survive into the final output, such as domains with numeric TLDs like `.co1`, `.co2`, or `.co3`.

Instead of trusting those domains, I changed the policy to reject invalid domains and leave the final domain blank when no valid domain is available. This is more conservative and better aligned with the task brief because publishing a bad domain as a trusted golden-record value is worse than leaving the field blank.

I also chose conservative matching thresholds rather than aggressive fuzzy matching. This may miss some true matches, but it reduces the risk of merging two different companies.

## 4. If your reviewer asked "why this approach?" about the hardest part of your
##    solution — your conflict-resolution policy — what would you say, in your own words?

I would say that I used a field-specific trust policy rather than one global rule.

The vendor source is preferred for canonical firmographics because it has cleaner domains and structured company attributes. The CRM source is preferred for contact fields because that is where contact information exists and is most likely to be operationally useful. The web source is used as a fallback and freshness signal, but I do not let freshness automatically override trust because scraped data can be noisy.

For matching, I favored precision over recall. A missed match creates two records that can be reviewed later, but a false merge corrupts the golden record. That is why exact domain matches are treated as strong evidence, while fuzzy name matches require very high similarity and location support.

Every selected field includes provenance, so the final output is not just a merged dataset; it is an auditable set of decisions.