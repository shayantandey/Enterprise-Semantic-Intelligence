"""Consumer 1: SQL saved in a BI tool. A report writer wrote each query by hand against the warehouse.

Two of these queries do not agree with the semantic layer. Find out why, then fix them.
The report passes the user's stores in as a list, and the BI tool applies it to every query.
"""
from semantic_layer import connect

SQL = {
    "orders": """
        SELECT COUNT(*) FROM sem_orders t
        WHERE t.date_day >= :start AND t.date_day < :end AND {filters}
    """,
    "gross_sales": """
        SELECT SUM(o.gross_amount) FROM fct_orders o
        JOIN sem_orders t ON t.order_id = o.order_id
        WHERE o.order_ts >= :start AND o.order_ts <= :last_day AND {filters}
    """,
    "average_order_value": """
        SELECT AVG(store_average) FROM (
            SELECT t.store_id, SUM(t.gross_amount) / COUNT(*) AS store_average
            FROM sem_orders t
            WHERE t.date_day >= :start AND t.date_day < :end AND {filters}
            GROUP BY t.store_id)
    """,
}


def get_metric(metric, start, end, where=None, user="finance"):
    con = connect()
    stores = [r[0] for r in con.execute("SELECT store_id FROM user_store_access WHERE user_name = ?", (user,))]
    filters = ["t.store_id IN ({})".format(", ".join(f"'{s}'" for s in stores))]
    for column, value in (where or {}).items():
        filters.append(f"t.{column} = '{value}'")
    last_day = con.execute("SELECT date(?, '-1 day')", (end,)).fetchone()[0]     # the report's date picker is inclusive
    sql = SQL[metric].format(filters=" AND ".join(filters))
    value = con.execute(sql, {"start": start, "end": end, "last_day": last_day}).fetchone()[0]
    con.close()
    return value or 0
