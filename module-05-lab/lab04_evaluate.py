"""Lab 4. Evaluate retrieval against the 60-question gold set and report each metric with a confidence interval.

Run:  python lab04_evaluate.py            (all four methods)
      python lab04_evaluate.py hybrid_rerank
You write three functions: recall at k, nDCG at k and a bootstrap confidence interval."""
import json, math, random, sys
from pathlib import Path
LAB = Path(__file__).resolve().parent; LAB = LAB.parent if LAB.name == "solutions" else LAB
sys.path.insert(0, str(LAB))
import db, embedder, labkit

def recall_at_k(retrieved, relevant, k):
    """Share of the relevant sections that appear in the first k retrieved sections.

    retrieved: list of section ids in rank order, for example ["CC-GOLD:late", "CC-CLASSIC:late"], without repeats.
    relevant:  {section id: grade}. Count the sections with grade 2 only (grade 1 is 'related, does not answer').
    Return a float from 0.0 to 1.0. Raise ValueError if no section has grade 2: recall is undefined for such a question."""
    # TODO: the grade-2 sections are the answers; count how many of them are in retrieved[:k]
    raise NotImplementedError("see the TODO comment")

def ndcg_at_k(retrieved, relevant, k):
    """Normalised discounted cumulative gain at k, with graded relevance.

    The gain of a section with grade g is 2**g - 1 (grade 2 -> 3, grade 1 -> 1, not in `relevant` -> 0).
    DCG = sum over positions i = 1..k of gain_i / log2(i + 1).
    The ideal DCG is the DCG of the best possible order: the grades in `relevant` sorted from high to low, cut at k.
    Return DCG / ideal DCG, a float from 0.0 to 1.0."""
    # TODO: DCG over retrieved[:k] with math.log2(position + 1), divided by the same sum over the grades sorted from high to low
    raise NotImplementedError("see the TODO comment")

def bootstrap_ci(values, resamples=2000, seed=5, level=0.95):
    """A percentile bootstrap confidence interval for the mean of `values` (one value per question).

    Repeat `resamples` times: draw len(values) values WITH replacement and take their mean. Sort the means.
    Return (low, high): the values at positions (1 - level) / 2 and 1 - (1 - level) / 2 of the sorted means.
    Use random.Random(seed) so that everyone in the room gets the same interval."""
    # TODO: rng.choices(values, k=len(values)) draws one resample; positions 50 and 1949 of the 2,000 sorted means are the ends of a 95 percent interval
    raise NotImplementedError("see the TODO comment")

# ----------------------------------------------------------------------------------------------- provided from here on
recall_at_k_ = labkit.use("lab04_evaluate", "recall_at_k")
ndcg_at_k_ = labkit.use("lab04_evaluate", "ndcg_at_k")
bootstrap_ci_ = labkit.use("lab04_evaluate", "bootstrap_ci")

def judge(con, item, out, k):
    """Score one gold question against one search result. Returns a dict of per-question values."""
    res = out["results"][:k]
    sections = list(dict.fromkeys(f"{r['doc_id']}:{r['section']}" for r in res))
    relevant = {f"{r['doc_id']}:{r['section']}": r["grade"] for r in item["relevant"]}
    row = dict(qid=item["qid"], category=item["category"], question=item["question"], role=item["role"], sections=sections,
               seconds=out["seconds"], words=sum(len(r["text"].split()) for r in res),
               leaked=sum(item["role"] not in r["allowed_roles"] for r in res),
               answerable=bool(relevant))
    if relevant:
        docs = {r["doc_id"] for r in item["relevant"]}
        shown = " ".join(r["text"] for r in res if r["doc_id"] in docs)
        row.update(recall=recall_at_k_(sections, relevant, k), ndcg=ndcg_at_k_(sections, relevant, k),
                   rr=next((1.0 / (i + 1) for i, s in enumerate(sections) if relevant.get(s) == 2), 0.0),
                   precision=sum(s in relevant for s in sections) / max(len(sections), 1),
                   sufficient=float(all(e in shown for e in item["evidence"])))
    return row

def evaluate(con, cfg, mode):
    import retriever
    return [judge(con, item, retriever.search(con, item["question"], item["role"], cfg, mode), cfg["k"]) for item in labkit.gold()]

def summarise(rows):
    """Means with 95 percent bootstrap intervals over the answerable questions, plus latency and the two safety counts."""
    ans = [r for r in rows if r["answerable"]]
    out = {"n": len(ans)}
    for m in ("recall", "ndcg", "rr", "precision", "sufficient"):
        vals = [r[m] for r in ans]
        out[m] = (sum(vals) / len(vals),) + tuple(bootstrap_ci_(vals))
    secs = sorted(r["seconds"] for r in rows)
    out["p50_ms"], out["p95_ms"] = 1000 * secs[len(secs) // 2], 1000 * secs[int(0.95 * len(secs)) - 1]
    out["words"] = sum(r["words"] for r in rows) / len(rows)
    out["leaked"] = sum(r["leaked"] for r in rows)
    return out

def fmt(t):
    return f"{t[0]:.3f} [{t[1]:.3f}, {t[2]:.3f}]"

def main():
    import retriever
    con = db.connect(); cfg = labkit.config()
    modes = sys.argv[1:] or retriever.MODES
    retriever.search(con, "warm up", "agent", cfg, "hybrid_rerank")           # load the models before timing anything
    print(f"Embedding model: {embedder.describe()}    k = {cfg['k']}    options on: " + (", ".join(k for k, v in cfg.items() if v is True) or "none (baseline)"))
    table, saved = [], {}
    for mode in modes:
        rows = evaluate(con, cfg, mode); s = summarise(rows); saved[mode] = rows
        table.append([mode, fmt(s["recall"]), fmt(s["ndcg"]), fmt(s["sufficient"]), f"{s['rr'][0]:.3f}", f"{s['precision'][0]:.3f}",
                      f"{s['p50_ms']:.0f} / {s['p95_ms']:.0f}", f"{s['words']:.0f}", s["leaked"]])
    n = sum(r["answerable"] for r in rows)
    print(f"\n{n} answerable questions. Mean and 95 percent bootstrap interval:\n")
    labkit.table(table, ["method", f"recall@{cfg['k']}", f"nDCG@{cfg['k']}", "evidence sufficiency", "MRR", f"precision@{cfg['k']}", "latency p50 / p95 ms", "words returned", "leaks"])
    last = saved[modes[-1]]
    print(f"\nBy category, {modes[-1]} (n is small: use these to choose what to read in lab 5):\n")
    cats = {}
    for r in last:
        if r["answerable"]: cats.setdefault(r["category"], []).append(r)
    labkit.table([[c, len(v), f"{sum(x['recall'] for x in v) / len(v):.2f}", f"{sum(x['sufficient'] for x in v) / len(v):.2f}"] for c, v in sorted(cats.items())], ["category", "n", "recall", "sufficiency"])
    un = [r for r in last if not r["answerable"]]
    stale = [r["qid"] for r in un if any(s.split(":")[0] == "PROMO-FESTIVE" for s in r["sections"])]
    print(f"\n{len(un)} questions have no permitted, current answer. Results from a withdrawn document: {stale or 'none'}. Results the asker may not read: {sum(r['leaked'] for r in un)}.")
    (LAB / "results").mkdir(exist_ok=True)
    (LAB / "results" / "last_eval.json").write_text(json.dumps(saved, indent=1), encoding="utf-8")
    print("\nPer-question results saved to results/last_eval.json\nNext: python check.py 4")

if __name__ == "__main__":
    main()
