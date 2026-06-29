# Architecture

## Overview

This project builds one golden company record from three messy input sources: CRM, vendor, and web directory data. The pipeline is deterministic and idempotent: it reads the CSV files, normalizes fields, matches records across sources, resolves conflicts, quarantines unusable rows, and writes final outputs.

The main design goal is explainability. Every selected field in `golden_records.json` includes the winning value, source, source row ID, and reason.

## Matching Approach

The matcher is intentionally conservative because a false merge is worse than a missed match.

Before matching, the pipeline normalizes key fields:

- company names are lowercased, punctuation is removed, and legal suffixes such as `Inc`, `Ltd`, `LLC`, `Corp`, `Co`, and `GmbH` are removed
- URLs are normalized into bare domains
- country aliases such as `DE`, `Deutschland`, `CAN`, `UK`, and `Bharat` are mapped to canonical country names
- industries and web categories are mapped into a shared taxonomy
- invalid domains, including numeric TLDs such as `.co1` or `.co3`, are rejected

Matching happens in two main ways:

1. **Exact domain match**
   If records share the same normalized valid domain, they are treated as the same company.

2. **Fuzzy name match with location support**
   If domain is missing, records may match only when company-name similarity is very high and country or city supports the match.

The pipeline avoids merging records when domains conflict, name similarity is weak, or location evidence does not support the match. This favors precision over recall.

## Conflict-Resolution Policy

The resolver uses a field-specific trust policy instead of always choosing the newest value.

Vendor is preferred for structured firmographics because it has cleaner canonical company data:

- company name
- domain
- employees
- industry
- revenue band
- founded year
- country

CRM is preferred for contact-oriented fields because it contains operational contact data:

- email
- city

Web data is used as fallback and freshness support. It is useful, but it is not always trusted over vendor or CRM because scraped data can be noisy, coarse, or wrong.

If two or more sources agree on a field value, that agreement can override normal source preference. If no source has a usable value, the field is left blank with the reason `no_available_value`.

## Provenance

The authoritative output is:

```text
output/golden_records.json
