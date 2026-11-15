"""Exercise 1: find the five planted inconsistencies in a catalog export.

Run:  python lab1_catalog_checks.py
catalog.json is a small hand-written file in the shape of a catalog export: terms, columns, column lineage,
tables and dashboards. It is fictional. Each check below compares two records that should agree. Two checks are written. Write the other three.
"""
import json
from pathlib import Path

CATALOG = json.loads(Path(__file__).with_name("catalog.json").read_text(encoding="utf-8"))
COLUMNS = {c["name"]: c for c in CATALOG["columns"]}
TERMS = {t["id"]: t for t in CATALOG["terms"]}


def upstream(column):
    """Columns one step upstream of this column in the lineage."""
    return [src for src, dst in CATALOG["lineage"] if dst == column]


def sources(column):
    """Follow the lineage back to the columns that have nothing upstream of them."""
    parents = upstream(column)
    if not parents:
        return {column}
    found = set()
    for p in parents:
        found |= sources(p)
    return found


def check_duplicate_terms():
    """Business metadata against itself: two terms with the same definition and no recorded relation."""
    findings = []
    terms = CATALOG["terms"]
    for i, a in enumerate(terms):
        for b in terms[i + 1:]:
            if a["definition"] == b["definition"] and b["id"] not in a["related"] and a["id"] not in b["related"]:
                findings.append(f"{a['id']} {a['name']} and {b['id']} {b['name']} have the same definition and no relation")
    return findings


def check_stale_certified():
    """Operational against governance metadata: a certified dashboard that reads a table past its freshness expectation."""
    stale = {t["name"] for t in CATALOG["tables"] if t["days_since_refresh"] > t["freshness_days_expected"]}
    return [f"dashboard '{d['name']}' is certified and reads stale table {t}"
            for d in CATALOG["dashboards"] if d["certified"] for t in d["reads"] if t in stale]


def check_classification_gaps():
    """Security metadata against lineage: a classified column whose upstream column in the catalog has no classification."""
    # TODO: for each column with a classification, look at upstream(name); report parents that are in COLUMNS and have classification None
    raise NotImplementedError("see the TODO comment")


def check_golden_claims():
    """Business metadata against lineage: a description that says 'golden' on a column whose sources are not in mdm."""
    # TODO: for each column whose description contains 'golden' (any case), report it if any of sources(name) does not start with 'mdm.'
    raise NotImplementedError("see the TODO comment")


def check_term_links():
    """Business metadata against lineage: a column linked to a term whose source_columns share nothing with the column's sources."""
    # TODO: for each column with a term, compare sources(name) with TERMS[term]['source_columns']; report when the two sets have no member in common
    raise NotImplementedError("see the TODO comment")


def main():
    total = 0
    for check in (check_duplicate_terms, check_stale_certified, check_classification_gaps, check_golden_claims, check_term_links):
        try:
            findings = check()
        except NotImplementedError:
            print(f"{check.__name__}: not written yet")
            continue
        total += len(findings)
        print(f"{check.__name__}: {len(findings)} finding(s)")
        for f in findings:
            print(f"   {f}")
    print(f"\n{total} findings. The catalog has five planted inconsistencies. A finding is a question for an owner, and one planted fault can show up in two checks.")


if __name__ == "__main__":
    main()
