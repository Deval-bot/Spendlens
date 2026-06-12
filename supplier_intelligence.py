"""
supplier_intelligence.py — build each supplier's 'DNA' (categories it supplies),
then answer: who competes with a supplier, and who can supply a category.
"""
import pandas as pd

df = pd.read_csv("procurement_classified.csv")

profile = df.groupby("supplier_clean").agg(
    total_spend=("invoice_value", "sum"),
    categories=("pred_category", lambda s: set(s)),
).reset_index()

def find_competitors(supplier, top_n=5):
    target = profile.loc[profile["supplier_clean"] == supplier, "categories"].iloc[0]
    results = []
    for _, other in profile.iterrows():
        if other["supplier_clean"] == supplier:
            continue
        union = target | other["categories"]
        score = len(target & other["categories"]) / len(union) if union else 0
        if score > 0:
            results.append((other["supplier_clean"], score, other["total_spend"]))
    results.sort(key=lambda x: (x[1], x[2]), reverse=True)
    return results[:top_n]

def alternate_suppliers(category):
    sub = df[df["pred_category"] == category]
    return sub.groupby("supplier_clean")["invoice_value"].sum().sort_values(ascending=False)

top_supplier = profile.sort_values("total_spend", ascending=False).iloc[0]["supplier_clean"]
print(f"Biggest supplier by spend: {top_supplier}")
print("Closest competitors (most similar category footprint):")
for name, score, spend in find_competitors(top_supplier):
    print(f"   {name:<34} {score:.0%} match   Rs {spend/1e7:,.0f} Cr")

print("\nWho can supply 'Pumps & Compressors' (a leverage category), ranked by spend:")
for name, spend in alternate_suppliers("Pumps & Compressors").items():
    print(f"   {name:<34} Rs {spend/1e7:,.0f} Cr")

out = profile.copy()
out["categories"] = out["categories"].apply(lambda s: "; ".join(sorted(s)))
out.to_csv("supplier_profiles.csv", index=False)
print("\nSaved supplier profiles to supplier_profiles.csv")