# Reconciliation Report

## Summary

- Source rows read: 323
- CRM rows: 100
- Vendor rows: 118
- Web rows: 105
- Golden companies produced: 144
- Quarantined rows: 3
- Companies appearing in 1 source: 34
- Companies appearing in 2 sources: 44
- Companies appearing in 3 sources: 66
- Field conflicts detected: 231

## Conflict Breakdown

- employees: 108
- industry: 20
- name: 103

## Resolution Reasons

- no_available_value: 142
- selected_by_policy_preference_crm>vendor>web: 88
- selected_by_policy_preference_crm>web>vendor: 70
- selected_by_policy_preference_vendor>crm>web: 617
- value_agreed_by_multiple_sources: 379

## Quarantine Reasons

- junk_web_page_without_company_identity: 1
- missing_name_and_domain: 2

## Policy Summary

- Exact normalized domain matches are treated as strong matches.
- Fuzzy company-name matches require very high similarity and location support.
- Vendor is preferred for canonical firmographics: name, domain, employees, industry, revenue, founded year.
- CRM is preferred for contact-oriented fields such as email and city.
- Web is used as a fallback and freshness signal, but weak web rows are quarantined.
- Agreement by multiple sources can override normal source preference.

## Output Notes

- `golden_records.json` is the authoritative output because it includes field-level provenance.
- `golden_records.csv` is a flat convenience export for quick review.
- `quarantine.csv` lists rows excluded from golden records and the reason.

## Risk Posture

The matcher favors precision over recall. A missed match is easier to review later, but a false merge corrupts a golden record. For that reason, low-signal rows are kept separate or quarantined.
