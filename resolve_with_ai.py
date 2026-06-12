"""
resolve_with_ai.py — use Gemini (an LLM) to resolve supplier abbreviations that
string-matching couldn't: e.g. KBL = Kirloskar Brothers, L&T = Larsen & Toubro.
"""
import os, json
from collections import defaultdict
import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise SystemExit("No GEMINI_API_KEY found — check your .env file (step 4 should print True).")

client = genai.Client(api_key=api_key)
MODEL = "gemini-2.5-flash"   # current, stable free-tier model

df = pd.read_csv("procurement_classified.csv")
names = sorted(df["supplier_clean"].unique())

prompt = f"""These are supplier names from an Indian steel plant's procurement system.
Some are abbreviations or alternate forms of the SAME real company
(for example: "KBL" is Kirloskar Brothers, "L&T" is Larsen & Toubro).

Group the names that refer to the same real company, and return a JSON object that
maps each input name (exactly as given) to one canonical, full company name.
Use the most complete and correct official company name as the value.

Supplier names:
{json.dumps(names, indent=2)}

Return ONLY the JSON object, nothing else."""

print(f"Asking {MODEL} to resolve {len(names)} supplier names...")
try:
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json"),
    )
except Exception as e:
    raise SystemExit(f"Gemini call failed: {e}\n"
                     "If it mentions the model, change MODEL to 'gemini-3.5-flash'.\n"
                     "If it mentions the key, re-check your .env.")

mapping = json.loads(response.text)
df["supplier_final"] = df["supplier_clean"].map(lambda n: mapping.get(n, n))

print(f"\nSuppliers before AI : {df['supplier_clean'].nunique()}")
print(f"Suppliers after AI  : {df['supplier_final'].nunique()}")

groups = defaultdict(list)
for raw, canon in mapping.items():
    groups[canon].append(raw)
print("\nNames the AI folded together (the gaps string-matching missed):")
for canon, members in sorted(groups.items()):
    if len(members) > 1:
        print(f"   {canon}")
        print(f"      <- {', '.join(sorted(members))}")

check = df.groupby("supplier_final")["true_supplier"].nunique()
print(f"\nAccuracy check: {(check == 1).mean():.0%} of final groups map to exactly one real supplier.")

df.to_csv("procurement_final.csv", index=False)
print("Saved fully resolved data to procurement_final.csv")