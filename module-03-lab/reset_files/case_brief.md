# Case brief: finance revenue reconciliation across three reports (fictional, written for this course)

The retailer from Module 1 closes fiscal Q2 of FY26-27 (July to September 2026). Three reports show net revenue
for the quarter, and no two agree.

| Report | Owner | Figure | How it is built |
|---|---|---|---|
| Finance month-end pack | finance controller | 643,813.12 | The semantic layer's net_revenue, version 2: gross sales less discounts less refunds, refunds dated by return date |
| Sales dashboard | head of sales operations | 802,801.87 | SQL in the BI tool: orders joined to returns, refunds dated by order date, discounts not deducted |
| E-commerce weekly export | e-commerce lead | 769,213.37 | A scheduled query: amount charged including tax, less refunds, filtered on the order timestamp up to '2026-09-30' |

The finance controller has to sign the investor presentation in four days. The head of sales operations has already
quoted the dashboard figure to the regional managers.

Run `python case_reconciliation.py` to see each figure rebuilt from the lab warehouse and reconciled step by step.
