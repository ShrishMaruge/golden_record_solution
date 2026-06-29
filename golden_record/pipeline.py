import csv
import json
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "output"

SOURCE_TRUST = {
    "vendor": 3,
    "crm": 2,
    "web": 1,
}

COUNTRY_ALIASES = {
    "us": "United States",
    "usa": "United States",
    "u.s.a.": "United States",
    "united states": "United States",
    "de": "Germany",
    "germany": "Germany",
    "deutschland": "Germany",
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
    "britain": "United Kingdom",
    "united kingdom": "United Kingdom",
    "can": "Canada",
    "ca": "Canada",
    "canada": "Canada",
    "aus": "Australia",
    "au": "Australia",
    "australia": "Australia",
    "in": "India",
    "india": "India",
    "bharat": "India",
}

INDUSTRY_MAP = {
    "fintech": "Financial Services",
    "finance / payments": "Financial Services",
    "financial services": "Financial Services",
    "health": "Healthcare Technology",
    "health tech": "Healthcare Technology",
    "healthcare technology": "Healthcare Technology",
    "security": "Information Security",
    "cybersecurity": "Information Security",
    "information security": "Information Security",
    "shipping": "Logistics & Supply Chain",
    "logistics": "Logistics & Supply Chain",
    "logistics & supply chain": "Logistics & Supply Chain",
    "telecom": "Telecommunications",
    "telecoms": "Telecommunications",
    "telecommunications": "Telecommunications",
    "education": "Education Technology",
    "edtech": "Education Technology",
    "education technology": "Education Technology",
    "games": "Interactive Entertainment",
    "gaming": "Interactive Entertainment",
    "interactive entertainment": "Interactive Entertainment",
    "retail": "Consumer Retail",
    "ecommerce / retail": "Consumer Retail",
    "consumer retail": "Consumer Retail",
    "energy": "Energy & Utilities",
    "clean energy": "Energy & Utilities",
    "energy & utilities": "Energy & Utilities",
    "manufacturing": "Industrial Manufacturing",
    "factory / industrial": "Industrial Manufacturing",
    "industrial manufacturing": "Industrial Manufacturing",
}

LEGAL_SUFFIXES = {
    "inc", "incorporated", "ltd", "limited", "llc", "corp", "corporation",
    "co", "company", "gmbh", "plc"
}

JUNK_WEB_NAMES = {
    "untitled page",
    "home",
    "homepage",
    "index",
    "welcome",
    "error",
    "404",
    "not found",
}


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def normalize_domain(value):
    value = clean(value).lower()
    value = re.sub(r"^https?://", "", value)
    value = re.sub(r"^www\.", "", value)
    value = value.split("/")[0].strip()
    value = value.split("?")[0].strip()

    if not value:
        return ""
    if "." not in value:
        return ""
    if " " in value:
        return ""

    return value


def domain_from_email(email):
    email = clean(email).lower()
    if "@" not in email:
        return ""
    domain = email.split("@")[-1]
    return normalize_domain(domain)


def normalize_name(value):
    value = clean(value).lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9 ]+", " ", value)

    words = []
    for word in value.split():
        if word not in LEGAL_SUFFIXES:
            words.append(word)

    return " ".join(words)


def normalize_country(value):
    key = clean(value).lower()
    return COUNTRY_ALIASES.get(key, clean(value))


def normalize_city(value):
    return clean(value).title()


def normalize_industry(value):
    key = clean(value).lower()
    return INDUSTRY_MAP.get(key, clean(value))


def parse_location(value):
    value = clean(value)
    if not value:
        return "", ""

    parts = [p.strip() for p in value.split(",")]
    if len(parts) == 1:
        return normalize_city(parts[0]), ""

    city = normalize_city(parts[0])
    country = normalize_country(parts[-1])
    return city, country


def parse_web_size(value):
    value = clean(value)
    if not value or value == "?":
        return ""

    if value.endswith("+"):
        return clean(value[:-1])

    if "-" in value:
        left, right = value.split("-", 1)
        try:
            return str(round((int(left) + int(right)) / 2))
        except ValueError:
            return ""

    return value


