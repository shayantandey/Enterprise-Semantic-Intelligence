"""Lab 6. Change two retrieval architecture choices and measure the effect against the baseline on the same 60 questions.

Edit retrieval_config.json first: switch exactly two of the five options to true. Then run:  python lab06_changes.py
Options: contextual_headers (index time), parent_child, glossary_expansion, metadata_filter, decompose (all query time)."""
import random, sys
from pathlib import Path
LAB = Path(__file__).resolve().parent; LAB = LAB.parent if LAB.name == "solutions" else LAB
sys.path.insert(0, str(LAB))
import db, labkit

OPTIONS = ["contextual_headers", "parent_child", "glossary_expansion", "metadata_filter", "decompose"]

def paired_bootstrap(before, after, resamples=2000, seed=5):
    """Mean difference (after - before) over the same questions, with a 95 percent interval from resampling the questions.
    The questions are resampled as pairs, which removes the question-to-question variation that both runs share."""
    rng = random.Random(seed); n = len(before); d = [a - b for a, b in zip(after, before)]
    means = sorted(sum(rng.choices(d, k=n)) / n for _ in range(resamples))
    return sum(d) / n, means[int(0.025 * resamples)], means[int(0.975 * resamples) - 1]

def ensure_index(con, cfg):
    """Re-embed if the index was built with a different contextual_headers setting from the one asked for."""
    import indexer
    has, = con.execute("SELECT bool_or(search_text <> text) FROM chunks").fetchone()
    if bool(has) != bool(cfg["contextual_headers"]):
        print(f"  Index-time option contextual_headers={cfg['contextual_headers']}: the search text of every chunk changes, so every chunk is embedded again.")
        indexer.sync(con, indexer.current_paths(), cfg, f"re-embed with contextual_headers={cfg['contextual_headers']}")

def main():
    import lab04_evaluate
    con = db.connect(); cfg = labkit.config()
    on = [o for o in OPTIONS if cfg[o]]
    if len(on) != 2:
        print(f"NOTE: {len(on)} options are switched on in retrieval_config.json ({', '.join(on) or 'none'}). The exercise asks for exactly two.\n")
    base = dict(cfg, **{o: False for o in OPTIONS})
    print("Baseline (all options off):"); ensure_index(con, base)
    b = lab04_evaluate.evaluate(con, base, "hybrid_rerank"); sb = lab04_evaluate.summarise(b)
    print(f"Changed ({', '.join(on) or 'nothing'}):"); ensure_index(con, cfg)
    a = lab04_evaluate.evaluate(con, cfg, "hybrid_rerank"); sa = lab04_evaluate.summarise(a)
    rows = []
    for m, label in (("recall", f"recall@{cfg['k']}"), ("ndcg", f"nDCG@{cfg['k']}"), ("sufficient", "evidence sufficiency")):
        bv = [r[m] for r in b if r["answerable"]]; av = [r[m] for r in a if r["answerable"]]
        d, lo, hi = paired_bootstrap(bv, av)
        verdict = "improvement" if lo > 0 else "regression" if hi < 0 else "not distinguishable from no change"
        rows.append([label, f"{sb[m][0]:.3f}", f"{sa[m][0]:.3f}", f"{d:+.3f} [{lo:+.3f}, {hi:+.3f}]", verdict])
    print(f"\n{sb['n']} answerable questions, hybrid_rerank:\n")
    labkit.table(rows, ["metric", "baseline", "changed", "difference and 95 percent interval", "reading"])
    print()
    labkit.table([["latency p50 / p95 ms", f"{sb['p50_ms']:.0f} / {sb['p95_ms']:.0f}", f"{sa['p50_ms']:.0f} / {sa['p95_ms']:.0f}"],
                  ["words returned per question", f"{sb['words']:.0f}", f"{sa['words']:.0f}"], ["leaks", sb["leaked"], sa["leaked"]]], ["cost side", "baseline", "changed"])
    gained = [x["qid"] for x, y in zip(a, b) if x["answerable"] and x["sufficient"] > y["sufficient"]]
    lost = [x["qid"] for x, y in zip(a, b) if x["answerable"] and x["sufficient"] < y["sufficient"]]
    print(f"\nQuestions that gained sufficient evidence: {', '.join(gained) or 'none'}\nQuestions that lost it: {', '.join(lost) or 'none'}")
    for qid in lost:
        x = next(r for r in a if r["qid"] == qid)
        print(f"    {qid} [{x['category']}] {x['question']}\n        now returns: {', '.join(x['sections'])}")
    print("\nThe index is left as the changed configuration built it. Record the decision in adr/retrieval-architecture-decision.md, then: python check.py 6")

if __name__ == "__main__":
    main()
