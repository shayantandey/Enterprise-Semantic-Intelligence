"""Exercise 3 (self-study): a slowly changing dimension and a many-to-many relationship.

Run:  python lab3_scd_bridge.py
Part A needs no code. Store S03 moved from the South region to the West region on 1 July 2026.
The semantic model offers two region dimensions. Read the output and answer the question it asks.
Part B: an order can carry several promotions. You write the query that allocates an order's sales between them.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # find semantic_layer.py in the lab folder
from semantic_layer import connect, query, show

H1 = ("2026-04-01", "2026-10-01")


def part_a():
    print("Part A: gross sales by region for the first half of FY26-27")
    as_was = query(["gross_sales"], group_by=["fiscal_quarter", "region"], start=H1[0], end=H1[1])
    current = query(["gross_sales"], group_by=["fiscal_quarter", "region_current"], start=H1[0], end=H1[1])
    table = {}
    for r in as_was:
        table.setdefault((r["fiscal_quarter"], r["region"]), {})["region as it was on the order date"] = r["gross_sales"]
    for r in current:
        table.setdefault((r["fiscal_quarter"], r["region_current"]), {})["region as it is today"] = r["gross_sales"]
    rows = [{"fiscal_quarter": k[0], "region": k[1], **{c: v.get(c, 0.0) for c in ("region as it was on the order date", "region as it is today")}}
            for k, v in sorted(table.items())]
    show(rows)
    print("  Question: the South region manager's bonus depends on Q1 sales. Which column should the bonus report use, and why")
    print("  would the planning team, which sets next year's targets by region, choose the other one?")


def double_counted_sql():
    """Gross sales by promotion, joined through the bridge table. An order with two promotions is counted under both."""
    return """
        SELECT p.promo_name, COUNT(*) AS orders, SUM(o.gross_amount) AS gross_sales
        FROM fct_orders o
        JOIN bridge_order_promotion b ON b.order_id = o.order_id
        JOIN dim_promotion p ON p.promo_id = b.promo_id
        WHERE o.status = 'COMPLETED' AND o.order_date >= ? AND o.order_date < ?
        GROUP BY p.promo_name ORDER BY p.promo_name
    """


def allocated_sql():
    """Gross sales by promotion with each order's amount split equally between its promotions."""
    # Answer. Hint given: as double_counted_sql(), but divide o.gross_amount by the number of promotions on the order. Join a subquery (SELECT order_id, COUNT(*) AS n FROM bridge_order_promotion GROUP BY order_id) and sum o.gross_amount / n
    return """
        SELECT p.promo_name, COUNT(*) AS orders, SUM(o.gross_amount / n.n) AS gross_sales
        FROM fct_orders o
        JOIN bridge_order_promotion b ON b.order_id = o.order_id
        JOIN (SELECT order_id, COUNT(*) AS n FROM bridge_order_promotion GROUP BY order_id) n ON n.order_id = o.order_id
        JOIN dim_promotion p ON p.promo_id = b.promo_id
        WHERE o.status = 'COMPLETED' AND o.order_date >= ? AND o.order_date < ?
        GROUP BY p.promo_name ORDER BY p.promo_name
    """


def part_b():
    print("\nPart B: gross sales by promotion, first half of FY26-27")
    con = connect()
    total = con.execute("""SELECT SUM(gross_amount) FROM fct_orders WHERE status = 'COMPLETED' AND order_date >= ? AND order_date < ?
                           AND order_id IN (SELECT order_id FROM bridge_order_promotion)""", H1).fetchone()[0]
    rows = con.execute(double_counted_sql(), H1).fetchall()
    for name, orders, gross in rows:
        print(f"  {name:16} {orders:4} orders {gross:13,.2f}")
    print(f"  Sum of the three lines: {sum(r[2] for r in rows):,.2f}. Gross sales of orders that had a promotion: {total:,.2f}.")
    try:
        rows = con.execute(allocated_sql(), H1).fetchall()
    except NotImplementedError:
        print("  allocated_sql() is not written yet")
        return
    print("  With each order split between its promotions:")
    for name, orders, gross in rows:
        print(f"  {name:16} {orders:4} orders {gross:13,.2f}")
    allocated = sum(r[2] for r in rows)
    print(f"  Sum of the three lines: {allocated:,.2f}. " + ("It now equals the total." if abs(allocated - total) < 0.01 else "It should equal the total."))
    print("  An equal split is one allocation rule. The owner of the metric decides the rule; the semantic layer applies it.")
    con.close()


if __name__ == "__main__":
    part_a()
    part_b()
