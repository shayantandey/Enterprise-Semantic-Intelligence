"""Exercise 2: match CRM and ERP customer records, review the uncertain pairs, build golden records.

Run:  python lab2_matching.py
Stage 1 scores candidate pairs with the Fellegi-Sunter model from section 2.5 and writes review_queue.csv.
Fill in the decision column (accept or reject) and run the script again.
Stage 2 then builds golden_records.csv and crosswalk.csv.
You write match_weight(). survive() is written: read it, because the page asks a question about it.
All records are fictional and were generated for this lab.
"""
import csv
import math
from difflib import SequenceMatcher
from pathlib import Path

HERE = Path(__file__).parent
PRIOR = math.log2(1 / 9999)       # one pair in ten thousand is a true match: about -13.29
# Illustrative weights: (added when the field agrees, added when it disagrees).
WEIGHTS = {"email": (9.8, -3.5), "surname": (6.6, -4.9), "dob": (7.9, -5.6),
           "first_name": (4.1, -2.8), "city": (3.2, -1.2)}   # phone is not in the model
ACCEPT_AT, REJECT_BELOW = 0.95, 0.05


def read(name):
    with (HERE / name).open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for n, row in enumerate(rows, start=2):
        if None in row or any(v is None for v in row.values()):
            raise SystemExit(f"{name}, line {n}: the row has the wrong number of columns. Keep the commas when you edit the file.")
    return rows


def agrees(field, a, b):
    """True or False when both values are present, None when either is missing."""
    x, y = a[field].strip().lower(), b[field].strip().lower()
    if not x or not y:
        return None
    if field in ("first_name", "surname"):
        if len(x) == 1 or len(y) == 1:                       # an initial agrees with a name that starts with it
            return x[0] == y[0]
        return SequenceMatcher(None, x, y).ratio() >= 0.85   # tolerate a one-letter typo
    return x == y


def blocking_pairs(crm, erp):
    """Only compare pairs that share the first three letters of the surname, or the email."""
    for a in crm:
        for b in erp:
            if (a["surname"][:3].lower() == b["surname"][:3].lower()
                    or (a["email"] and a["email"] == b["email"])):
                yield a, b


def match_weight(a, b):
    """Start from PRIOR. For each field in WEIGHTS add the agree weight, the disagree weight, or nothing if missing."""
    # TODO: loop over WEIGHTS.items(); call agrees(field, a, b); add the first weight for True, the second for False, nothing for None
    raise NotImplementedError("see the TODO comment")


def probability(w):
    return 2 ** w / (1 + 2 ** w)


def survive(records):
    """Build one golden record from the source records of one person.

    records is a list of dicts, each with a 'system' key ('CRM' or 'ERP') and the source fields.
    The rule:
      first_name, surname, dob: from the ERP record if it has a value longer than one letter, otherwise the CRM value
      phone, city: from the most recently updated record that has a value
      email: from the CRM record that was updated most recently, otherwise the ERP value
    Return a dict with those six fields.
    """
    newest = sorted(records, key=lambda r: r["updated"], reverse=True)
    erp = [r for r in newest if r["system"] == "ERP"]
    crm = [r for r in newest if r["system"] == "CRM"]
    golden = {}
    for field in ("first_name", "surname", "dob"):
        values = [r[field] for r in erp if len(r[field]) > 1] + [r[field] for r in crm if r[field]]
        golden[field] = values[0] if values else ""
    for field in ("phone", "city"):
        values = [r[field] for r in newest if r[field]]
        golden[field] = values[0] if values else ""
    values = [r["email"] for r in crm if r["email"]] + [r["email"] for r in erp if r["email"]]
    golden["email"] = values[0] if values else ""
    return golden


def score_pairs(crm, erp):
    scored = []
    for a, b in blocking_pairs(crm, erp):
        p = probability(match_weight(a, b))
        scored.append((p, a, b))
    return sorted(scored, key=lambda t: -t[0])


def describe(r):
    return " | ".join(r[k] or "-" for k in ("first_name", "surname", "dob", "email", "phone", "city"))


