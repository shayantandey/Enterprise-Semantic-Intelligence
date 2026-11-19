"""Checks for the lab exercises.  Run:  python check.py 1     (or 2, 3, 4, 5, 6)

Each check tests the function you wrote on small cases with known answers, then looks at the index in PostgreSQL."""
import json, math, random, re, sys
from pathlib import Path
LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB))
import db, labkit

results = []
def check(name, good, hint=""):
    results.append(good)
    print(("  pass  " if good else "  FAIL  ") + name + ("" if good or not hint else f"\n        hint: {hint}"))

def attempt(fn, *args):
    """Call a participant's function. Returns (value, None) or (None, text describing what went wrong)."""
    try:
        return fn(*args), None
    except NotImplementedError:
        return None, "the TODO is not written yet"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

def check1():
    import lab01_enrich as L
    g = [dict(term_id="G1", preferred_term="late payment charge", synonyms=["late fee", "overdue fee"]),
         dict(term_id="G2", preferred_term="tax deducted at source", synonyms=["TDS"]),
         dict(term_id="G3", preferred_term="prepayment", synonyms=["foreclosure"])]
    for text, want, why in (("A Late Fee applies after the due date.", ["G1"], "match synonyms, ignoring case"),
                            ("Prepayment and foreclosure are the same thing; TDS is separate.", ["G2", "G3"], "each id once, sorted"),
                            ("The outdsx counter and the plate fees.", [], "whole words only: use \\b on both sides"),
                            ("Tax deducted at source, also the late payment charge.", ["G1", "G2"], "match the preferred term too")):
        got, err = attempt(L.glossary_terms_in, text, g)
        check(f"glossary_terms_in: {why}", got == want, err or f"for {text!r} expected {want}, got {got}")
    got, err = attempt(L.allowed_roles_for, {"doc_id": "X", "audience": ["team_lead", "agent", "agent"]})
    check("allowed_roles_for: returns the audience, sorted, each role once", got == ["agent", "team_lead"], err or f"got {got}")
    for meta in ({"doc_id": "X", "audience": []}, {"doc_id": "X"}):
        got, err = attempt(L.allowed_roles_for, meta)
        check(f"allowed_roles_for: refuses a document with {'an empty' if 'audience' in meta else 'no'} audience", bool(err) and err.startswith("ValueError"), "raise ValueError, do not return an empty list or a default role")
    con = db.connect()
    if not con.execute("SELECT to_regclass('chunks')").fetchone()[0]:
        return check("the index exists", False, "run python lab01_enrich.py")
    n, = con.execute("SELECT count(*) FROM chunks").fetchone()
    check(f"the index holds the chunks of the corpus ({n})", n in (130, 127), "run python lab01_enrich.py")
    bad, = con.execute("SELECT count(*) FROM chunks WHERE cardinality(allowed_roles) = 0").fetchone()
    check("every chunk has at least one entitlement tag", bad == 0)
    r = con.execute("SELECT allowed_roles FROM chunks WHERE doc_id='FRAUD-PLAYBOOK' LIMIT 1").fetchone()
    check("fraud playbook chunks are tagged fraud_analyst and team_lead only", bool(r) and r[0] == ["fraud_analyst", "team_lead"], f"got {r and r[0]}")
    r = con.execute("SELECT glossary_terms, fts_extra FROM chunks WHERE chunk_key='PL-STD:prepayment:0'").fetchone()
    check("the personal loan prepayment chunk carries term G04 and its synonyms for full-text search", bool(r) and "G04" in r[0] and "foreclosure" in r[1], f"got {r}")

