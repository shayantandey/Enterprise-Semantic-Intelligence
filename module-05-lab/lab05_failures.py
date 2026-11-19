"""Lab 5. Failure analysis: the ten worst questions, and at which stage each lost its evidence.

Run:  python lab05_failures.py
The script gathers the facts. You read them and fill in failure_analysis.md: the cause of each failure and the change that would fix it."""
import sys
from pathlib import Path
LAB = Path(__file__).resolve().parent; LAB = LAB.parent if LAB.name == "solutions" else LAB
sys.path.insert(0, str(LAB))
import db, embedder, labkit

def first_rank(keys, answers):
    """1-based position of the first chunk in `keys` that belongs to an answering section, or None."""
    return next((i + 1 for i, k in enumerate(keys) if k.rsplit(":", 1)[0] in answers), None)

def stage_facts(con, item, cfg):
    """Where the answering sections stand at each stage of the pipeline for one question."""
    import lab03_hybrid, retriever
    answers = {f"{r['doc_id']}:{r['section']}" for r in item["relevant"] if r["grade"] == 2}
    p = dict(qvec=db.vec(embedder.embed_query(item["question"])), qtext=item["question"], roles=[item["role"]], docs=None, n=cfg["candidates"], rrf_k=cfg["rrf_k"])
    vec = [r[0] for r in con.execute(lab03_hybrid.VECTOR_SQL, p)]
    fts = [r[0] for r in con.execute(lab03_hybrid.FTS_SQL, p)]
    fused = [r[0] for r in con.execute(retriever.hybrid_sql(), p)]
    final = retriever.search(con, item["question"], item["role"], cfg, "hybrid_rerank")["results"]
    return dict(answers=sorted(answers), vector=first_rank(vec, answers), fts=first_rank(fts, answers), fused=first_rank(fused, answers),
                final=first_rank([r["chunk_key"] for r in final], answers), top=[r["chunk_key"] for r in final])

def main():
    import lab04_evaluate
    con = db.connect(); cfg = labkit.config()
    rows = [r for r in lab04_evaluate.evaluate(con, cfg, "hybrid_rerank") if r["answerable"]]
    gold = {g["qid"]: g for g in labkit.gold()}
    worst = sorted(rows, key=lambda r: (r["sufficient"], r["recall"], r["ndcg"], r["qid"]))[:10]
    failed = sum(1 for r in rows if not r["sufficient"])
    print(f"hybrid_rerank: {failed} of {len(rows)} answerable questions lack sufficient evidence in the top {cfg['k']}. The ten worst:\n")
    for r in worst:
        f = stage_facts(con, gold[r["qid"]], cfg)
        show = lambda x: "-" if x is None else str(x)
        print(f"{r['qid']} [{r['category']}] {r['question']}")
        print(f"    needs: {', '.join(f['answers'])}    evidence: {gold[r['qid']]['evidence']}")
        print(f"    recall {r['recall']:.2f}   nDCG {r['ndcg']:.2f}   sufficient {'yes' if r['sufficient'] else 'no'}")
        print(f"    best rank of an answering chunk: vector {show(f['vector'])}, full-text {show(f['fts'])}, fused top {cfg['candidates']} {show(f['fused'])}, after reranking {show(f['final'])} (top {cfg['rerank_top']} of the fused list are reranked)")
        print(f"    returned: {', '.join(f['top'])}\n")
    print("Fill in failure_analysis.md, then: python check.py 5")

if __name__ == "__main__":
    main()
