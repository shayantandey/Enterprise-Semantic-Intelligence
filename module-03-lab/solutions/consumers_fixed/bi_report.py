"""Consumer 1, fixed. Both queries now use the layer's conventions: a date column with an exclusive end,
and a ratio computed from the summed numerator and denominator."""
from semantic_layer import connect

SQL = {
    "orders": """
        SELECT COUNT(*) FROM sem_orders t
        WHERE t.date_day >= :start AND t.date_day < :end AND {filters}
    """,
    "gross_sales": """
        SELECT SUM(t.gross_amount) FROM sem_orders t
        WHERE t.date_day >= :start AND t.date_day < :end AND {filters}
    """,
    "average_order_value": """
        SELECT SUM(t.gross_amount) / COUNT(*) FROM sem_orders t
        WHERE t.date_day >= :start AND t.date_day < :end AND {filters}
    """,
}


def get_metric(metric, start, end, where=None, user="finance"):
    con = connect()
    stores = [r[0] for r in con.execute("SELECT store_id FROM user_store_access WHERE user_name = ?", (user,))]
    filters = ["t.store_id IN ({})".format(", ".join(f"'{s}'" for s in stores))]
    for column, value in (where or {}).items():
        filters.append(f"t.{column} = '{value}'")
    sql = SQL[metric].format(filters=" AND ".join(filters))
    value = con.execute(sql, {"start": start, "end": end}).fetchone()[0]
    con.close()
    return value or 0
