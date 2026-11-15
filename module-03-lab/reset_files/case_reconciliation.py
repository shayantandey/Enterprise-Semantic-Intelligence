"""Case study for section 3.8: three reports give three figures for net revenue in FY26-27 Q2.

Run:  python case_reconciliation.py
Nothing to write here. The script rebuilds each report's figure from the lab warehouse and then walks
from each report to the governed figure one difference at a time. The company and its data are fictional.
The governed definition used here is version 2: gross sales less discounts less refunds, refunds dated by return date.
"""
from semantic_layer import connect

Q = ("2026-07-01", "2026-10-01")


def one(con, sql, params=Q):
    return con.execute(sql, params).fetchone()[0] or 0.0


def main():
    con = connect()
    gross = one(con, "SELECT SUM(gross_amount) FROM sem_orders WHERE date_day >= ? AND date_day < ?")
    discounts = one(con, "SELECT SUM(discount_amount) FROM sem_orders WHERE date_day >= ? AND date_day < ?")
    tax = one(con, "SELECT SUM(tax_amount) FROM sem_orders WHERE date_day >= ? AND date_day < ?")
    refunds_by_return = one(con, "SELECT SUM(refund_amount) FROM sem_returns WHERE date_day >= ? AND date_day < ?")
    refunds_by_order = one(con, """SELECT SUM(r.refund_amount) FROM fct_returns r JOIN fct_orders o ON o.order_id = r.order_id
                                   WHERE o.status = 'COMPLETED' AND o.order_date >= ? AND o.order_date < ?""")
    fanned_gross = one(con, """SELECT SUM(o.gross_amount) FROM fct_orders o LEFT JOIN fct_returns r ON r.order_id = o.order_id
                               WHERE o.status = 'COMPLETED' AND o.order_date >= ? AND o.order_date < ?""")
    last_day = one(con, """SELECT SUM(gross_amount - discount_amount + tax_amount) FROM fct_orders
                           WHERE status = 'COMPLETED' AND order_date = '2026-09-30'""", ())
    clean_refunds = one(con, """SELECT SUM(refund_amount) FROM (SELECT DISTINCT return_id, order_id, return_date, refund_amount FROM fct_returns)
                                WHERE return_date >= ? AND return_date < ?""")
    governed = gross - discounts - refunds_by_return

    finance = governed
    sales = fanned_gross - refunds_by_order
    ecommerce = (gross - discounts + tax - last_day) - refunds_by_return

    print("Net revenue, FY26-27 Q2, as each report shows it")
    print(f"  Finance month-end pack      {finance:13,.2f}")
    print(f"  Sales dashboard             {sales:13,.2f}")
    print(f"  E-commerce weekly export    {ecommerce:13,.2f}")

    print("\nFrom the sales dashboard to the governed figure")
    steps = [("Sales dashboard", sales),
             ("remove order rows repeated by the join to returns", -(fanned_gross - gross)),
             ("move refunds to the quarter of the return", -(refunds_by_return - refunds_by_order)),
             ("deduct discounts", -discounts)]
    walk(steps, governed)

    print("\nFrom the e-commerce export to the governed figure")
    steps = [("E-commerce weekly export", ecommerce),
             ("add back 30 September, dropped by the date filter", last_day),
             ("remove tax", -tax)]
    walk(steps, governed)

    print("\nAfter the three reports agree")
    print(f"  Governed figure on the data as loaded          {governed:13,.2f}")
    print(f"  Return rows loaded twice (17 to 21 August)     {refunds_by_return - clean_refunds:13,.2f}")
    print(f"  Governed figure once each return counts once   {governed + refunds_by_return - clean_refunds:13,.2f}")
    con.close()


def walk(steps, target):
    total = 0.0
    for i, (label, amount) in enumerate(steps):
        total += amount
        print(f"  {label:52} {amount:+14,.2f}" if i else f"  {label:52} {amount:14,.2f}")
    print(f"  {'= governed figure':52} {total:14,.2f}" + ("" if abs(total - target) < 0.01 else f"   (expected {target:,.2f})"))


if __name__ == "__main__":
    main()
