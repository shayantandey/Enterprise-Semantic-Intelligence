# Decision record: retrieval architecture for policy search (Module 5)

Status: proposed
Date: TODO
Deciders: TODO

## Context

Contact-centre staff at Lakemont Bank (a fictional bank) search 23 current policy documents. The baseline is hybrid
retrieval in PostgreSQL (pgvector and full-text search, fused by reciprocal rank fusion) with a cross-encoder reranker,
measured on a 60-question gold set of which 55 have an answer the asker may read.

## Decision

TODO: the two options you switched on in retrieval_config.json, and in one sentence each what they change.

## Evidence

TODO: paste the three metric rows from lab06_changes.py with their differences and intervals. Name the questions that
gained sufficient evidence and any that lost it.

## Cost and trade-offs

TODO: latency, words returned per question (which become tokens for the answering model), indexing cost, and any
question the change made worse and why.

## What the gold set cannot tell us

TODO: what 55 questions written by one team do not show. Think about interval width, categories with 3 to 8 questions,
questions real agents ask that are not in the set, and documents not yet in the corpus.

## Revisit when

TODO: the events that should cause this decision to be measured again.
