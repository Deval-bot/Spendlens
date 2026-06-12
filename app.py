"""
app.py — SpendLens: turn ANY messy procurement CSV into spend intelligence.
Run with:  python -m streamlit run app.py
"""
import os, json, re
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from rapidfuzz import fuzz

load_dotenv()
st.set_page_config(page_title="SpendLens", page_icon="🔎", layout="wide")
COLORS = {"Leverage": "#2e9e6f", "Strategic": "#e0922f", "Bottleneck": "#d9534f", "Routine": "#7a838f"}

# ============================ ENGINE (industry-agnostic) ============================
NOISE = re.compile(r"\b(ltd|limited|pvt|private|llp|inc|incorporated|corp|corporation|co|company|"
                   r"gmbh|plc|sa|bv|group|holdings|technologies|tech|the|and|india|indian)\b", re.I)

def _clean(name):
    s = re.sub(r"[^a-z0-9 ]", " ", str(name).lower())
    s = NOISE.sub(" ", s)
    return " ".join(t for t in s.split() if len(t) > 1)

def consolidate_suppliers(names):
    """Fuzzy-cluster messy supplier names into one canonical name each."""
    clusters = []
    for i, name in enumerate(sorted(names)):
        c = _clean(name)
        if c == "":
            clusters.append({"key": f"unmatched{i}", "members": [name]}); continue
        placed = False
        for cl in clusters:
            if fuzz.token_set_ratio(c, cl["key"]) >= 85:
                cl["members"].append(name); placed = True; break
        if not placed:
            clusters.append({"key": c, "members": [name]})
    return {m: max(cl["members"], key=len) for cl in clusters for m in cl["members"]}

