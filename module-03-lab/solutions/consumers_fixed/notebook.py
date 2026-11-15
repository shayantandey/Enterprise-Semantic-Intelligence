"""Consumer 2, fixed. The notebook now applies the user's store access and filters on the region as it was
on the order date. The shorter fix is to call the semantic layer and delete this code:

    from consumers.api import get_metric
"""
from semantic_layer import connect


def load_orders(start, end, user):
    con = connect()
    rows = con.execute("""SELECT order_id, store_id, region, region_current, segment, gross_amount
                          FROM sem_orders WHERE date_day >= ? AND date_day < ?
                          AND store_id IN (SELECT store_id FROM user_store_access WHERE user_name = ?)""", (start, end, user)).fetchall()
    con.close()
    return [dict(zip(("order_id", "store_id", "region", "region_current", "segment", "gross_amount"), r)) for r in rows]


def get_metric(metric, start, end, where=None, user="finance"):
    orders = load_orders(start, end, user)
    for column, value in (where or {}).items():
        orders = [o for o in orders if o[column] == value]
    if metric == "orders":
        return len(orders)
    if metric == "gross_sales":
        return sum(o["gross_amount"] for o in orders)
    if metric == "average_order_value":
        return sum(o["gross_amount"] for o in orders) / len(orders) if orders else 0
    raise ValueError(f"the notebook does not compute {metric}")
