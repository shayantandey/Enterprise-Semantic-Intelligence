# Competency questions: medicine supply risk

A competency question is a question the knowledge graph must be able to answer. Each one names the things
and relationships the ontology has to contain. Four are written. Write four more for the case in
case_brief.md, then mark for each the classes and properties it needs.

| No. | Question | Classes and properties it needs |
|---|---|---|
| 1 | Which suppliers supply heparin sodium to which plants today? | Supplier, Component, Plant, SupplyAgreement, validFrom, validTo |
| 2 | Which components have a single supplier today? | SupplyAgreement, supplier, component, validFrom, validTo |
| 3 | Which critical products contain a sole-sourced component? | Product, critical, contains, SupplyAgreement |
| 4 | Who supplied heparin sodium a year ago but does not supply it today? | SupplyAgreement, validFrom, validTo |
| 5 | <your question> | <classes and properties> |
| 6 | <your question> | <classes and properties> |
| 7 | <your question> | <classes and properties> |
| 8 | <your question> | <classes and properties> |

Check each question: can it be answered with a list of things or a yes or no, does it name a time where time
matters, and would two people agree on whether an answer is right?
