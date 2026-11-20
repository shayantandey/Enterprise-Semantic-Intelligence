# ADR 4: retrieval or graph traversal for relationship questions

Status: proposed
Date: TODO
Deciders: TODO

## Context

Executives at Corvane Pharma (a fictional company) ask the assistant who supplies which plant, which products depend on a
supplier and where a component has only one source. Two components could answer such questions: retrieval over documents
(Module 5) and queries over the supply graph (Module 4). The router has to send each kind of question to one of them.

## Decision

TODO: which component answers relationship questions, which answers questions about rules, and what the router does with a
question that needs both.

## Evidence

TODO: results of lab06_adr4.py, in the form "4 of 6 found, 0 wrong", for at least two questions and both methods. Say what
the retrieved memo is and why its answers are incomplete or wrong. State the two limits of the comparison: what the document
index lacks, and where the right answers come from.

## Consequences

TODO: what the decision costs. Think about who keeps the graph current, how the graph's own accuracy will be checked, what
happens to a relationship that is only written in a document, and what the answer must show so that a reader can check an
inferred relationship.

## When retrieval is the right tool

TODO: the kinds of question that still go to documents, with one example from the validation set.

## Revisit when

TODO: the events that should cause this decision to be looked at again.