def check2():
    import lab02_refresh as L
    got, err = attempt(L.plan_changes, {"a": "1", "b": "2", "c": "3"}, {"a": "1", "b": "9", "d": "4"})
    check("plan_changes: changed and new chunks are embedded, the same ones kept, missing ones deleted", got == (["b", "d"], ["a"], ["c"]), err or f"expected (['b', 'd'], ['a'], ['c']), got {got}")
    got, err = attempt(L.plan_changes, {}, {"x": "1"})
    check("plan_changes: an empty index means everything is embedded", got == (["x"], [], []), err or f"got {got}")
    con = db.connect()
    v = con.execute("SELECT DISTINCT version FROM chunks WHERE doc_id='CC-GOLD'").fetchall()
    check("the index holds version 4 of CC-GOLD and no other version", v == [(4,)], f"versions in the index: {[x[0] for x in v]}. Run python lab02_refresh.py")
    r = con.execute("SELECT text FROM chunks WHERE chunk_key='CC-GOLD:late:1'").fetchone()
    check("the late payment table shows the new charge of 900", bool(r) and "Charge (INR): 900" in r[0])
    n, = con.execute("SELECT count(*) FROM chunks c FULL JOIN documents d USING (doc_id) WHERE doc_id='PROMO-FESTIVE'").fetchone()
    check("the withdrawn offer is gone from chunks and from documents", n == 0, "write withdraw() and run python lab02_refresh.py")
    r = con.execute("SELECT embedded, kept FROM index_runs WHERE note LIKE 'lab 2%' ORDER BY run_id DESC LIMIT 1").fetchone()
    check("the refresh embedded only the chunks that changed (2 embedded, 7 kept)", r == (2, 7), f"the last refresh embedded {r and r[0]} and kept {r and r[1]}. If you ran it twice, the second run correctly embeds 0: reset with python lab01_enrich.py and run lab 2 once")

def check3():
    import lab03_hybrid as L, embedder
    sql, err = attempt(L.hybrid_sql)
    if err: return check("hybrid_sql returns a statement", False, err)
    con = db.connect()
    for question, role in (("How much is the bounce charge on a home loan EMI?", "agent"), ("What does CHG-104 cost?", "agent"), ("Which hold code do I place for a suspected account takeover?", "fraud_analyst")):
        p = dict(qvec=db.vec(embedder.embed_query(question)), qtext=question, roles=[role], docs=None, n=40, rrf_k=60)
        try:
            cur = con.execute(sql, p); cols = [d.name for d in cur.description]; got = cur.fetchall()
        except Exception as e:
            return check("the statement runs", False, f"{type(e).__name__}: {str(e)[:300]}")
        check("columns are chunk_key and score", cols == ["chunk_key", "score"], f"got {cols}")
        want = {}
        for s in (L.VECTOR_SQL, L.FTS_SQL):
            for key, rank in con.execute(s, p): want[key] = want.get(key, 0) + 1.0 / (60 + rank)
        order = sorted(want, key=lambda k: (-want[k], k))[:40]
        close = len(got) == len(order) and all(abs(float(s) - want.get(k, -1)) < 1e-9 for k, s in got)
        check(f"scores equal reciprocal rank fusion of the two lists: {question[:40]}...", close, "score = sum of 1.0 / (rrf_k + rank) over the lists a chunk appears in; cut each list at n before fusing")
        check("rows are ordered by score, highest first", [float(s) for _, s in got] == sorted((float(s) for _, s in got), reverse=True))
    p = dict(qvec=db.vec(embedder.embed_query("hold code HLD-21 account takeover")), qtext="hold code HLD-21 account takeover", roles=["agent"], docs=None, n=40, rrf_k=60)
    leaked = [k for k, _ in con.execute(sql, p) if k.startswith(("FRAUD", "FEE-WAIVER", "HARDSHIP"))]
    check("an agent gets no chunk from a restricted document", not leaked, f"returned {leaked}: BOTH branches need the entitlement filter")
    p.update(roles=["fraud_analyst"], docs=["FRAUD-PLAYBOOK"])
    only = {k.split(":")[0] for k, _ in con.execute(sql, p)}
    check("the docs parameter restricts both branches", only == {"FRAUD-PLAYBOOK"}, f"documents returned: {sorted(only)}")