def row_identity_missing(row):
    return not row["norm_name"] and not row["domain"]


def is_junk_row(row):
    if row_identity_missing(row):
        return True, "missing_name_and_domain"

    if row["source"] == "web":
        name_key = row["name"].lower()
        no_useful_facts = not any([
            row["domain"],
            row["industry"],
            row["employees"],
            row["country"],
            row["city"],
        ])
        if name_key in JUNK_WEB_NAMES and no_useful_facts:
            return True, "junk_web_page_without_company_identity"

    return False, ""


def read_crm_rows():
    rows = []

    with open(DATA_DIR / "source1_crm.csv", newline="", encoding="utf-8") as f:
        for raw in csv.DictReader(f):
            email = clean(raw.get("primary_contact_email"))
            domain = normalize_domain(raw.get("website"))

            if not domain:
                domain = domain_from_email(email)

            rows.append({
                "source": "crm",
                "source_id": clean(raw.get("crm_id")),
                "name": clean(raw.get("account_name")),
                "norm_name": normalize_name(raw.get("account_name")),
                "domain": domain,
                "industry": normalize_industry(raw.get("industry")),
                "employees": clean(raw.get("headcount")),
                "revenue_band": "",
                "founded_year": "",
                "country": normalize_country(raw.get("country")),
                "city": normalize_city(raw.get("city")),
                "email": email,
                "date": clean(raw.get("last_updated")),
                "raw": raw,
            })

    return rows


def read_vendor_rows():
    rows = []

    with open(DATA_DIR / "source2_vendor.csv", newline="", encoding="utf-8") as f:
        for raw in csv.DictReader(f):
            rows.append({
                "source": "vendor",
                "source_id": clean(raw.get("vendor_id")),
                "name": clean(raw.get("legal_name")),
                "norm_name": normalize_name(raw.get("legal_name")),
                "domain": normalize_domain(raw.get("domain")),
                "industry": normalize_industry(raw.get("industry")),
                "employees": clean(raw.get("employees")),
                "revenue_band": clean(raw.get("revenue_band")),
                "founded_year": clean(raw.get("founded_year")),
                "country": normalize_country(raw.get("hq_country")),
                "city": "",
                "email": "",
                "date": clean(raw.get("as_of")),
                "raw": raw,
            })

    return rows


def read_web_rows():
    rows = []

    with open(DATA_DIR / "source3_web.csv", newline="", encoding="utf-8") as f:
        for raw in csv.DictReader(f):
            city, country = parse_location(raw.get("location"))

            rows.append({
                "source": "web",
                "source_id": clean(raw.get("page_id")),
                "name": clean(raw.get("company")),
                "norm_name": normalize_name(raw.get("company")),
                "domain": normalize_domain(raw.get("url")),
                "industry": normalize_industry(raw.get("category")),
                "employees": parse_web_size(raw.get("approx_size")),
                "revenue_band": "",
                "founded_year": "",
                "country": country,
                "city": city,
                "email": "",
                "date": clean(raw.get("crawled_at")),
                "raw": raw,
            })

    return rows


def read_all_rows():
    return read_crm_rows() + read_vendor_rows() + read_web_rows()


def similarity(left, right):
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def match_decision(a, b):
    if a["domain"] and b["domain"]:
        if a["domain"] == b["domain"]:
            return True, 1.0, "exact_domain"
        return False, 0.0, "different_domains"

    name_score = similarity(a["norm_name"], b["norm_name"])

    country_match = (
        a["country"] and b["country"] and a["country"] == b["country"]
    )
    city_match = (
        a["city"] and b["city"] and a["city"].lower() == b["city"].lower()
    )

    if name_score >= 0.94 and (country_match or city_match):
        return True, name_score, "high_name_similarity_with_location"

    if name_score >= 0.97 and not a["country"] and not b["country"]:
        return True, name_score, "very_high_name_similarity_no_location_conflict"

    return False, name_score, "below_match_threshold"