def classify_with_llm(descriptions, api_key, model="gemini-2.5-flash"):
    """Ask Gemini to infer categories for THIS data and assign each description."""
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=api_key)
    prompt = ("You are a procurement spend-analysis assistant. Below are unique item/line "
              "descriptions from a company's purchasing records, possibly cryptic shorthand from any industry.\n"
              "1. Infer a concise set of sensible spend categories (about 6-15) that fit THIS data.\n"
              "2. Assign each description to exactly one of those categories.\n"
              "Return ONLY a JSON object mapping each description (exactly as given) to its category.\n\n"
              "Descriptions:\n" + json.dumps(descriptions, indent=2))
    resp = client.models.generate_content(
        model=model, contents=prompt,
        config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json"))
    return json.loads(resp.text)

def analyze(work):
    s = work.groupby("category").agg(
        total_spend=("amount", "sum"), n_suppliers=("supplier", "nunique"),
        n_orders=("item_desc", "count")).reset_index()
    sm, um = s.total_spend.median(), s.n_suppliers.median()
    def quad(r):
        hs, fs = r.total_spend >= sm, r.n_suppliers <= um
        return "Strategic" if hs and fs else "Leverage" if hs and not fs else \
               "Bottleneck" if not hs and fs else "Routine"
    s["quadrant"] = s.apply(quad, axis=1)
    return s.sort_values("total_spend", ascending=False)

def fmt(v, sym=""):
    a = abs(v)
    if a >= 1e9: return f"{sym}{v/1e9:.2f}B"
    if a >= 1e6: return f"{sym}{v/1e6:.2f}M"
    if a >= 1e3: return f"{sym}{v/1e3:.1f}K"
    return f"{sym}{v:.0f}"

# ================================ SIDEBAR ================================
st.sidebar.title("SpendLens")
api_key = st.sidebar.text_input("Gemini API key", value=os.getenv("GEMINI_API_KEY") or "",
                                type="password", help="Free key: aistudio.google.com/app/apikey")
currency = st.sidebar.text_input("Currency symbol (optional)", value="")
source = st.sidebar.radio("Data source", ["Use sample (steel plant)", "Upload my CSV"])

def load_csv(f):
    try:
        return pd.read_csv(f)
    except UnicodeDecodeError:
        if hasattr(f, "seek"):
            f.seek(0)
        return pd.read_csv(f, encoding="latin-1")

if source == "Upload my CSV":
    up = st.sidebar.file_uploader("Upload procurement CSV", type=["csv"])
    raw = load_csv(up) if up is not None else None
else:
    raw = load_csv("procurement_steel.csv")

# ================================ HEADER ================================
st.title("SpendLens")
st.caption("Turn messy procurement data into spend intelligence — any industry. After Li et al. (2025), INFORMS.")

if raw is None:
    st.info("⬅ Upload a CSV in the sidebar, or switch to the sample, to begin.")
    st.stop()

# column mapping
cols = list(raw.columns)
def guess(keys):
    for i, c in enumerate(cols):
        if any(k in c.lower() for k in keys): return i
    return 0
st.sidebar.markdown("**Map your columns**")
sup_col  = st.sidebar.selectbox("Supplier name", cols, index=guess(["supplier", "vendor"]))
desc_col = st.sidebar.selectbox("Item description", cols, index=guess(["item", "desc", "product", "material"]))
amt_col  = st.sidebar.selectbox("Amount / spend", cols, index=guess(["invoice", "amount", "value", "spend", "price", "cost"]))
run = st.sidebar.button("Run analysis", type="primary")

# ================================ RUN PIPELINE ================================
if run:
    if not api_key:
        st.error("Please paste your free Gemini API key in the sidebar first.")
        st.stop()
    work = raw[[sup_col, desc_col, amt_col]].copy()
    work.columns = ["supplier_raw", "item_desc", "amount"]
    work["amount"] = pd.to_numeric(
        work["amount"].astype(str).str.replace(r"[^0-9.\-]", "", regex=True),
        errors="coerce")
    work = work.dropna(subset=["amount", "supplier_raw", "item_desc"])
    work["supplier_raw"] = work["supplier_raw"].astype(str)
    work["item_desc"] = work["item_desc"].astype(str)

    with st.spinner("Consolidating suppliers..."):
        work["supplier"] = work["supplier_raw"].map(consolidate_suppliers(work["supplier_raw"].unique()))
    with st.spinner("Classifying spend with AI (this is the slow bit)..."):
        try:
            catmap = classify_with_llm(sorted(work["item_desc"].unique()), api_key)
        except Exception as e:
            st.error(f"AI classification failed: {e}\nCheck your key, or try model 'gemini-3.5-flash'.")
            st.stop()
        work["category"] = work["item_desc"].map(lambda d: catmap.get(d, "Uncategorized"))
    st.session_state["work"] = work
    st.session_state["summary"] = analyze(work)

# ================================ DASHBOARD ================================
if "work" in st.session_state:
    work, summary = st.session_state["work"], st.session_state["summary"]
    total = summary.total_spend.sum()
    lev = summary[summary.quadrant == "Leverage"]
    low, high = lev.total_spend.sum() * 0.05, lev.total_spend.sum() * 0.10

    a, b, c, d = st.columns(4)
    a.metric("Total spend", fmt(total, currency))
    b.metric("Suppliers consolidated", f"{work.supplier_raw.nunique()} → {work.supplier.nunique()}")
    c.metric("Categories found", f"{summary.shape[0]}")
    d.metric("Est. savings", f"{fmt(low, currency)}–{fmt(high, currency)}")
    st.divider()

    st.subheader("Kraljic leverage map")
    st.caption("Each bubble is a category. Top-right (high spend, many suppliers) = leverage = safe to renegotiate.")
    fig = px.scatter(summary, x="n_suppliers", y="total_spend", size="n_orders", color="quadrant",
                     text="category", color_discrete_map=COLORS, size_max=55,
                     labels={"n_suppliers": "Number of suppliers (more → lower risk)", "total_spend": "Total spend"})
    fig.update_traces(textposition="top center"); fig.update_layout(height=480)
    st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns(2)
    with left:
        st.subheader("Spend by category")
        bar = px.bar(summary.sort_values("total_spend"), x="total_spend", y="category", orientation="h",
                     color="quadrant", color_discrete_map=COLORS, labels={"total_spend": "Spend", "category": ""})
        bar.update_layout(height=420, showlegend=False)
        st.plotly_chart(bar, use_container_width=True)
    with right:
        st.subheader("Who can supply a category?")
        st.caption("Pick a category to see its suppliers ranked by spend — your RFQ shortlist.")
        pick = st.selectbox("Category", summary.category)
        alt = (work[work.category == pick].groupby("supplier")["amount"].sum()
               .sort_values(ascending=False)).rename("Spend").to_frame()
        alt["Spend"] = alt["Spend"].map(lambda v: fmt(v, currency))
        st.dataframe(alt, use_container_width=True)

    st.divider()
    st.download_button("⬇ Download cleaned + classified data (CSV)",
                       work.to_csv(index=False).encode("utf-8"), "spendlens_output.csv", "text/csv")
else:
    st.info("Set your key, map your columns, and press **Run analysis** in the sidebar.")