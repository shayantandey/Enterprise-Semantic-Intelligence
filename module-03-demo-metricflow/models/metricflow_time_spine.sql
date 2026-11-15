select cast(date_day as date) as date_day, fiscal_quarter, fiscal_year from {{ ref('dim_date') }}
