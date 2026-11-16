"""Exercise 7: check the structure of your ADR 3.

Run:  python check_adr.py
Write your ADR in adr/0003-physical-or-virtual-graph.md first. This script checks the form only.
The reasoning is reviewed by another pair.
"""
import re
from pathlib import Path

PATH = Path(__file__).parent / "adr" / "0003-physical-or-virtual-graph.md"


def main():
    if not PATH.exists():
        raise SystemExit(f"{PATH} not found.")
    text = PATH.read_text(encoding="utf-8")
    sections = dict(re.findall(r"^## (\w+)\s*\n(.*?)(?=^## |\Z)", text, flags=re.S | re.M))
    context = sections.get("Context", "")
    consequences = sections.get("Consequences", "")
    bullets = re.findall(r"^[-*] .*", context, flags=re.M)
    filled = not re.search(r"<[a-z][^<>\n]*>", text)
    checks = [
        ("Title line starts with '# ADR 3'", text.lstrip().startswith("# ADR 3")),
        ("Has the four sections Status, Context, Decision, Consequences",
         all(s in sections for s in ("Status", "Context", "Decision", "Consequences"))),
        ("Status is one of Proposed, Accepted, Deprecated, Superseded",
         sections.get("Status", "").strip().split("\n")[0].strip() in ("Proposed", "Accepted", "Deprecated", "Superseded")),
        ("Context lists at least three facts or assumptions as bullet points", filled and len(bullets) >= 3),
        ("Context marks each bullet as a Fact or an Assumption",
         filled and bool(bullets) and all(re.match(r"[-*] (Fact|Assumption)", b) for b in bullets)),
        ("Decision says 'We will' and names a rejected option", filled and "We will" in sections.get("Decision", "") and "reject" in sections.get("Decision", "").lower()),
        ("Consequences names something that gets harder", filled and "harder" in consequences.lower()),
        ("Consequences gives a condition for revisiting the decision", filled and "revisit" in consequences.lower()),
        ("No template placeholders in angle brackets remain", filled),
    ]
    for label, ok in checks:
        print(f"{'ok  ' if ok else 'TODO'}  {label}")
    done = sum(ok for _, ok in checks)
    print(f"\n{done} of {len(checks)} checks pass.")


if __name__ == "__main__":
    main()
