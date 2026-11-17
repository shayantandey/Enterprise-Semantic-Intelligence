# ADR 3: Physical or virtual knowledge graph

## Status
Proposed

## Context
- Fact: in exercise 10 the physical graph answered cq1 in about 12 ms. The virtual graph took about 10 seconds for the same answer, over CSV files with no indexes.
- Fact: an agreement added to the warehouse appeared in the virtual graph at once and in the physical graph only after the next load.
- Fact: three of the eight competency questions (cq5, cq6 and cq7) return nothing without inference, and the case study question, cq6, is one of them. The virtual repository returned no organizations at all for a class the data does not state.
- Fact: in exercise 7 GraphDB rejected a batch with an unmatched vendor, a malformed date and an unknown component. The virtual repository is read-only and has no write at which to reject anything.
- Fact: the virtual engine refused FILTER NOT EXISTS, so cq4 had to be rewritten with MINUS.
- Assumption: exposure questions are asked after a notice arrives, so a graph that is a few hours old is acceptable if its age is shown.

## Decision
We will build a physical graph in GraphDB for suppliers, agreements, plants, products, customers and notices, loaded nightly with SHACL validation on every load, and we will add a virtual repository over the shipments table only if users need shipments from the current day.
We considered a fully virtual graph and rejected it because the risk questions depend on class and property inference and on validated golden keys, and the virtual repository provided neither.

## Consequences
- Easier: inference and validation on the whole graph, fast path queries, and history kept through validity periods.
- Harder: a load and a refresh to operate and monitor, and answers that are as old as the last load, so every answer has to show the graph's currency.
- Revisit if: users need exposure answers within minutes of a new agreement or shipment, or the nightly load starts to fail often enough that the graph is stale for days.
