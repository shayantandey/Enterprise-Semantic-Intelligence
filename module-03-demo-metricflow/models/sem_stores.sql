select store_id, store_name, region from {{ ref('dim_store') }}
