# Decision record: retrieval architecture for policy search (Module 5)

Status: proposed
Date: 18 November 2026
Deciders: worked answer for the Module 5 lab

## Context

Contact-centre staff at Lakemont Bank (a fictional bank) search 23 current policy documents. The baseline is hybrid
retrieval in PostgreSQL (pgvector and full-text search, fused by reciprocal rank fusion) with a cross-encoder reranker,
measured on a 60-question gold set of which 55 have an answer the asker may read.

## Decision

Switch on contextual_headers and parent_child. contextual_headers puts the document title and section heading in front
of each chunk before it is embedded, indexed for full-text search and read by the reranker. parent_child returns the
whole section for each matched chunk, one result per section.

## Evidence

Run with the local embedding model BAAI/bge-small-en-v1.5, hybrid_rerank, 55 answerable questions.

| Metric | Baseline | Changed | Difference and 95 percent interval |
|---|---|---|---|
| recall@5 | 0.909 | 0.982 | +0.073 [+0.018, +0.145] |
| nDCG@5 | 0.811 | 0.954 | +0.142 [+0.073, +0.220] |
| evidence sufficiency | 0.836 | 0.982 | +0.145 [+0.055, +0.236] |

All three intervals exclude zero. Questions that gained sufficient evidence: Q11, Q25, Q28, Q40, Q51, Q54, Q57, Q58.
None lost it. Q27 still fails: the question says "chargeback" and "closed", and the reranker prefers account-closure
paragraphs. Leaks stayed at 0.

## Cost and trade-offs

contextual_headers is an index-time change: all 127 chunks were embedded again, which took 18 seconds here and would be a
planned migration on a large corpus. Words returned per question rose from 230 to 274, about a fifth more input for any
answering model, on every question. Median latency rose from about 800 to about 920 ms on a CPU, since the reranker
reads longer texts. The metadata filter was not chosen: it fixes several of the same questions and removes the answer to
Q38, which asks about a process that applies to a product. glossary_expansion would fix Q27 and is the next candidate.

## What the gold set cannot tell us

The lower end of the interval for the gain in evidence sufficiency is 5.5 points, so the true gain may be much smaller
than 14.5. Categories have 3 to 15 questions, so no rate per category can be quoted. The questions were written by the
project team with the documents in view and may not match what agents ask. The same 55 questions were used to choose
the change and to measure it, so the result on new questions will be lower. Zero leaks on three probing questions
does not show that entitlement works for every restricted document and role.

## Revisit when

A new product family with a different document template is added; the embedding model changes; 200 logged agent
questions have been judged; an answering model is placed on top (Module 6), when the extra words become a cost per call.
