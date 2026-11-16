# Competency questions: medicine supply risk (sample answer for questions 5 to 8)

| No. | Question | Classes and properties it needs |
|---|---|---|
| 5 | Which organizations of any kind are in the graph? | Organization and its subclasses |
| 6 | Which customers are exposed today to a disruption at a named supplier, through the plants it supplies and the products made there? | Supplier, SupplyAgreement, Plant, Product, madeAt, contains, Shipment, toCustomer, shipDate, Customer |
| 7 | Which customers have ever received a critical product? | Customer, receives, Product, critical |
| 8 | Which disruption notices concern a supplier with an agreement in force today, and what document does each rest on? | DisruptionNotice, aboutSupplier, wasDerivedFrom, extractionConfidence, SupplyAgreement |

These are the questions that queries/cq5.rq to cq8.rq answer. Other questions are equally valid if they can be
answered with a list or a yes or no, name a time where time matters, and can be checked.
