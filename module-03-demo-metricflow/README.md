# Module 3 facilitator demonstration: the same metrics in dbt and MetricFlow

This folder is for the facilitator. Participants do not need it. It defines the lab's metrics in a dbt
project and queries them with MetricFlow, on the same fictional data as the Python lab, so that the
class can see a production semantic layer return the figures their own lab returned.

It needs packages from PyPI, so it has a `requirements.txt`. The versions in it are the ones the demo was
written and run with: dbt Core 1.12.7, dbt-duckdb 1.11.1, dbt-metricflow 0.15.0, MetricFlow 0.213.0 and DuckDB 2.0.0 on Python 3.13.
The database is DuckDB, which is a file, so there is no database server.

## Option A: a Python virtual environment

    python -m venv .venv
    source .venv/bin/activate          (Windows: .venv\Scripts\activate)
    pip install -r requirements.txt
    export DBT_PROFILES_DIR=.          (Windows PowerShell: $env:DBT_PROFILES_DIR=".")
    dbt build
    mf validate-configs

## Option B: Docker

    docker build -t esi-metricflow-demo .
    docker run -it --rm esi-metricflow-demo

The image installs the packages and runs `dbt build`, and the container opens a shell in which the `mf`
commands below work. The Dockerfile was written with the demo and has not been run under Docker by the
author of this material, so build it once before the session.

## Queries to show

    mf list metrics
    mf query --metrics orders,gross_sales,refunds,net_revenue --decimals 2 --group-by metric_time__fiscal_quarter --order metric_time__fiscal_quarter
    mf query --metrics net_revenue --group-by metric_time__fiscal_quarter --explain
    mf query --metrics average_order_value --start-time 2026-04-01 --end-time 2026-06-30
    mf query --metrics inventory_units --group-by metric_time__month --order metric_time__month
    mf query --metrics gross_sales,gross_sales_ytd --group-by metric_time__month --start-time 2026-01-01 --end-time 2026-06-30 --order metric_time__month
    mf query --metrics net_revenue --group-by store__region --start-time 2026-07-01 --end-time 2026-09-30 --order store__region
    mf query --metrics gross_sales,business_gross_sales,gross_sales_change_on_prior_month --group-by metric_time__month --start-time 2026-04-01 --end-time 2026-06-30 --order metric_time__month

If time is short, show the first three.

What to point out:

- The second query returns the orders, gross sales and refunds that the Python lab returns. Net revenue is version 2 of the lab's definition applied to every quarter, so it equals the lab's "version 2 restated" series: 643,813.12 for FY26-27 Q2.
- `--explain` prints the SQL. Orders and returns are each aggregated in their own subquery and then joined on the quarter, so no order row is repeated.
- `--end-time` is inclusive in MetricFlow. The Python lab's `end` is exclusive. That difference is a time-boundary convention of the kind exercise 4 tests.
- `inventory_units` uses `non_additive_dimension`, so a month shows the last day's stock and not the sum of the days.
- `gross_sales_ytd` sets `period_agg: last`. Without it, a month shows the running total as of the first day of the month.
- The last query shows a metric with a filter in its definition and a derived metric with `offset_window`. April's change of 21,750 is April less March.
- After `dbt build`, `target/semantic_manifest.json` holds the compiled semantic model and `target/osi_document.json` holds an Open Semantic Interchange document.

## Differences from the Python lab

- The demo holds one definition of net revenue (version 2). MetricFlow has no effective-dated versions of a metric, so the lab's version switch has no counterpart here.
- The cumulative metric accumulates gross sales over the calendar year. With these versions, `grain_to_date` rejected the custom granularity `fiscal_year`, and a cumulative metric over the derived metric `net_revenue` failed at query time.
- `store__region` is the store's current region. The region on the order date is the dimension `order__region_on_order_date`, which applies to order metrics only.
- There is no security context. Row-level security belongs to the database and to the service that runs the queries, and DuckDB in this demo has neither.

## Refreshing the data

The CSV files in `seeds` were exported from the lab warehouse. To export them again:

    python export_seeds.py ../module-03-lab/metrics.db