def cluster_rows(rows):
    clusters = []
    quarantine = []

    for row in rows:
        junk, reason = is_junk_row(row)
        if junk:
            quarantine.append({
                "source": row["source"],
                "source_id": row["source_id"],
                "name": row["name"],
                "domain": row["domain"],
                "reason": reason,
            })
            continue

        placed = False

        for cluster in clusters:
            decisions = [match_decision(row, existing) for existing in cluster]
            positive = [d for d in decisions if d[0]]

            if positive:
                cluster.append(row)
                placed = True
                break

        if not placed:
            clusters.append([row])

    return clusters, quarantine


def values_for_field(cluster, field):
    return [r for r in cluster if clean(r.get(field))]


def choose_field(cluster, field, preference):
    candidates = values_for_field(cluster, field)

    if field == "domain":
        valid_candidates = [r for r in candidates if is_valid_domain(r.get("domain"))]
        candidates = valid_candidates

    if not candidates:
        return {
            "value": "",
            "source": "",
            "source_id": "",
            "reason": "no_available_value",
        }

    value_counts = Counter(clean(r[field]) for r in candidates)
    top_value, top_count = value_counts.most_common(1)[0]

    if top_count >= 2:
        winner = next(r for r in candidates if clean(r[field]) == top_value)
        return {
            "value": top_value,
            "source": winner["source"],
            "source_id": winner["source_id"],
            "reason": "value_agreed_by_multiple_sources",
        }

    def sort_key(row):
        preference_rank = (
            preference.index(row["source"])
            if row["source"] in preference
            else 99
        )
        return (
            preference_rank,
            -SOURCE_TRUST.get(row["source"], 0),
            row["date"],
        )

    winner = sorted(candidates, key=sort_key)[0]

    return {
        "value": clean(winner[field]),
        "source": winner["source"],
        "source_id": winner["source_id"],
        "reason": f"selected_by_policy_preference_{'>'.join(preference)}",
    }


def cluster_match_reasons(cluster):
    reasons = Counter()

    for i, left in enumerate(cluster):
        for right in cluster[i + 1:]:
            matched, _, reason = match_decision(left, right)
            if matched:
                reasons[reason] += 1

    return dict(reasons)


def build_record(cluster, index):
    field_policy = {
        "name": ["vendor", "crm", "web"],
        "domain": ["vendor", "crm", "web"],
        "industry": ["vendor", "crm", "web"],
        "employees": ["vendor", "crm", "web"],
        "country": ["vendor", "crm", "web"],
        "city": ["crm", "web", "vendor"],
        "email": ["crm", "vendor", "web"],
        "revenue_band": ["vendor", "crm", "web"],
        "founded_year": ["vendor", "crm", "web"],
    }

    fields = {}
    for field, preference in field_policy.items():
        fields[field] = choose_field(cluster, field, preference)

    return {
        "golden_id": f"G{index:05d}",
        "source_records": [
            {
                "source": row["source"],
                "source_id": row["source_id"],
            }
            for row in cluster
        ],
        "source_count": len(set(row["source"] for row in cluster)),
        "match_reasons": cluster_match_reasons(cluster),
        "fields": fields,
    }


def detect_conflicts(clusters):
    conflict_fields = Counter()
    total_conflicts = 0

    comparable_fields = [
        "name",
        "domain",
        "industry",
        "employees",
        "country",
        "city",
    ]

    for cluster in clusters:
        if len(cluster) < 2:
            continue

        for field in comparable_fields:
            values = {
                clean(row.get(field))
                for row in cluster
                if clean(row.get(field))
            }
            if len(values) > 1:
                conflict_fields[field] += 1
                total_conflicts += 1

    return total_conflicts, conflict_fields


def resolution_reason_counts(records):
    counts = Counter()

    for record in records:
        for meta in record["fields"].values():
            counts[meta["reason"]] += 1

    return counts


