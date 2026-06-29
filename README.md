# Multi-Source Golden Record

A Python backend pipeline that reconciles three messy company data sources into one trusted golden record per company, with field-level provenance and a reconciliation report.

---

# What This Project Does

The input files describe overlapping companies from three different sources:

* `source1_crm.csv` – Human-entered CRM export with contact details, messy names, and older capture dates.
* `source2_vendor.csv` – Paid vendor feed with cleaner domains and structured firmographics.
* `source3_web.csv` – Scraped web directory with fresh but coarse and occasionally incorrect data.

The pipeline:

* Normalizes company names, domains, locations, industries, and employee counts.
* Matches records across sources without a shared ID.
* Resolves conflicting fields using a consistent policy.
* Records provenance for every selected field.
* Quarantines junk or unusable rows.
* Writes golden-record outputs and a reconciliation report.

---

# Project Structure

```text
golden_record_solution/
│
├── README.md
├── ARCHITECTURE.md
├── AI_USAGE_LOG.md
├── requirements.txt
│
├── data/
│   ├── source1_crm.csv
│   ├── source2_vendor.csv
│   └── source3_web.csv
│
├── golden_record/
│   ├── __init__.py
│   ├── __main__.py
│   └── pipeline.py
│
└── output/
    ├── golden_records.json
    ├── golden_records.csv
    ├── quarantine.csv
    └── reconciliation_report.md
```

---

# Requirements

* Python **3.11** or newer is recommended.
* This project uses only the Python Standard Library.
* No third-party packages are required.

---

# Setup

From the project root:

```bash
python --version
```

Confirm Python is available.

No dependency installation is required.

---

# Input Data

Place the provided CSV files inside the `data/` directory.

```text
data/source1_crm.csv
data/source2_vendor.csv
data/source3_web.csv
```

> **Note:** Do not manually edit the input files. Cleaning and reconciliation are handled automatically by the pipeline.

---

# Run

From the project root, execute:

```bash
python -m golden_record
```

Expected console output:

```text
Wrote 144 golden records to .../output
Quarantined 3 rows
```

(The exact path depends on where the project is located.)

---

# Outputs

The pipeline writes all generated files to the `output/` directory.

## `output/golden_records.json`

The authoritative golden-record output.

Each record contains:

* `golden_id`
* `source_records`
* `source_count`
* `match_reasons`
* `fields`

Each field contains:

* `value`
* `source`
* `source_id`
* `reason`

Example:

```json
{
  "golden_id": "G00001",
  "source_records": [
    {
      "source": "crm",
      "source_id": "CRM5170"
    }
  ],
  "source_count": 1,
  "match_reasons": {},
  "fields": {
    "name": {
      "value": "Drift Technologies GmbH",
      "source": "crm",
      "source_id": "CRM5170",
      "reason": "selected_by_policy_preference_vendor>crm>web"
    }
  }
}
```

---

## `output/golden_records.csv`

A flat convenience export for quick review in spreadsheet applications.

This file does **not** contain complete provenance information.

Use `golden_records.json` whenever provenance is important.

---

## `output/quarantine.csv`

Contains rows excluded from the golden records together with the quarantine reason.

Example reasons:

* `missing_name_and_domain`
* `junk_web_page_without_company_identity`

---

## `output/reconciliation_report.md`

A run-level summary containing:

* Source row counts
* Golden record count
* Quarantine count
* Source coverage
* Conflict breakdown
* Resolution reason counts
* Policy summary

---

# Matching Policy

The matcher is intentionally conservative.

* Exact normalized domain matches are considered strong matches.
* If the domain is missing, fuzzy company-name matching is allowed only with very high similarity and location support.
* Rows with no usable company identity are quarantined.
* Junk web rows such as **"Untitled Page"** with no useful facts are quarantined.

This favors **precision over recall**, because merging two different companies is considered worse than missing a potential match.

---

# Conflict Resolution Policy

Field values are selected using a consistent source-preference policy.

### Vendor is preferred for canonical firmographics

* Company name
* Domain
* Employees
* Industry
* Revenue band
* Founded year

### CRM is preferred for contact-oriented fields

* Email
* City

### Web data

Used as fallback data and freshness support.

If two or more sources agree on a value, agreement may override the normal source preference.

---

# Domain Quality Policy

Domains are normalized before matching and output.

The pipeline rejects invalid domains, including invalid numeric TLDs such as:

```text
example.co1
example.co2
example.co3
```

Invalid domains are left blank in the final golden record instead of being promoted as trusted values.

---

# Idempotency

The pipeline is fully idempotent.

Running:

```bash
python -m golden_record
```

multiple times rewrites the same files in the `output/` directory without duplicating records or corrupting previous outputs.

---

# Current Run Summary

For the provided dataset:

| Metric                           |   Value |
| -------------------------------- | ------: |
| Source rows read                 | **323** |
| Golden companies produced        | **144** |
| Quarantined rows                 |   **3** |
| Companies appearing in 1 source  |  **34** |
| Companies appearing in 2 sources |  **44** |
| Companies appearing in 3 sources |  **66** |

---

# Assumptions

* A false merge is worse than a missed match.
* Vendor data is generally the most trustworthy for structured firmographics.
* CRM data is generally the most trustworthy for contact-related fields.
* Web data is useful for freshness and fallback values but is less trusted.
* Invalid domains should never be promoted into trusted golden records.

---

# Limitations

This solution does **not** use a trained entity-resolution model.

Instead, it implements a deterministic, rule-based reconciliation pipeline designed for:

* Explainability
* Reproducibility
* Consistent policy enforcement


