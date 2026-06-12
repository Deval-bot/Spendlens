# SpendLens

**Turn messy procurement data into spend intelligence — for any industry.**

SpendLens takes a raw, messy procurement export — where the same supplier is
recorded under many names and items are typed as free-text shorthand — and
automatically consolidates suppliers, classifies spend into categories, and
surfaces where the negotiable savings sit. Upload a CSV, map three columns, and
get an interactive dashboard.

Inspired by Li, Culmone, De Reyck & Yoo (2025), *"Automating Procurement
Practices Using Artificial Intelligence,"* INFORMS Journal on Applied Analytics.

## What it does
- **Supplier consolidation** — fuzzy-matches duplicate supplier names
  ("SKF India Ltd", "SKF INDIA", "S.K.F." → one supplier).
- **AI classification** — uses Google Gemini to infer sensible spend categories
  for *your* data and sort every line into them — no industry rules required.
- **Kraljic leverage analysis** — maps each category by spend and supply risk to
  show where you have negotiating leverage.
- **Savings estimate & sourcing** — estimates savings in leverage categories and
  ranks suppliers per category for RFQs.

## How it works
1. Upload any procurement CSV (or try the built-in steel-plant sample).
2. Map your columns: supplier, item description, amount.
3. SpendLens consolidates suppliers (RapidFuzz), classifies spend (Gemini), and
   runs the analysis.
4. Explore the dashboard and download your cleaned, categorised data.

It is **bring-your-own-key**: each user supplies their own free Gemini API key,
so the app stores no secrets.

## Run it locally
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py

Get a free Gemini API key at https://aistudio.google.com/app/apikey and paste it
into the app sidebar.

## Tech stack
Python · Streamlit · pandas · Plotly · RapidFuzz · Google Gemini (google-genai)

## Live demo
*Coming soon — deployed on Streamlit Community Cloud.*

---
Built by [Your Name]. Sample data is synthetic and models real steel-plant procurement.