def stage1(crm, erp):
    scored = score_pairs(crm, erp)
    accepted = [(a, b) for p, a, b in scored if p >= ACCEPT_AT]
    review = [(p, a, b) for p, a, b in scored if REJECT_BELOW <= p < ACCEPT_AT]
    print(f"records: {len(crm)} CRM, {len(erp)} ERP. All pairs: {len(crm) * len(erp)}. Pairs after blocking: {len(scored)}")
    print(f"auto-accepted at {ACCEPT_AT} or above: {len(accepted)}")
    print(f"sent to steward review: {len(review)}")
    print(f"rejected below {REJECT_BELOW}: {len(scored) - len(accepted) - len(review)}")
    truth = {(r["crm_id"], r["erp_id"]) for r in read("labelled_sample.csv")}
    found = {(a["crm_id"], b["erp_id"]) for a, b in accepted}
    queued = {(a["crm_id"], b["erp_id"]) for _, a, b in review}
    wrong = found - truth
    print(f"labelled sample: {len(truth)} true matches. Auto-accepted {len(found & truth)}, in review {len(queued & truth)}, "
          f"missed {len(truth - found - queued)}. Auto-accepted pairs that are not true matches: {len(wrong)}")
    compared = {(a["crm_id"], b["erp_id"]) for _, a, b in scored}
    for c, e in sorted(truth - found - queued):
        why = "scored below the reject threshold" if (c, e) in compared else "never compared: no blocking rule covers this pair"
        print(f"  missed: {c} and {e}, {why}")
    path = HERE / "review_queue.csv"
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["crm_id", "erp_id", "probability", "crm_record", "erp_record", "decision"])
            for p, a, b in review:
                w.writerow([a["crm_id"], b["erp_id"], f"{p:.3f}", describe(a), describe(b), ""])
        print(f"\nWrote {path.name}. Type accept or reject in the decision column for each row, save, and run again.")
    return accepted


def stage2(crm, erp, accepted):
    decisions = read("review_queue.csv")
    if any(d["decision"].strip().lower() not in ("accept", "reject") for d in decisions):
        print("\nreview_queue.csv still has rows without accept or reject. Stage 2 has not run.")
        return
    links = [(a["crm_id"], b["erp_id"], "model, probability >= 0.95") for a, b in accepted]
    links += [(d["crm_id"], d["erp_id"], "steward review") for d in decisions if d["decision"].strip().lower() == "accept"]
    by_id = {r["crm_id"]: dict(r, system="CRM", source_id=r["crm_id"]) for r in crm}
    by_id.update({r["erp_id"]: dict(r, system="ERP", source_id=r["erp_id"]) for r in erp})
    group = {i: i for i in by_id}                      # union-find: every record starts as its own person

    def root(i):
        while group[i] != i:
            i = group[i]
        return i

    how = {}
    for c, e, reason in links:
        group[root(e)] = root(c)
        how[c], how[e] = reason, reason
    clusters = {}
    for i in by_id:
        clusters.setdefault(root(i), []).append(by_id[i])
    golden_rows, crosswalk_rows = [], []
    for n, members in enumerate(sorted(clusters.values(), key=lambda m: min(r["source_id"] for r in m)), start=1):
        key = f"G-{n:06d}"
        golden_rows.append({"golden_key": key, **survive(members)})
        for r in sorted(members, key=lambda r: r["source_id"]):
            crosswalk_rows.append({"golden_key": key, "source_system": r["system"], "source_id": r["source_id"],
                                   "linked_by": how.get(r["source_id"], "no match found")})
    for name, rows in (("golden_records.csv", golden_rows), ("crosswalk.csv", crosswalk_rows)):
        with (HERE / name).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    multi = sum(1 for m in clusters.values() if len(m) > 1)
    print(f"\nStage 2: {len(by_id)} source records became {len(golden_rows)} golden records, {multi} of them with more than one source record.")
    print("Wrote golden_records.csv and crosswalk.csv.")
    sample = next(g for g in golden_rows if g["golden_key"] == crosswalk_rows[[c["source_id"] for c in crosswalk_rows].index("C-1003")]["golden_key"])
    print("Golden record that contains C-1003:", sample)


def main():
    crm, erp = read("crm_records.csv"), read("erp_records.csv")
    try:
        accepted = stage1(crm, erp)
        if (HERE / "review_queue.csv").exists():
            stage2(crm, erp, accepted)
    except NotImplementedError:
        print("Still to write: match_weight(). See the TODO comment in this file.")


if __name__ == "__main__":
    main()
