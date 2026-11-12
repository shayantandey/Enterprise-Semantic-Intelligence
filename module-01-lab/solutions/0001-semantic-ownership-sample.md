# ADR 1: Ownership of semantics for the retailer

## Status
Proposed

## Context
- Fact: the quarterly investor presentation quotes active customers and net revenue, and the company is listed.
- Fact: the central data engineering team has nine people and takes about three weeks to deliver a change to a shared model.
- Fact: marketing asks for definition changes about twice a month. Customer service has no data staff.
- Fact: the customer master data hub covers about 60 percent of customers.
- Assumption: finance will name one owner for each term that appears in investor reporting.

## Decision
We will centralise a named core: the terms and metrics that appear in statutory accounts or the investor presentation are owned by finance and changed only through the central team. All other terms are owned and changed by the domain that uses them, under shared naming and identifier rules.
We considered full centralisation and rejected it because a three-week lead time against two marketing changes a month would push marketing back to private definitions.

## Consequences
- Easier: one audited definition of each investor-facing number, and marketing can change its own terms without a queue.
- Harder: someone has to decide which terms are in the core, and customer service needs a named steward it does not have today.
- Revisit if: master data coverage passes 90 percent, or the core grows beyond about 30 terms.
