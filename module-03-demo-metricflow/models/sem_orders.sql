-- One row per completed order. Dimensions are added through many-to-one joins only.
select o.order_id, o.customer_id, o.store_id, cast(o.order_date as date) as date_day,
       h.region as region_on_order_date, c.segment,
       o.gross_amount, o.discount_amount, o.tax_amount
from {{ ref('fct_orders') }} o
join {{ ref('dim_store_history') }} h
  on h.store_id = o.store_id and cast(o.order_date as varchar) >= h.valid_from and cast(o.order_date as varchar) < h.valid_to
join {{ ref('dim_customer') }} c on c.customer_id = o.customer_id
where o.status = 'COMPLETED'
