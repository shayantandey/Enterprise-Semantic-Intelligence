"""Exercise 4 without Git: show what changed between two versions of a file.

Run:  python diff_versions.py old_file new_file
      python diff_versions.py 03_ontology/ontology_seed.ttl 03_ontology/ontology.ttl

Prints the lines that were removed (-) and added (+). Git does the same with:  git diff
"""
import difflib
import sys
from pathlib import Path

if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    old, new = (Path(p).read_text(encoding="utf-8").splitlines() for p in sys.argv[1:3])
    changes = [l for l in difflib.unified_diff(old, new, sys.argv[1], sys.argv[2], lineterm="", n=0) if not l.startswith("@@")]
    print("\n".join(changes) if changes else "The two files are the same.")
    added = sum(1 for l in changes[2:] if l.startswith("+"))
    removed = sum(1 for l in changes[2:] if l.startswith("-"))
    print(f"\n{added} line(s) added, {removed} line(s) removed.")
