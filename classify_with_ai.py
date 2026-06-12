"""
classify_with_ai.py — a UNIVERSAL classifier: give it ANY procurement data and it
infers sensible spend categories with the LLM, using zero industry-specific rules.
"""
import os, json
import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
key = os.getenv("GEMINI_API_KEY")
if not key:
    raise SystemExit("No GEMINI_API_KEY found — check your .env file.")
client = genai.Client(api_key=key)
MODEL = "gemini-2.5-flash"

# This works on ANY procurement file. We use the steel data here only to prove
# it produces sensible categories with NONE of our steel-specific keywords.
df = pd.read_csv("procurement_classified.csv")
DESC_COL = "item_description"

descriptions = sorted(df[DESC_COL].dropna().unique())
print(f"Found {len(descriptions)} unique descriptions. Asking the AI to categorise them...")

prompt = f"""You are a procurement spend-analysis assistant.
Below are unique item/line descriptions from a company's purchasing records.
They may be cryptic shorthand from any industry.

Do two things:
1. Infer a concise set of sensible spend categories (about 6-15) that fit THIS data.
2. Assign each description to exactly one of those categories.

Return ONLY a JSON object mapping each description (exactly as given) to its category.

Descriptions:
{json.dumps(descriptions, indent=2)}
"""

resp = client.models.generate_content(
    model=MODEL, contents=prompt,
    config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json"),
)
mapping = json.loads(resp.text)
df["ai_category"] = df[DESC_COL].map(lambda d: mapping.get(d, "Uncategorized"))

cats = sorted(df["ai_category"].unique())
print(f"\nThe AI invented {len(cats)} categories — with no industry rules from us:")
for c in cats:
    print("   ", c)

print("\nSample classifications:")
for d in descriptions[:10]:
    print(f"   {d[:38]:38} ->  {mapping.get(d)}")

df.to_csv("procurement_ai_classified.csv", index=False)
print("\nSaved to procurement_ai_classified.csv")