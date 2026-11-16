# Case brief: customers indirectly exposed to a supplier disruption (fictional, written for this course)

A medicine manufacturer runs four plants and sells to hospitals, pharmacy chains and distributors.
On 20 October 2026 a regulator places an import alert on the manufacturing site of Baltic Synthesis,
which supplies heparin sodium, the active ingredient of two injectable products. The notice arrives
as a PDF and is read by an extraction model, which records it with a confidence of 0.93.

No customer buys from Baltic Synthesis. A customer is exposed indirectly: Baltic Synthesis supplies a
component to a plant, the plant makes products that contain it, and the products are shipped to the customer.

The head of supply chain asks three questions on 1 November 2026:

1. Which plants and products depend on Baltic Synthesis today?
2. Which customers received those products in the last 90 days, and which of the products are critical?
3. Is there another supplier we have used before for the same component?

The ERP knows vendors by vendor number, and one supplier has two numbers. The quality system knows
suppliers by a different identifier. Master data links both to one golden key per supplier.
