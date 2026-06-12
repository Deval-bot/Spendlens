"""
analyze_kraljic.py — turn the clean, categorised data into a Kraljic leverage
map and a savings estimate. This is where the data becomes a decision.
"""
import pandas as pd

df = pd.read_csv("procurement_classified.csv")

summary = df.groupby("pred_category").agg(
    total_spend=("invoice_value", "sum"),
    n_suppliers=("supplier_clean", "nunique"),
    n_orders=("po_id", "count"),
).reset_index()

# Kraljic axes (median split): profit impact = spend ; supply risk = how FEW suppliers
spend_mid = summary["total_spend"].median()
sup_mid = summary["n_suppliers"].median()

def quadrant(row):
    high_spend = row["total_spend"] >= spend_mid
    few_suppliers = row["n_suppliers"] <= sup_mid
    if high_spend and few_suppliers:     return "Strategic"
    if high_spend and not few_suppliers: return "Leverage"
    if not high_spend and few_suppliers: return "Bottleneck"
    return "Routine"

summary["quadrant"] = summary.apply(quadrant, axis=1)
summary = summary.sort_values("total_spend", ascending=False)

print(f"{'Category':<26}{'Spend (Cr)':>11}{'Suppliers':>11}   Quadrant")
print("-" * 62)
for _, r in summary.iterrows():
    print(f"{r['pred_category']:<26}{r['total_spend']/1e7:>11,.0f}{r['n_suppliers']:>11}   {r['quadrant']}")

leverage = summary[summary["quadrant"] == "Leverage"]
lev_spend = leverage["total_spend"].sum()
total = summary["total_spend"].sum()
low, high = lev_spend * 0.05, lev_spend * 0.10

print()
print(f"Total spend analysed : Rs {total/1e7:,.0f} Cr")
print(f"Leverage categories  : {', '.join(leverage['pred_category'])}")
print(f"Estimated savings    : Rs {low/1e7:,.0f}-{high/1e7:,.0f} Cr  ({low/total:.1%}-{high/total:.1%} of total spend)")

summary.to_csv("category_analysis.csv", index=False)
print("\nSaved the category analysis to category_analysis.csv")