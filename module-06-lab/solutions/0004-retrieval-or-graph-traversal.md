# ADR 4: retrieval or graph traversal for relationship questions

Status: proposed
Date: 20 November 2026
Deciders: worked answer for the Module 6 lab

## Context

Executives at Corvane Pharma (a fictional company) ask the assistant who supplies which plant, which products depend on a
supplier and where a component has only one source. Two components could answer such questions: retrieval over documents
(Module 5) and queries over the supply graph (Module 4). The router has to send each kind of question to one of them.

## Decision

Questions about relationships between suppliers, plants, components and products go to the graph tool, which runs a named
SPARQL query over agreements in force. Questions about rules, definitions, thresholds and approvals go to retrieval over
the policy documents. A question that needs both, such as which suppliers breach the termination policy, is decomposed:
the rule comes from the documents and the facts it is applied to come from the graph and the metrics layer.

## Evidence

lab06_adr4.py answered six relationship questions both ways, against the agreements in force on 1 November 2026.

| Question | Top retrieved passage | Graph |
|---|---|---|
| Suppliers of the Ahmedabad plant | 4 of 6 found, 0 wrong | 6 of 6 found, 0 wrong |
| Suppliers of the Hyderabad plant | 2 of 4 found, 1 wrong | 4 of 4 found, 0 wrong |
| Plants Baltic Synthesis supplies | 1 of 2 found, 0 wrong | 2 of 2 found, 0 wrong |
| Products with a component from Baltic Synthesis | 0 of 2 found, 0 wrong | 2 of 2 found, 0 wrong |
| Suppliers of the Visakhapatnam plant | 3 of 4 found, 1 wrong | 4 of 4 found, 0 wrong |

The passage retrieved every time is a memo written for the plant reviews of March 2025. It covers two of the four plants,
names Sagar Pharma Ingredients as a paracetamol supplier to Hyderabad although that agreement ended on 30 September 2025,
and says nothing about products. Retrieval returned the most similar text there was, and the text was incomplete and out
of date. A complete answer to "which" needs a source that holds every instance, and the graph is that source.

Two limits of this evidence. The document index holds no current supplier list, so retrieval was tested on a poor corpus,
and it was scored on its single top passage. And the right answers were computed from the same agreement list that the
graph is loaded from, so the graph's scores show that the query and the property chain work. They do not show that the
agreement data is right.

## Consequences

The graph must be loaded from the agreement system on a schedule, with an owner, because the assistant now presents its
content as current. Its accuracy has to be checked against something other than itself: each quarter procurement confirms
a sample of plants against the supplier list the graph returns, and the result is published with the load date. A relationship that exists only in a contract or an email is invisible to the graph tool until someone
models it. The answer labels "supplies plant" as an inferred relationship, so the query that lists the underlying
agreements has to be offered beside it for a reader who wants to check. The graph tool runs named queries only, which
limits it to the relationships someone has written a query for; a new kind of question needs a new query and a review.

## When retrieval is the right tool

Rules and definitions: "What notice applies to termination for cause?" (V22) and "Who approves a termination for cause?"
(V21) are answered from the termination policy with a verified quote. The graph holds no policy text. Retrieval is also the
fallback for narrative context, provided the answer shows the document's date.

## Revisit when

A graph query generator replaces the named queries; contract terms are modelled in the graph for more roles; a second
document source with current supply data is indexed; the validation set gains relationship questions the graph cannot answer.