def check4():
    import lab04_evaluate as L
    rel = {"A:x": 2, "B:y": 2, "C:z": 1}
    for args, want, why in ((( ["A:x", "Q:q", "C:z", "B:y"], rel, 3), 0.5, "one of two grade-2 sections in the top 3"),
                            ((["A:x", "Q:q", "C:z", "B:y"], rel, 5), 1.0, "both in the top 5"),
                            ((["C:z"], rel, 5), 0.0, "a grade-1 section does not count")):
        got, err = attempt(L.recall_at_k, *args)
        check(f"recall_at_k: {why}", got is not None and abs(got - want) < 1e-9, err or f"expected {want}, got {got}")
    got, err = attempt(L.recall_at_k, ["A:x"], {"C:z": 1}, 5)
    check("recall_at_k: raises ValueError when no section has grade 2", bool(err) and err.startswith("ValueError"))
    ideal = 3 / 1 + 3 / math.log2(3) + 1 / 2
    for retrieved, want, why in ((["A:x", "B:y", "C:z"], 1.0, "the ideal order scores 1"),
                                 (["Q:q", "A:x"], (3 / math.log2(3)) / ideal, "an answer at position 2 only"),
                                 (["C:z", "A:x", "B:y"], (1 + 3 / math.log2(3) + 3 / 2) / ideal, "graded gains 2**g - 1"),
                                 (["Q:q", "R:r"], 0.0, "nothing relevant scores 0")):
        got, err = attempt(L.ndcg_at_k, retrieved, rel, 5)
        check(f"ndcg_at_k: {why}", got is not None and abs(got - want) < 1e-9, err or f"expected {want:.4f}, got {got}")
    vals = [1.0] * 40 + [0.0] * 15
    rng = random.Random(5); means = sorted(sum(rng.choices(vals, k=55)) / 55 for _ in range(2000))
    got, err = attempt(L.bootstrap_ci, vals)
    check("bootstrap_ci: the interval for 40 hits in 55 questions", got is not None and abs(got[0] - means[50]) < 1e-9 and abs(got[1] - means[1949]) < 1e-9,
          err or f"expected ({means[50]:.3f}, {means[1949]:.3f}), got {got}. Use random.Random(seed).choices(values, k=len(values)), 2000 times, and positions 50 and 1949 of the sorted means")
    got, err = attempt(L.bootstrap_ci, [0.5] * 20)
    check("bootstrap_ci: identical values give an interval of zero width", got == (0.5, 0.5), err or f"got {got}")
    f = LAB / "results" / "last_eval.json"
    check("results/last_eval.json exists (python lab04_evaluate.py has been run)", f.exists())

STAGES = ["candidates", "fusion", "reranking", "chunking", "none"]
def check5():
    text = (LAB / "failure_analysis.md").read_text(encoding="utf-8")
    rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in text.splitlines() if re.match(r"\|\s*Q\d\d", ln)]
    check(f"the table has ten question rows ({len(rows)} found)", len(rows) == 10)
    filled = [r for r in rows if len(r) >= 5 and r[2] and r[3] and r[4]]
    check(f"every row has a stage, a cause and a change ({len(filled)} of {len(rows)} filled)", len(filled) == len(rows) and bool(rows))
    bad = [r[0] for r in filled if r[2].lower() not in STAGES]
    check("each stage is one of: " + ", ".join(STAGES), not bad, f"rows with another value: {bad}")
    names = ["contextual_headers", "parent_child", "glossary_expansion", "metadata_filter", "decompose", "none"]
    bad = [r[0] for r in filled if not any(n in r[4] for n in names)]
    check("each change names an option of retrieval_config.json, or none", not bad, f"rows without one: {bad}")
    m = re.search(r"## The two changes I will make\s+(.+?)(\n## |\Z)", text, re.S)
    check("the section 'The two changes I will make' is written", bool(m) and len(m.group(1).split()) >= 25 and "TODO" not in m.group(1))

def check6():
    cfg = labkit.config()
    on = [o for o in ("contextual_headers", "parent_child", "glossary_expansion", "metadata_filter", "decompose") if cfg[o]]
    check(f"exactly two options are switched on in retrieval_config.json ({', '.join(on) or 'none'})", len(on) == 2)
    text = (LAB / "adr" / "retrieval-architecture-decision.md").read_text(encoding="utf-8")
    check("the decision record has no TODO left", "TODO" not in text)
    for o in on:
        check(f"the decision record names the option {o}", o in text)
    for head, words in (("Decision", 20), ("Evidence", 30), ("Cost and trade-offs", 25), ("What the gold set cannot tell us", 25), ("Revisit when", 10)):
        m = re.search(rf"## {head}\s+(.+?)(\n## |\Z)", text, re.S)
        check(f"section '{head}' has at least {words} words", bool(m) and len(m.group(1).split()) >= words)
    m = re.search(r"## Evidence\s+(.+?)(\n## |\Z)", text, re.S)
    check("the evidence quotes a difference with its interval, such as +0.109 [+0.036, +0.200]", bool(m) and bool(re.search(r"[+-]0\.\d+\s*\[[+-]?0\.\d+,\s*[+-]?0\.\d+\]", m.group(1))))

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else ""
    if which not in "123456" or not which:
        sys.exit("Usage: python check.py N    where N is 1, 2, 3, 4, 5 or 6")
    globals()[f"check{which}"]()
    print(f"\n{sum(results)} of {len(results)} checks pass." + ("" if all(results) else "  A worked answer is in the solutions folder."))
    sys.exit(0 if all(results) else 1)
