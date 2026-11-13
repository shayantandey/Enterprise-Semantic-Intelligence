"""Exercise 5: review drafted descriptions as a steward, with automatic checks to help.

Run:  python lab5_review_drafts.py
drafts.json holds ten descriptions in the style a language model produces, each with the evidence
a steward can see. They were written for this lab; no model is called and no API key is needed.
Stage 1 runs three automatic checks and writes decisions.csv. Two checks are written. Write the third.
Fill in decisions.csv (approve, edit or reject, with a reason) and run again.
If the text you type contains a comma, put double quotes around it: "first, second".
Stage 2 publishes what you approved or edited, with its provenance, and compares your decisions with the key.
"""
import csv
import json
import re
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent.parent   # the solution reads the data in the lab folder
STEWARD = "your name"          # change this to your name
KEY = {"d01": "edit", "d02": "reject", "d03": "approve", "d04": "edit", "d05": "approve",
       "d06": "reject", "d07": "edit", "d08": "reject", "d09": "reject", "d10": "approve"}


def read_csv(path, required):
    """Read a CSV that a participant has edited. Stops with a clear message when a row is damaged."""
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for n, row in enumerate(rows, start=2):
        if None in row or any(row.get(c) is None for c in required):
            raise SystemExit(f"{path.name}, line {n}: the row has the wrong number of columns. "
                             'Put double quotes around any text that contains a comma, for example "first, second".')
    return rows

def evidence_text(item):
    return " ".join(str(v) for v in item["evidence"].values())


def check_business_claim(item):
    """Flag wording that asserts a business definition, which only a term owner can decide."""
    hits = [w for w in ("meaning", "as defined by", "defined as") if w in item["draft"].lower()]
    return f"asserts a business definition ('{hits[0]}')" if hits else None


def check_unsupported_numbers(item):
    """Flag any number in the draft that does not appear in the evidence."""
    # Answer. Hint given: find numbers with re.findall(r"\d+", ...) in the draft and in evidence_text(item); return a message naming the numbers that are only in the draft (each number once), or None
    in_draft = re.findall(r"\d+", item["draft"])
    in_evidence = set(re.findall(r"\d+", evidence_text(item)))
    extra = list(dict.fromkeys(n for n in in_draft if n not in in_evidence))
    return f"numbers not in the evidence: {', '.join(extra)}" if extra else None


def check_example_value(item):
    """Flag a draft that quotes something that looks like a real value: an email address or a long digit string."""
    if re.search(r"[\w.]+@[\w.]+", item["draft"]) or re.search(r"\d{6,}", item["draft"]):
        return "quotes what looks like a real value"
    return None


CHECKS = (check_business_claim, check_unsupported_numbers, check_example_value)


def stage1(drafts):
    rows, unwritten = [], False
    for item in drafts:
        flags = []
        for check in CHECKS:
            try:
                result = check(item)
            except NotImplementedError:
                result, unwritten = f"{check.__name__} not written yet", True
            if result:
                flags.append(result)
        print(f"{item['id']}  {item['object']}")
        print(f"     draft: {item['draft']}")
        for k, v in item["evidence"].items():
            print(f"     {k}: {v}")
        print(f"     flags: {'; '.join(flags) or 'none'}")
        rows.append([item["id"], item["object"], item["draft"], "; ".join(flags), "", "", ""])
    path = HERE / "decisions.csv"
    if unwritten:
        print("\nWrite check_unsupported_numbers() and run again. decisions.csv is written once all three checks run.")
    elif not path.exists():
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "object", "draft", "flags", "decision", "final_text", "reason"])
            w.writerows(rows)
        print(f"\nWrote {path.name}. For each row type approve, edit or reject. For edit, put the corrected text in final_text. Then run again.")


def stage2(drafts):
    decisions = read_csv(HERE / "decisions.csv", ("id", "decision", "final_text", "reason"))
    if any(d["decision"].strip().lower() not in ("approve", "edit", "reject") for d in decisions):
        print("\ndecisions.csv still has rows without approve, edit or reject. Stage 2 has not run.")
        return
    if STEWARD == "your name":
        print("\nNote: STEWARD at the top of the script is still 'your name'. Set it so that published.json records who approved.")
    published, same = [], 0
    for d in decisions:
        choice = d["decision"].strip().lower()
        same += choice == KEY[d["id"]]
        if choice == "edit" and not d["final_text"].strip():
            print(f"{d['id']}: marked edit but final_text is empty, so it was not published")
            continue
        if choice in ("approve", "edit"):
            published.append({"object": d["object"], "description": d["final_text"].strip() if choice == "edit" else d["draft"],
                              "drafted_by": "language model (simulated for this lab)", "decision": choice, "approved_by": STEWARD,
                              "approved_on": date.today().isoformat(), "reason": d["reason"]})
    (HERE / "published.json").write_text(json.dumps(published, indent=1), encoding="utf-8")
    print(f"\nStage 2: published {len(published)} of {len(decisions)} descriptions to published.json, each with who drafted and who approved it.")
    print(f"{same} of {len(KEY)} decisions match the key.")
    for d in decisions:
        if d["decision"].strip().lower() != KEY[d["id"]]:
            print(f"   {d['id']}: you chose {d['decision'].strip().lower()}, the key has {KEY[d['id']]}")


def main():
    drafts = json.loads((HERE / "drafts.json").read_text(encoding="utf-8"))
    stage1(drafts)
    if (HERE / "decisions.csv").exists():
        stage2(drafts)


if __name__ == "__main__":
    main()
