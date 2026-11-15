-- One row per store, product and day: units on hand at the end of the day.
select store_id || '-' || product_id || '-' || cast(snapshot_date as varchar) as snapshot_key,
       cast(snapshot_date as date) as date_day, store_id, product_id, units_on_hand
from {{ ref('fct_inventory_snapshot') }}
