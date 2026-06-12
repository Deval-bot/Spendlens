"""
normalize_suppliers.py — consolidate the many supplier names into single entities.
"""
import re
import pandas as pd
from rapidfuzz import fuzz

df = pd.read_csv("procurement_steel.csv")

NOISE = re.compile(
    r"\b(ltd|limited|pvt|private|llp|inc|corp|corporation|co|company|the|and|india|indian|asia|engineering|engg)\b",
    re.IGNORECASE)

def clean(name):
    s = name.lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = NOISE.sub(" ", s)
    tokens = [t for t in s.split() if len(t) > 1]   # NEW: ignore lone single letters like 'l', 't'
    return " ".join(tokens)

recorded = sorted(df["supplier_name_raw"].unique())
clusters = []
for i, name in enumerate(recorded):
    c = clean(name)
    if c == "":                                      # NEW: no usable signal -> stands alone, never force-matched
        clusters.append({"key": f"unmatched{i}", "members": [name]})
        continue
    placed = False
    for cl in clusters:
        if fuzz.token_set_ratio(c, cl["key"]) >= 85:
            cl["members"].append(name)
            placed = True
            break
    if not placed:
        clusters.append({"key": c, "members": [name]})

mapping = {}
for cl in clusters:
    official = max(cl["members"], key=len)
    for m in cl["members"]:
        mapping[m] = official

df["supplier_clean"] = df["supplier_name_raw"].map(mapping)

print(f"Recorded names : {df['supplier_name_raw'].nunique()}")
print(f"After cleaning : {df['supplier_clean'].nunique()} consolidated suppliers")
print()
print("Examples of names merged into one supplier:")
for cl in clusters:
    if len(cl["members"]) > 1:
        official = max(cl["members"], key=len)
        print(f"   {official}")
        print(f"      <- {', '.join(cl['members'])}")

check = df.groupby("supplier_clean")["true_supplier"].nunique()
pure = (check == 1).mean()
print(f"\nAccuracy check: {pure:.0%} of consolidated groups map to exactly one real supplier.")

df.to_csv("procurement_clean.csv", index=False)
print("Saved the cleaned data to procurement_clean.csv")