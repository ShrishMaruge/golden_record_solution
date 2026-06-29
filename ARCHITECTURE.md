# Golden Record Pipeline Architecture

## Overview

This project builds **golden company records** from three messy and conflicting data sources:

* CRM Export
* Vendor Feed
* Web Directory Scrape

The objective is to produce **one trusted record per real company** while preserving **field-level provenance** for every selected value.

The solution is implemented as a **deterministic Python batch pipeline** that:

1. Reads input CSV files
2. Normalizes data
3. Quarantines unusable rows
4. Matches records across sources
5. Resolves field conflicts
6. Produces authoritative golden records with complete provenance

---

# Design Goals

The pipeline is designed around five core principles:

1. **Reproducibility**
   The same inputs always produce the same outputs.

2. **Explainability**
   Every selected field records why it was chosen and where it came from.

3. **Conservative Matching**
   Avoid false merges even if some true matches are missed.

4. **Field-Level Trust**
   Different sources are trusted for different fields.

5. **Idempotency**
   Running the pipeline multiple times safely rewrites outputs without duplicates.

---

# Input Sources

## 1. CRM Source

**File**

```text
data/source1_crm.csv
```

### Contains

* Company Name
* Website
* Headcount
* Industry
* Country
* City
* Primary Contact Email
* Last Updated Date

### Strengths

* Contact email
* City
* Human-maintained relationship data

### Risks

* Messy company names
* Missing websites
* Older update dates
* Inconsistent country names

---

## 2. Vendor Source

**File**

```text
data/source2_vendor.csv
```

### Contains

* Legal Company Name
* Domain
* Employee Count
* Industry
* Revenue Band
* Founded Year
* Country
* As-of Date

### Strengths

* Canonical company name
* Domain
* Employee count
* Industry
* Revenue information
* Founded year
* Country

### Risks

* Sparse contact information
* Vendor-specific industry taxonomy
* Occasional incorrect values

---

## 3. Web Source

**File**

```text
data/source3_web.csv
```

### Contains

* Company
* URL
* Category
* Approximate Size
* Location
* Crawled Date

### Strengths

* Fresh information
* Backup company/location data
* Extra matching evidence

### Risks

* Employee-size bands instead of exact counts
* Messy URLs
* Free-text categories
* Junk pages

---

# Pipeline Flow

The pipeline executes in the following order:

```text
Read CSV Files
        ↓
Normalize Fields
        ↓
Quarantine Invalid Rows
        ↓
Cluster Matching Records
        ↓
Resolve Field Conflicts
        ↓
Write Golden Records
        ↓
Write Quarantine File
        ↓
Write Reconciliation Report
```

---

# Normalization

Normalization converts inconsistent values into comparable formats.

The following fields are normalized:

* Domains and URLs
* Company names
* Countries
* Cities
* Industries
* Employee-size bands
* Blank values

---

## Domain Normalization

URLs are converted into clean lowercase domains.

### Examples

```text
https://www.example.com/about
→ example.com

HTTP://EXAMPLE.COM
→ example.com

example.com/page
→ example.com
```

Invalid domains are rejected.

Examples:

```text
example.co1
example.co2
example.co3
```

These are **never promoted** into the golden record.

---

## Company Name Normalization

Company names are standardized by:

* Lowercasing
* Removing punctuation
* Removing legal suffixes

### Removed Suffixes

* Inc
* Ltd
* LLC
* Corp
* Co
* GmbH
* Limited

### Example

```text
Birch Solutions Inc.
Birch Solutions Co.
birch solutions

↓

birch solutions
```

---

## Country Normalization

Aliases are mapped into canonical country names.

| Alias       | Canonical Name |
| ----------- | -------------- |
| DE          | Germany        |
| Deutschland | Germany        |
| CAN         | Canada         |
| CA          | Canada         |
| UK          | United Kingdom |
| Britain     | United Kingdom |
| Bharat      | India          |

---

## Industry Normalization

Different source taxonomies are mapped into one common taxonomy.

| Original           | Canonical                |
| ------------------ | ------------------------ |
| Fintech            | Financial Services       |
| Finance / Payments | Financial Services       |
| Health             | Healthcare Technology    |
| Cybersecurity      | Information Security     |
| Shipping           | Logistics & Supply Chain |
| EdTech             | Education Technology     |

---

# Quarantine Policy

Rows are excluded when they cannot safely represent a company.

### Current Reasons

* `missing_name_and_domain`
* `junk_web_page_without_company_identity`

A row is quarantined if:

