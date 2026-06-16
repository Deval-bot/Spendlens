"""
find_price_variance.py — find items bought at inconsistent unit prices.
Compare each purchase to a sensible BENCHMARK (the median price for that item),
not the rock-bottom price, and count only the premium paid above that benchmark.
"""
import pandas as pd

df = pd.read_csv("procurement_classified.csv")
df["unit_price"] = df["invoice_value"] / df["order_qty"]   # price per single unit

rows = []
for item, g in df.groupby("item_description"):
    if len(g) < 2:
        continue                                   # need 2+ orders to compare
    benchmark = g["unit_price"].median()           # the "fair" going rate
    over = g[g["unit_price"] > benchmark]          # only the overpriced buys
    savings = ((over["unit_price"] - benchmark) * over["order_qty"]).sum()
    rows.append({
        "item": item,
        "orders": len(g),
        "suppliers": g["supplier_clean"].nunique(),
        "median_price": benchmark,
        "max_price": g["unit_price"].max(),
        "spread_x": g["unit_price"].max() / g["unit_price"].min(),
        "savings_vs_median": savings,
    })

opp = pd.DataFrame(rows).sort_values("savings_vs_median", ascending=False)
total_savings = opp["savings_vs_median"].sum()
total_spend = df["invoice_value"].sum()

print(f"Items analysed : {len(opp)}")
print(f"Total spend    : Rs {total_spend/1e7:,.0f} Cr")
print(f"Recoverable if over-median buys came down to median : "
      f"Rs {total_savings/1e7:,.0f} Cr  ({total_savings/total_spend:.1%})")
print()
print(f"{'Item':<32}{'Ord':>4}{'Median':>11}{'Max':>11}{'Spread':>8}{'Savings(Cr)':>13}")
print("-" * 79)
for _, r in opp.head(8).iterrows():
    print(f"{r['item'][:31]:<32}{r['orders']:>4}{r['median_price']:>11,.0f}"
          f"{r['max_price']:>11,.0f}{r['spread_x']:>7.1f}x{r['savings_vs_median']/1e7:>12,.0f}")