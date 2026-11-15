-- One row per return. An order can have several returns, on different dates.
select r.return_id, r.order_id, o.customer_id, o.store_id, cast(r.return_date as date) as date_day, r.refund_amount
from {{ ref('fct_returns') }} r
join {{ ref('fct_orders') }} o on o.order_id = r.order_id
where o.status = 'COMPLETED'