* It has neither a usable company name nor domain.
* It represents a junk page (e.g., *Untitled Page*).

This prevents invalid data from contaminating the final output.

---

# Matching Strategy

The matcher prioritizes **precision over recall**.

A false merge is considered more harmful than a missed match.

---

## Rule 1 — Exact Domain Match

If two records share the same normalized domain, they belong to the same company.

Example:

```text
CRM:
birchsolutions.com

Vendor:
birchsolutions.com

Web:
birchsolutions.com/about

↓

One Company
```

---

## Rule 2 — Fuzzy Name + Location

If the domain is unavailable, records match when:

* Company names are highly similar
* Country or city supports the match

---

## Rule 3 — Very High Name Similarity

If location information is missing:

* Extremely high name similarity may be accepted
* Only when no conflicting location exists

---

## Non-Matches

Records are **not merged** when:

* Domains differ
* Name similarity is below threshold
* Location conflicts exist

---

# Conflict Resolution

Conflicts are resolved using deterministic rules.

---

## Source Preference

### Vendor (Preferred)

Used for firmographic data:

* Company Name
* Domain
* Industry
* Employees
* Revenue Band
* Founded Year
* Country

---

### CRM (Preferred)

Used for contact information:

* Email
* City

---

### Web

Used only as fallback when stronger sources do not provide usable values.

---

## Agreement Rule

If multiple sources agree on the same value, agreement can override normal source preference.

Example reason:

```text
value_agreed_by_multiple_sources
```

---

## Missing Values

If no usable value exists:

```text
Reason:
no_available_value
```

---

# Provenance Model

The authoritative output file is:

```text
output/golden_records.json
```

Each field stores:

```json
{
  "value": "...",
  "source": "...",
  "source_id": "...",
  "reason": "..."
}
```

Example:

```json
"employees": {
  "value": "3200",
  "source": "vendor",
  "source_id": "V5059",
  "reason": "selected_by_policy_preference_vendor>crm>web"
}
```

Every selected value is fully traceable.

---

# Output Files

## 1. Golden Records

```text
output/golden_records.json
```

Authoritative output with complete provenance.

---

## 2. CSV Export

```text
output/golden_records.csv
```

Spreadsheet-friendly export.

Does **not** contain full provenance.

---

## 3. Quarantine

```text
output/quarantine.csv
```

Contains excluded rows and quarantine reasons.

---

## 4. Reconciliation Report

```text
output/reconciliation_report.md
```

Includes:

* Source row counts
* Golden record count
* Quarantine count
* Source coverage
* Conflict summary
* Resolution reasons
* Policy summary

---

# Idempotency

Running:

```bash
python -m golden_record
```

multiple times:

* Rewrites outputs
* Produces identical results
* Never duplicates records
* Never mutates input files

---

# Current Run Summary

| Metric                 | Value |
| ---------------------- | ----: |
| Source Rows Read       |   323 |
| Golden Companies       |   144 |
| Quarantined Rows       |     3 |
| Companies in 1 Source  |    34 |
| Companies in 2 Sources |    44 |
| Companies in 3 Sources |    66 |
| Field Conflicts        |   231 |

---

# Tradeoffs

## Precision over Recall

Some genuine matches may be missed when evidence is weak.

This is intentional because:

* False merges permanently corrupt golden records.
* Missed matches can be reviewed later.

---

## Rule-Based Instead of Machine Learning

### Advantages

* Deterministic
* Easy to explain
* Easy to debug
* No training data required
* Fully reproducible

### Disadvantages

* Less flexible than ML-based entity resolution
* Threshold tuning may be required for larger datasets

---

## JSON as the Source of Truth

Although CSV files are easier to inspect, they cannot represent complete field-level provenance.

Therefore:

```text
golden_records.json
```

is considered the authoritative output.

---

# Future Improvements

Given additional development time, the pipeline could be enhanced with:

* Unit tests for matching and non-matching scenarios
* Confidence scores for clusters
* Manual review workflow for borderline matches
* Public Suffix List (PSL) based URL parsing
* Phonetic company-name matching
* Richer industry taxonomy mapping
* Employee-count anomaly detection
* Source freshness weighting
* Docker support for reproducible deployment

---

# Conclusion

The architecture is intentionally **deterministic**, **conservative**, and **fully explainable**.

It satisfies the core objective of producing **one trusted golden record per company**, while maintaining complete field-level provenance, deterministic matching rules, robust conflict resolution policies, and transparent quarantine handling.

The resulting dataset is reliable, auditable, reproducible, and suitable for downstream analytics, integration, and data governance workflows.
