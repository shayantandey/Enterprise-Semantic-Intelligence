"""Exercise 1: reproduce a join that inflates net revenue, fix it, and add the tests that catch it.

Run:  python lab1_fanout.py
An order can have several returns. The first query joins orders straight to returns, so an order
with three returns is counted three times. You write the fixed query and one test.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # find semantic_layer.py in the lab folder
from semantic_layer import connect, query

QUARTER = ("2026-07-01", "2026-10-01")     # fiscal Q2 of FY26-27. The end date is exclusive.


def wrong_sql():
    """Net revenue as a report writer first wrote it: orders joined to returns, then summed."""
    return """
        SELECT COUNT(o.order_id)                                   AS order_rows,
               SUM(o.gross_amount)                                 AS gross_sales,
               SUM(COALESCE(r.refund_amount, 0))                   AS refunds,
               SUM(o.gross_amount) - SUM(COALESCE(r.refund_amount, 0)) AS net_revenue
        FROM fct_orders o
        LEFT JOIN fct_returns r ON r.order_id = o.order_id
        WHERE o.status = 'COMPLETED' AND o.order_date >= ? AND o.order_date < ?
    """


def fixed_sql():
    """The same definition with the join fixed: bring returns to one row per order before joining."""
    # Answer. Hint given: copy wrong_sql() and replace 'fct_returns r' with a subquery that has one row per order: (SELECT order_id, SUM(refund_amount) AS refund_amount FROM fct_returns GROUP BY order_id) r
    return """
        SELECT COUNT(o.order_id)                                   AS order_rows,
               SUM(o.gross_amount)                                 AS gross_sales,
               SUM(COALESCE(r.refund_amount, 0))                   AS refunds,
               SUM(o.gross_amount) - SUM(COALESCE(r.refund_amount, 0)) AS net_revenue
        FROM fct_orders o
        LEFT JOIN (SELECT order_id, SUM(refund_amount) AS refund_amount
                   FROM fct_returns GROUP BY order_id) r ON r.order_id = o.order_id
        WHERE o.status = 'COMPLETED' AND o.order_date >= ? AND o.order_date < ?
    """


def test_no_fanout(con, sql):
    """Return True when the query counts each completed order in the quarter exactly once.

    Compare order_rows from the query with a plain count of completed orders in fct_orders for the same dates.
    """
    # Answer. Hint given: run sql with QUARTER as parameters and read order_rows; run SELECT COUNT(*) FROM fct_orders WHERE status = 'COMPLETED' AND order_date >= ? AND order_date < ?; return whether the two numbers are equal
    order_rows = con.execute(sql, QUARTER).fetchone()[0]
    expected = con.execute("SELECT COUNT(*) FROM fct_orders WHERE status = 'COMPLETED' AND order_date >= ? AND order_date < ?",
                           QUARTER).fetchone()[0]
    return order_rows == expected


def source_tests(con):
    """Tests on the source data itself. These are written for you. Each returns the number of failing rows."""
    return {
        "return_id is unique in fct_returns":
            con.execute("SELECT COUNT(*) FROM (SELECT return_id FROM fct_returns GROUP BY return_id HAVING COUNT(*) > 1)").fetchone()[0],
        "every return points to an order that exists":
            con.execute("SELECT COUNT(*) FROM fct_returns r LEFT JOIN fct_orders o ON o.order_id = r.order_id WHERE o.order_id IS NULL").fetchone()[0],
        "refunds for an order do not exceed what the customer paid":
            con.execute("""SELECT COUNT(*) FROM (SELECT o.order_id FROM fct_orders o JOIN fct_returns r ON r.order_id = o.order_id
                           GROUP BY o.order_id, o.gross_amount, o.discount_amount
                           HAVING SUM(r.refund_amount) > o.gross_amount - o.discount_amount + 0.01)""").fetchone()[0],
    }


def line(label, row):
    print(f"{label:22} order rows {row[0]:5}   gross sales {row[1]:13,.2f}   refunds {row[2]:11,.2f}   net revenue {row[3]:13,.2f}")


def main():
    con = connect()
    wrong = con.execute(wrong_sql(), QUARTER).fetchone()
    line("Joined, then summed:", wrong)
    try:
        fixed = con.execute(fixed_sql(), QUARTER).fetchone()
        line("Fixed join:", fixed)
        print(f"The wrong join overstates gross sales by {wrong[1] - fixed[1]:,.2f} and net revenue by {wrong[3] - fixed[3]:,.2f}.")
    except NotImplementedError:
        print("Fixed join:            not written yet: fixed_sql()")
        fixed = None
    try:
        print(f"\ntest_no_fanout on the wrong query: {'pass' if test_no_fanout(con, wrong_sql()) else 'FAIL'}")
        if fixed:
            print(f"test_no_fanout on the fixed query: {'pass' if test_no_fanout(con, fixed_sql()) else 'FAIL'}")
    except NotImplementedError:
        print("\ntest_no_fanout: not written yet")
    print("\nSource tests on fct_returns:")
    for name, failures in source_tests(con).items():
        print(f"  {'pass' if failures == 0 else 'FAIL'}  {name}" + (f" ({failures} failing)" if failures else ""))
    layer = query(["refunds", "net_revenue"], start=QUARTER[0], end=QUARTER[1], definition=1)[0]
    clean = con.execute("""SELECT SUM(refund_amount) FROM (SELECT DISTINCT return_id, order_id, return_date, refund_amount FROM fct_returns)
                           WHERE return_date >= ? AND return_date < ?""", QUARTER).fetchone()[0]
    print(f"\nThe semantic layer reports refunds of {layer['refunds']:,.2f} for the quarter, dated by return date.")
    print(f"With each return counted once the figure is {clean:,.2f}. The layer computed its definition correctly on data that was loaded twice.")
    con.close()


if __name__ == "__main__":
    main()
