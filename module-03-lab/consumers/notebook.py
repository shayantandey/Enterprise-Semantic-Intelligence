"""Consumer 2: an analyst's notebook. It reads rows from the warehouse and computes the metric in Python.

Two things in this file make its numbers differ from the semantic layer. Find out why, then fix them.
Hint for the case with a restricted user: the stores a user may see are in the table user_store_access
(columns user_name and store_id). load_orders() can take the user and add a condition on store_id.
"""
from semantic_layer import connect


def load_orders(start, end):
    con = connect()
    rows = con.execute("""SELECT order_id, store_id, region, region_current, segment, gross_amount
                          FROM sem_orders WHERE date_day >= ? AND date_day < ?""", (start, end)).fetchall()
    con.close()
    return [dict(zip(("order_id", "store_id", "region", "region_current", "segment", "gross_amount"), r)) for r in rows]


def get_metric(metric, start, end, where=None, user="finance"):
    orders = load_orders(start, end)
    for column, value in (where or {}).items():
        if column == "region":
            column = "region_current"          # the analyst's region lookup came from the current store list
        orders = [o for o in orders if o[column] == value]
    if metric == "orders":
        return len(orders)
    if metric == "gross_sales":
        return sum(o["gross_amount"] for o in orders)
    if metric == "average_order_value":
        return sum(o["gross_amount"] for o in orders) / len(orders) if orders else 0
    raise ValueError(f"the notebook does not compute {metric}")
