"""Exercise 5: publish version 2 of net revenue with an effective date, and decide about restatement.

Run:  python lab5_versioning.py
Finance has decided that net revenue deducts discounts from 1 July 2026. You edit semantic_model.json:
in the "versions" list of the net_revenue metric, add a second entry after version 1:

    {"version": 2, "effective_from": "2026-07-01", "expr": "gross_sales - discounts - refunds",
     "note": "Discounts are deducted from 1 July 2026, to match the statutory accounts."}

Do not edit version 1. Then run this script. It shows the series three ways and checks your change
against baseline_model.json, which is the model as it was before you started.
"""
from semantic_layer import HERE, load_model, query

PERIOD = ("2025-10-01", "2026-10-01")       # the last four fiscal quarters


def classify_changes(old, new):
    """Compare two versions of the semantic model and classify each change to a metric."""
    findings = []
    for name, before in old["metrics"].items():
        after = new["metrics"].get(name)
        if after is None:
            findings.append(("BREAKING", f"{name} was removed. Deprecate it with an end date first, so that consumers can move."))
            continue
        if before.get("versions") is not None:
            old_versions = {v["version"]: v for v in before["versions"]}
            new_versions = {v["version"]: v for v in after.get("versions", [])}
            for number, v in old_versions.items():
                if number not in new_versions:
                    findings.append(("BREAKING", f"{name} version {number} was deleted. Published versions are kept so that old figures can be reproduced."))
                elif new_versions[number]["expr"] != v["expr"] or new_versions[number]["effective_from"] != v["effective_from"]:
                    findings.append(("BREAKING", f"{name} version {number} was edited in place. History changed without a record. Add a new version."))
            for number in sorted(set(new_versions) - set(old_versions)):
                v = new_versions[number]
                findings.append(("MANAGED", f"{name} version {number} added, effective from {v['effective_from']}: {v['expr']}. "
                                            "Needs the owner's approval, a notice to consumers and a restatement decision."))
        else:
            for key in ("type", "measure", "numerator", "denominator", "input_metric", "grain_to_date"):
                if before.get(key) != after.get(key):
                    findings.append(("BREAKING", f"{name}: {key} changed from {before.get(key)} to {after.get(key)} without a version."))
        if before.get("label") != after.get("label"):
            findings.append(("non-breaking", f"{name}: label changed."))
    for name in new["metrics"]:
        if name not in old["metrics"]:
            findings.append(("non-breaking", f"{name} was added. No existing consumer depends on it."))
    return findings


def main():
    model = load_model()
    baseline = load_model(HERE / "baseline_model.json")
    print("Changes since baseline_model.json:")
    for level, text in classify_changes(baseline, model) or [("-", "none")]:
        print(f"  {level:12} {text}")
    versions = {v["version"] for v in model["metrics"]["net_revenue"]["versions"]}
    if 2 not in versions:
        print("\nnet_revenue has no version 2 yet. Add it to semantic_model.json and run again.")
        return
    as_published = {r["fiscal_quarter"]: r["net_revenue"] for r in query(["net_revenue"], group_by=["fiscal_quarter"], start=PERIOD[0], end=PERIOD[1])}
    v1 = {r["fiscal_quarter"]: r["net_revenue"] for r in query(["net_revenue"], group_by=["fiscal_quarter"], start=PERIOD[0], end=PERIOD[1], definition=1)}
    v2 = {r["fiscal_quarter"]: r["net_revenue"] for r in query(["net_revenue"], group_by=["fiscal_quarter"], start=PERIOD[0], end=PERIOD[1], definition=2)}
    print("\nNet revenue by fiscal quarter")
    print(f"  {'quarter':12} {'version 1 throughout':>22} {'effective-dated':>18} {'version 2 restated':>20}")
    for q in sorted(v1):
        print(f"  {q:12} {v1[q]:22,.2f} {as_published[q]:18,.2f} {v2[q]:20,.2f}")
    quarters = sorted(v1)
    last, prev = quarters[-1], quarters[-2]

    def change(series):
        return 100 * (series[last] - series[prev]) / series[prev]

    print(f"\nChange from {prev} to {last}:")
    print(f"  effective-dated series {change(as_published):6.1f}%   (mixes the business change with the definition change)")
    print(f"  version 1 throughout   {change(v1):6.1f}%")
    print(f"  version 2 restated     {change(v2):6.1f}%")
    print("\nAfter the session, fill in restatement_note.md: which series each audience gets, and from when.")


if __name__ == "__main__":
    main()
