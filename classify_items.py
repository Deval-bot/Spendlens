"""
classify_items.py — sort each free-text item description into a spend category,
using simple, transparent keyword matching (whole words only).
"""
import re
import pandas as pd

df = pd.read_csv("procurement_clean.csv")

KEYWORDS = {
    "Hydraulics": ["hyd", "hydraulic", "proportional", "power pack", "hose"],
    "Pneumatics": ["pneu", "pneumatic", "solenoid", "frl", "air", "regulator"],
    "Gears & Drives": ["gearbox", "geared", "worm", "helical", "bevel", "coupling"],
    "Bearings & Spares": ["brg", "bearing", "ball", "taper", "plummer", "spherical"],
    "Conveyor & Handling": ["conveyor", "conv", "belt", "idler", "pulley", "fastener"],
    "Refractories": ["brick", "castable", "ladle", "tundish", "nozzle", "alumina", "mag carbon"],
    "Ferro Alloys": ["ferro", "silico", "manganese", "silicon", "chrome"],
    "Lubricants": ["grease", "oil", "ep2", "hlp", "turbine", "coolant"],
    "Electrical & Automation": ["motor", "vfd", "plc", "mccb", "contactor", "sensor", "transformer", "drive", "relay"],
    "Pumps & Compressors": ["pump", "centrifugal", "compressor", "submersible", "vacuum", "screw"],
    "Cutting Tools & Rolls": ["roll", "carbide", "insert", "grinding", "wheel", "slitter", "knife"],
}

def classify(description):
    text = description.lower()
    best_cat, best_score = "Uncategorized", 0
    for category, words in KEYWORDS.items():
        score = sum(1 for w in words if re.search(r"\b" + re.escape(w) + r"\b", text))
        if score > best_score:
            best_cat, best_score = category, score
    return best_cat

df["pred_category"] = df["item_description"].apply(classify)

accuracy = (df["pred_category"] == df["true_category"]).mean()
print(f"Classified {len(df)} purchase orders into categories.")
print(f"Classification accuracy vs the answer key: {accuracy:.1%}")
print()
print("A few examples:")
for _, row in df[["item_description", "pred_category", "true_category"]].head(10).iterrows():
    mark = "OK " if row["pred_category"] == row["true_category"] else "XX "
    print(f"   {mark} {row['item_description'][:34]:34}  ->  {row['pred_category']}")

df.to_csv("procurement_classified.csv", index=False)
print("\nSaved categorised data to procurement_classified.csv")