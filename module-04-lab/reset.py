"""Reset this lab to the state it was in when you received it, so that you can do the exercises again.

Run:  python reset.py          asks you to confirm first
      python reset.py --yes    resets without asking

What it does:
1. Saves your current work: every file you changed or created is copied to a new folder named
   my_work_<date>_<time> inside this folder. Nothing you wrote is lost.
2. Deletes the files that the lab scripts generate (the database, CSV and JSON output).
3. Puts back the original version of every lab file from the reset_files folder.

It does not touch the solutions folder, earlier my_work folders, or any file that is not part of the lab,
such as a page you saved here. Needs only the Python standard library. Do not edit the reset_files folder.
"""
import filecmp
import shutil
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORIGINALS = HERE / "reset_files"
GENERATED = ["retail.db", "metrics.db", "pharma.db", "failures.csv", "review_queue.csv", "golden_records.csv",
             "crosswalk.csv", "decisions.csv", "published.json"]


def main():
    if not ORIGINALS.is_dir():
        raise SystemExit("The reset_files folder is missing, so the lab cannot be reset. Copy the lab folder again from the facilitator.")
    originals = sorted(p.relative_to(ORIGINALS) for p in ORIGINALS.rglob("*") if p.is_file())
    changed = [rel for rel in originals if not (HERE / rel).exists() or not filecmp.cmp(HERE / rel, ORIGINALS / rel, shallow=False)]
    edited = [rel for rel in changed if (HERE / rel).exists()]
    generated = [Path(name) for name in GENERATED if (HERE / name).exists()]
    caches = [p for p in HERE.rglob("__pycache__") if p.is_dir() and "reset_files" not in p.parts and not p.relative_to(HERE).parts[0].startswith("my_work_")]

    if not changed and not generated and not caches:
        print("Nothing to reset. Every lab file is already in its original state.")
        return
    print(f"Lab folder: {HERE.name}")
    print(f"  files you changed, to be saved and then restored:  {len(edited)}")
    for rel in edited:
        print(f"     {rel.as_posix()}")
    print(f"  generated files, to be saved and then deleted:     {len(generated)}")
    for rel in generated:
        print(f"     {rel.as_posix()}")
    if len(changed) > len(edited):
        print(f"  missing files, to be put back:                     {len(changed) - len(edited)}")
    if "--yes" not in sys.argv:
        answer = input("Reset the lab? Your work is saved to a my_work folder first. Type yes to continue: ")
        if answer.strip().lower() not in ("yes", "y"):
            print("Nothing was changed.")
            return

    to_save = [rel for rel in edited + generated if rel.suffix != ".db"]     # the database is rebuilt by setup, so it is not copied
    backup = None
    if to_save:
        backup = HERE / f"my_work_{datetime.now():%Y%m%d_%H%M%S}"
        for rel in to_save:
            (backup / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(HERE / rel, backup / rel)

    for rel in generated:
        try:
            (HERE / rel).unlink()
        except PermissionError:
            raise SystemExit(f"{rel} is open in another program. Close it (for example the sqlite3 prompt or a spreadsheet) "
                             "and run reset.py again. Your work has already been saved"
                             + (f" to {backup.name}." if backup else "."))
    for cache in caches:
        shutil.rmtree(cache, ignore_errors=True)
    for rel in changed:
        (HERE / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ORIGINALS / rel, HERE / rel)

    print(f"\nReset done: {len(changed)} file(s) restored, {len(generated)} generated file(s) deleted.")
    if backup:
        print(f"Your earlier work is in {backup.name}.")
    if (HERE / "setup_warehouse.py").exists():
        print("Start again with:  python setup_warehouse.py")
    else:
        print("Start again with exercise 1 in README.md.")


if __name__ == "__main__":
    main()