def write_json(records):
    with open(OUT_DIR / "golden_records.json", "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)


def write_flat_csv(records):
    columns = [
        "golden_id",
        "name",
        "domain",
        "industry",
        "employees",
        "country",
        "city",
        "email",
        "revenue_band",
        "founded_year",
        "source_count",
    ]

    with open(OUT_DIR / "golden_records.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()

        for record in records:
            row = {
                "golden_id": record["golden_id"],
                "source_count": record["source_count"],
            }

            for column in columns:
                if column in record["fields"]:
                    row[column] = record["fields"][column]["value"]

            writer.writerow(row)


def write_quarantine(quarantine):
    columns = ["source", "source_id", "name", "domain", "reason"]

    with open(OUT_DIR / "quarantine.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()

        for row in quarantine:
            writer.writerow({column: row.get(column, "") for column in columns})


def write_report(rows, clusters, records, quarantine):
    source_row_counts = Counter(row["source"] for row in rows)
    source_coverage = Counter(record["source_count"] for record in records)
    total_conflicts, conflict_fields = detect_conflicts(clusters)
    reason_counts = resolution_reason_counts(records)
    quarantine_reasons = Counter(row["reason"] for row in quarantine)

    text = [
        "# Reconciliation Report",
        "",
        "## Summary",
        "",
        f"- Source rows read: {len(rows)}",
        f"- CRM rows: {source_row_counts['crm']}",
        f"- Vendor rows: {source_row_counts['vendor']}",
        f"- Web rows: {source_row_counts['web']}",
        f"- Golden companies produced: {len(records)}",
        f"- Quarantined rows: {len(quarantine)}",
        f"- Companies appearing in 1 source: {source_coverage[1]}",
        f"- Companies appearing in 2 sources: {source_coverage[2]}",
        f"- Companies appearing in 3 sources: {source_coverage[3]}",
        f"- Field conflicts detected: {total_conflicts}",
        "",
        "## Conflict Breakdown",
        "",
    ]

    if conflict_fields:
        for field, count in sorted(conflict_fields.items()):
            text.append(f"- {field}: {count}")
    else:
        text.append("- No conflicts detected.")

    text.extend([
        "",
        "## Resolution Reasons",
        "",
    ])

    for reason, count in sorted(reason_counts.items()):
        text.append(f"- {reason}: {count}")

    text.extend([
        "",
        "## Quarantine Reasons",
        "",
    ])

    if quarantine_reasons:
        for reason, count in sorted(quarantine_reasons.items()):
            text.append(f"- {reason}: {count}")
    else:
        text.append("- No rows quarantined.")

    text.extend([
        "",
        "## Policy Summary",
        "",
        "- Exact normalized domain matches are treated as strong matches.",
        "- Fuzzy company-name matches require very high similarity and location support.",
        "- Vendor is preferred for canonical firmographics: name, domain, employees, industry, revenue, founded year.",
        "- CRM is preferred for contact-oriented fields such as email and city.",
        "- Web is used as a fallback and freshness signal, but weak web rows are quarantined.",
        "- Agreement by multiple sources can override normal source preference.",
        "",
        "## Output Notes",
        "",
        "- `golden_records.json` is the authoritative output because it includes field-level provenance.",
        "- `golden_records.csv` is a flat convenience export for quick review.",
        "- `quarantine.csv` lists rows excluded from golden records and the reason.",
        "",
        "## Risk Posture",
        "",
        "The matcher favors precision over recall. A missed match is easier to review later, but a false merge corrupts a golden record. For that reason, low-signal rows are kept separate or quarantined.",
        "",
    ])

    (OUT_DIR / "reconciliation_report.md").write_text("\n".join(text), encoding="utf-8")


def run():
    OUT_DIR.mkdir(exist_ok=True)

    rows = read_all_rows()
    clusters, quarantine = cluster_rows(rows)
    records = [build_record(cluster, index + 1) for index, cluster in enumerate(clusters)]

    write_json(records)
    write_flat_csv(records)
    write_quarantine(quarantine)
    write_report(rows, clusters, records, quarantine)

    print(f"Wrote {len(records)} golden records to {OUT_DIR}")
    print(f"Quarantined {len(quarantine)} rows")



def is_valid_domain(domain):
    domain = clean(domain).lower()
    if not domain:
        return False
    if not re.match(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$", domain):
        return False

    tld = domain.split(".")[-1]
    if not tld.isalpha():
        return False

    if len(tld) < 2:
        return False

    return True