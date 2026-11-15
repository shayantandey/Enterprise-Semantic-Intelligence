"""Lab 1: count "active customers" three ways, then count people.

Run:  python lab1_three_definitions.py
Each function returns one SQL query. The marketing and customer service queries are written for you.
Write the other two, run the script, and compare the four numbers.
"""
import sqlite3
from pathlib import Path

REPORT_DATE = "2026-10-31"
DB = Path(__file__).with_name("retail.db")


def marketing_sql():
    """Marketing: a CRM profile seen in the last 90 days."""
    return f"""
        SELECT COUNT(*) FROM crm_customers
        WHERE last_seen_date >= date('{REPORT_DATE}', '-90 day')
    """


def finance_sql():
    """Finance: an ERP billing account with at least one PAID order in the last 12 months."""
    # TODO: count distinct erp_id in orders where payment_status is 'PAID' and order_date is within 12 months of REPORT_DATE
    raise NotImplementedError("see the TODO comment")


def service_sql():
    """Customer service: a CRM account row whose status flag is ACTIVE."""
    return "SELECT COUNT(*) FROM crm_customers WHERE status = 'ACTIVE'"


def marketing_people_sql():
    """Marketing's definition again, counted per person as far as the crosswalk allows.

    The crosswalk maps a CRM id to a golden key for about 60 percent of customers.
    Count distinct golden keys, and fall back to the crm_id where there is no golden key.
    """
    # TODO: LEFT JOIN crm_customers to crosswalk (source_system = 'CRM') and count DISTINCT COALESCE(golden_key, crm_id)
    raise NotImplementedError("see the TODO comment")


def main():
    if not DB.exists():
        raise SystemExit("retail.db not found. Run: python setup_warehouse.py")
    con = sqlite3.connect(DB)
    rows = [("Marketing: seen in 90 days, per CRM profile", marketing_sql),
            ("Finance: paid order in 12 months, per ERP account", finance_sql),
            ("Service: status flag ACTIVE, per account row", service_sql),
            ("Marketing's definition, counted per person", marketing_people_sql)]
    for label, fn in rows:
        try:
            value = con.execute(fn()).fetchone()[0]
        except NotImplementedError:
            value = f"not written yet: {fn.__name__}()"
        print(f"{label:52} {value}")
    con.close()


if __name__ == "__main__":
    main()
