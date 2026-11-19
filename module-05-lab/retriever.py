"""The retrieval pipeline, provided. Lab 3 supplies the hybrid SQL; retrieval_config.json switches the architecture options.

search() returns {"results": [...], "trace": {...}, "seconds": float}. Each result is a dict with chunk_key, doc_id, version,
section, kind, text (what would be handed to the answering model), allowed_roles and score. The trace records the candidate
lists at each stage, which lab 5 uses to say where a failed query lost its evidence."""
import re, time
import db, embedder, labkit

MODES = ["vector", "fts", "hybrid", "hybrid_rerank"]
hybrid_sql = labkit.use("lab03_hybrid", "hybrid_sql")
_products = None
_checked = False

def _statements():
    import lab03_hybrid
    return {"vector": lab03_hybrid.VECTOR_SQL, "fts": lab03_hybrid.FTS_SQL, "hybrid": hybrid_sql(), "hybrid_rerank": hybrid_sql()}

def product_aliases(con):
    """{alias in lower case: doc_id} built from the documents table, for example 'plus savings' -> SAV-PLUS."""
    global _products
    if _products is None:
        _products = {}
        for doc_id, product in con.execute("SELECT doc_id, product FROM documents WHERE product LIKE 'Lakemont %'"):
            name = product[len("Lakemont "):].lower()
            for alias in {name, re.sub(r" (account|card)$", "", name), name.replace(" credit card", " card")}:
                _products[alias] = doc_id
    return _products

def detect_products(con, question):
    """doc_ids of the products named in the question, in order of appearance. Longer names win over the shorter names inside
    them, a plural s is allowed, and 'Classic and Platinum credit cards' names two products that share the words 'credit card'."""
    ql, hits, aliases = question.lower(), [], product_aliases(con)
    for alias, doc_id in sorted(aliases.items(), key=lambda kv: -len(kv[0])):
        m = re.search(r"\b" + re.escape(alias) + r"s?\b", ql)
        if m and not any(a <= m.start() < b for a, b, _ in hits):
            hits.append((m.start(), m.end(), doc_id))
            first, _, rest = alias.partition(" ")
            before = re.search(r"\b(\w+) and $", ql[:m.start()])
            if rest and before and f"{before.group(1)} {rest}" in aliases:
                hits.append((before.start(), before.start() + 1, aliases[f"{before.group(1)} {rest}"]))
    return list(dict.fromkeys(d for _, _, d in sorted(hits)))

def expand_with_glossary(question):
    """The question, plus a second wording in which each glossary synonym is replaced by the preferred term (multi-query)."""
    alt = question
    for g in labkit.glossary():
        for syn in sorted(g["synonyms"], key=len, reverse=True):
            alt = re.sub(r"\b" + re.escape(syn) + r"\b", g["preferred_term"], alt, flags=re.I)
    return [question] if alt == question else [question, alt]

def split_question(con, question):
    """Rule-based decomposition. Returns [(sub_question, [doc_id] or None), ...].
    Two products named: one sub-question per product, each restricted to that product's document.
    One product and two clauses joined by ', and': one sub-question per clause, both restricted to that product.
    Two clauses, no product: one sub-question per clause."""
    prods = detect_products(con, question)
    if len(prods) >= 2:
        return [(question, [p]) for p in prods]
    if ", and " in question:
        return [(part.strip(), prods or None) for part in question.split(", and ", 1)]
    return [(question, None)]

def _candidates(con, question, role, cfg, mode, docs):
    """Ranked chunk keys for the question. Returns (keys, the wording to give the reranker)."""
    sql = _statements()[mode]
    wordings = expand_with_glossary(question) if cfg["glossary_expansion"] else [question]
    lists = []
    for w in wordings:
        params = dict(qvec=db.vec(embedder.embed_query(w)), qtext=w, roles=[role], docs=docs, n=cfg["candidates"], rrf_k=cfg["rrf_k"])
        lists.append([r[0] for r in con.execute(sql, params).fetchall()])
    if len(lists) == 1: return lists[0], wordings[-1]
    score = {}
    for lst in lists:                                  # fuse the lists of the two wordings with reciprocal rank fusion
        for rank, key in enumerate(lst, 1): score[key] = score.get(key, 0) + 1.0 / (cfg["rrf_k"] + rank)
    return sorted(score, key=lambda k: (-score[k], k)), wordings[-1]      # the reranker reads the wording in the documents' own terms

def _one(con, question, role, cfg, mode, docs):
    keys, wording = _candidates(con, question, role, cfg, mode, docs)
    rows = {r[0]: r for r in con.execute("""SELECT chunk_key, doc_id, version, section, kind, text, parent_text, allowed_roles, search_text
                                            FROM chunks WHERE chunk_key = ANY(%s)""", (keys,)).fetchall()}
    cands = [rows[k] for k in keys]
    scores = [1.0 / (i + 1) for i in range(len(cands))]
    if mode == "hybrid_rerank" and cands:
        head = cands[:cfg["rerank_top"]]
        s = embedder.rerank(wording, [c[8] for c in head])       # the reranker reads the search text, which carries the headers when they are on
        order = sorted(range(len(head)), key=lambda i: -s[i])
        cands, scores = [head[i] for i in order], [s[i] for i in order]
    out, seen = [], set()
    for c, s in zip(cands, scores):
        unit = (c[1], c[3]) if cfg["parent_child"] else c[0]          # parent-child: one result per section, showing the whole section
        if unit in seen: continue
        seen.add(unit)
        out.append(dict(chunk_key=c[0], doc_id=c[1], version=c[2], section=c[3], kind=c[4],
                        text=c[6] if cfg["parent_child"] else c[5], allowed_roles=c[7], score=float(s)))
    return out, keys

def search(con, question, role, cfg=None, mode="hybrid_rerank"):
    global _checked
    if not _checked:
        db.check_model(con, embedder.DIM); _checked = True
    cfg = cfg or labkit.config(); t0 = time.perf_counter()
    subs = split_question(con, question) if cfg["decompose"] else [(question, None)]
    if cfg["metadata_filter"]:                         # restrict any sub-question that has no document filter yet
        named = detect_products(con, question) or None
        subs = [(sub, docs or named) for sub, docs in subs]
    per_sub, trace = [], {"subquestions": [], "candidates": []}
    for sub, docs in subs:
        res, keys = _one(con, sub, role, cfg, mode, docs)
        per_sub.append(res); trace["subquestions"].append((sub, docs)); trace["candidates"] += keys
    results, seen, i = [], set(), 0
    while len(results) < cfg["k"] and any(i < len(r) for r in per_sub):       # take results from the sub-questions in turn
        for r in per_sub:
            if i < len(r) and r[i]["chunk_key"] not in seen and len(results) < cfg["k"]:
                seen.add(r[i]["chunk_key"]); results.append(r[i])
        i += 1
    return {"results": results, "trace": trace, "seconds": time.perf_counter() - t0}
