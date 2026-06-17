"""
app.py — SpendLens: turn ANY messy procurement file into spend intelligence.
Run with:  python -m streamlit run app.py
"""
import os, json, re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from rapidfuzz import fuzz

load_dotenv()
st.set_page_config(page_title="SpendLens", page_icon="🔎", layout="wide")
COLORS = {"Leverage": "#2e9e6f", "Strategic": "#e0922f", "Bottleneck": "#d9534f", "Routine": "#7a838f"}

# ============================ FILE LOADING ============================
def load_file(f):
    """Read a user file as CSV (utf-8, then latin-1) or Excel."""
    name = (f.name if hasattr(f, "name") else str(f)).lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(f)
    try:
        return pd.read_csv(f)
    except UnicodeDecodeError:
        if hasattr(f, "seek"):
            f.seek(0)
        return pd.read_csv(f, encoding="latin-1")

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
def resolve_suppliers_llm(names, api_key, model="gemini-2.5-flash"):
    """Merge names that are the SAME real-world company using the LLM's world
    knowledge (e.g. 'KBL' = 'Kirloskar Brothers Limited'). In-context clustering,
    after Fu et al. (2025) and Peeters et al. (2025) — catches aliases fuzzy can't."""
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=api_key)
    prompt = ("Below are supplier/company names from purchasing records, already partly "
              "de-duplicated. Some still refer to the SAME real-world company via abbreviations "
              "or aliases (e.g. 'KBL' = 'Kirloskar Brothers Limited', 'L&T' = 'Larsen & Toubro'). "
              "Using your world knowledge, cluster names that are the same company.\n"
              "Return ONLY a JSON object mapping EACH input name to one canonical company name "
              "(use the most complete, formal name as canonical).\n\nNames:\n"
              + json.dumps(sorted(names), indent=2))
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

def price_variance(work):
    """Items bought above their median unit price = recoverable premium (needs qty)."""
    if "qty" not in work.columns:
        return None
    w = work.dropna(subset=["qty"]).copy()
    w = w[w["qty"] > 0]
    if w.empty:
        return None
    w["unit_price"] = w["amount"] / w["qty"]
    rows = []
    for item, g in w.groupby("item_desc"):
        if len(g) < 2:
            continue
        bench = g["unit_price"].median()
        over = g[g["unit_price"] > bench]
        savings = ((over["unit_price"] - bench) * over["qty"]).sum()
        if savings <= 0:
            continue
        rows.append({"Item": item, "Orders": len(g), "Suppliers": g["supplier"].nunique(),
                     "Median unit price": bench, "Max unit price": g["unit_price"].max(),
                     "Spread": g["unit_price"].max() / g["unit_price"].min(),
                     "Recoverable": savings})
    if not rows:
        return None
    return pd.DataFrame(rows).sort_values("Recoverable", ascending=False)
def tail_spend(work, head_share=0.80):
    """Pareto: a few 'head' suppliers carry ~80% of spend; the rest are the long tail."""
    spend = work.groupby("supplier")["amount"].sum().sort_values(ascending=False)
    total = spend.sum()
    prof = spend.reset_index()
    prof.columns = ["supplier", "spend"]
    prof["rank"] = range(1, len(prof) + 1)
    prof["cum_pct"] = prof["spend"].cumsum() / total
    crossed = prof["cum_pct"] >= head_share
    boundary = crossed.idxmax() if crossed.any() else len(prof) - 1
    prof["segment"] = ["Head" if i <= boundary else "Tail" for i in range(len(prof))]
    n_head = int((prof["segment"] == "Head").sum())
    tail_amt = prof.loc[prof["segment"] == "Tail", "spend"].sum()
    return {"profile": prof, "n_total": len(prof), "n_head": n_head,
            "n_tail": len(prof) - n_head,
            "tail_pct_suppliers": (len(prof) - n_head) / len(prof) if len(prof) else 0,
            "tail_spend": tail_amt, "tail_spend_pct": tail_amt / total if total else 0}
def fmt(v, sym=""):
    a = abs(v)
    if a >= 1e9: return f"{sym}{v/1e9:.2f}B"
    if a >= 1e6: return f"{sym}{v/1e6:.2f}M"
    if a >= 1e3: return f"{sym}{v/1e3:.1f}K"
    return f"{sym}{v:.0f}"
def sourcing_strategist(summary, work, api_key, currency="", risk_brief="", model="gemini-2.5-flash"):
    """A Sourcing Strategist 'agent': reads the spend analysis and drafts a
    decision-ready sourcing brief. The first agent of a multi-agent design
    (after Jannelli & Brintrup, 2025) — the pipeline above is the Spend Analyst."""
    from google import genai
    from google.genai import types
    cat_lines = [f"- {r['category']}: spend {fmt(r['total_spend'], currency)}, "
                 f"{int(r['n_suppliers'])} suppliers, quadrant {r['quadrant']}"
                 for _, r in summary.iterrows()]
    lev_cats = list(summary[summary["quadrant"] == "Leverage"]["category"])
    sup_lines = []
    for c in lev_cats:
        s = (work[work["category"] == c].groupby("supplier")["amount"].sum()
             .sort_values(ascending=False).head(5))
        sup_lines.append(f"{c}: " + ", ".join(f"{n} ({fmt(v, currency)})" for n, v in s.items()))
    digest = ("Spend by category:\n" + "\n".join(cat_lines) +
              "\n\nLeverage categories (best renegotiation targets) and their suppliers:\n" +
              ("\n".join(sup_lines) if sup_lines else "none"))
    prompt = ("You are a procurement Sourcing Strategist. Based ONLY on the spend analysis below, "
              "write a concise, decision-ready sourcing brief for a category manager, in markdown, "
              "with these sections:\n"
              "1. Top 3 opportunities (which categories/suppliers, and why).\n"
              "2. Recommended action for each (e.g. run a competitive RFQ, consolidate suppliers, renegotiate).\n"
              "3. A suggested RFQ shortlist where relevant.\n"
              "4. One negotiation angle per opportunity.\n"
              "Be specific and practical. Do NOT invent data that is not in the analysis.\n\n"
              "ANALYSIS:\n" + digest)
    if risk_brief:
        prompt += ("\n\nSUPPLIER RISK ASSESSMENT (factor this in; do NOT recommend aggressive "
                   "renegotiation or sole-source consolidation where risk is high):\n" + risk_brief)
    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(
        model=model, contents=prompt,
        config=types.GenerateContentConfig(temperature=0.3))
    return resp.text


def _risk_metrics(summary, work, currency=""):
    lines, single = [], 0
    for _, r in summary.sort_values("total_spend", ascending=False).iterrows():
        cat = r["category"]
        g = work[work["category"] == cat].groupby("supplier")["amount"].sum().sort_values(ascending=False)
        top_share = (g.iloc[0] / g.sum()) if len(g) else 0
        top_name = g.index[0] if len(g) else "n/a"
        flag = "SINGLE-SOURCE" if r["n_suppliers"] == 1 else ("CONCENTRATED" if top_share >= 0.7 else "")
        if r["n_suppliers"] == 1:
            single += 1
        lines.append(f"- {cat}: spend {fmt(r['total_spend'], currency)}, {int(r['n_suppliers'])} suppliers, "
                     f"top supplier {top_name} {top_share:.0%} {flag}".rstrip())
    total = work["amount"].sum()
    dep = (work.groupby("supplier")["amount"].sum().sort_values(ascending=False).head(5) / total)
    dep_lines = [f"- {n}: {v:.0%} of total spend" for n, v in dep.items()]
    return (f"Categories: {len(summary)}; single-source categories: {single}\n\n"
            "Per-category supply risk:\n" + "\n".join(lines) +
            "\n\nMost depended-on suppliers:\n" + "\n".join(dep_lines))


def supplier_risk_agent(summary, work, api_key, currency="", model="gemini-2.5-flash"):
    """A Supplier Risk agent: flags single-source / concentrated categories and
    over-dependence on individual suppliers (after Jannelli & Brintrup, 2025)."""
    from google import genai
    from google.genai import types
    digest = _risk_metrics(summary, work, currency)
    prompt = ("You are a procurement Supplier Risk analyst. Based ONLY on the supply-risk signals below, "
              "identify the top supply risks: single-source or highly concentrated categories, and "
              "over-dependence on individual suppliers. For each, name the category/supplier, why it is "
              "risky, and the potential business impact. Be concise, in markdown. Do NOT invent data.\n\n"
              "SUPPLY-RISK SIGNALS:\n" + digest)
    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(
        model=model, contents=prompt,
        config=types.GenerateContentConfig(temperature=0.3))
    return resp.text

# ================================ SIDEBAR ================================
st.sidebar.title("SpendLens")
api_key = st.sidebar.text_input("Gemini API key", value=os.getenv("GEMINI_API_KEY") or "",
                                type="password", help="Free key: aistudio.google.com/app/apikey")
currency = st.sidebar.text_input("Currency symbol (optional)", value="")
ai_resolve = st.sidebar.checkbox("AI supplier resolution (merge abbreviations)", value=True)
source = st.sidebar.radio("Data source", ["Use sample (steel plant)", "Upload my file"])

if source == "Upload my file":
    up = st.sidebar.file_uploader("Upload procurement data", type=["csv", "xlsx", "xls"])
    raw = load_file(up) if up is not None else None
else:
    raw = load_file("procurement_steel.csv")

# ================================ HEADER ================================
st.title("SpendLens")
st.caption("Turn messy procurement data into spend intelligence — any industry. After Li et al. (2025), INFORMS.")

if raw is None:
    st.info("⬅ Upload a file in the sidebar, or switch to the sample, to begin.")
    st.stop()

# column mapping
cols = list(raw.columns)
def guess(keys):
    for i, c in enumerate(cols):
        if any(k in c.lower() for k in keys): return i
    return 0
qty_options = ["— none —"] + cols
def guess_qty():
    for c in cols:
        if any(k in c.lower() for k in ["qty", "quantity", "units", "order_qty"]):
            return qty_options.index(c)
    return 0

st.sidebar.markdown("**Map your columns**")
sup_col  = st.sidebar.selectbox("Supplier name", cols, index=guess(["supplier", "vendor"]))
desc_col = st.sidebar.selectbox("Item description", cols, index=guess(["item", "desc", "product", "material"]))
amt_col  = st.sidebar.selectbox("Amount / spend", cols, index=guess(["invoice", "amount", "value", "spend", "price", "cost"]))
qty_col  = st.sidebar.selectbox("Quantity (optional — unlocks price analysis)", qty_options, index=guess_qty())
run = st.sidebar.button("Run analysis", type="primary")

# ================================ RUN PIPELINE ================================
if run:
    if not api_key:
        st.error("Please paste your free Gemini API key in the sidebar first.")
        st.stop()
    work = raw[[sup_col, desc_col, amt_col]].copy()
    work.columns = ["supplier_raw", "item_desc", "amount"]
    work["amount"] = pd.to_numeric(
        work["amount"].astype(str).str.replace(r"[^0-9.\-]", "", regex=True), errors="coerce")
    if qty_col != "— none —":
        work["qty"] = pd.to_numeric(
            raw[qty_col].astype(str).str.replace(r"[^0-9.\-]", "", regex=True), errors="coerce")
    work = work.dropna(subset=["amount", "supplier_raw", "item_desc"])
    work["supplier_raw"] = work["supplier_raw"].astype(str)
    work["item_desc"] = work["item_desc"].astype(str)

    with st.spinner("Consolidating suppliers..."):
        work["supplier"] = work["supplier_raw"].map(consolidate_suppliers(work["supplier_raw"].unique()))
    if ai_resolve:
        with st.spinner("Resolving abbreviations & aliases with AI..."):
            try:
                fmap = resolve_suppliers_llm(work["supplier"].unique(), api_key)
                work["supplier"] = work["supplier"].map(lambda s: fmap.get(s, s))
            except Exception as e:
                st.warning(f"AI supplier resolution skipped ({e}). Using fuzzy matching only.")
    with st.spinner("Classifying spend with AI (this is the slow bit)..."):
        try:
            catmap = classify_with_llm(sorted(work["item_desc"].unique()), api_key)
        except Exception as e:
            st.error(f"AI classification failed: {e}\n\n"
                     "If this is a quota/limit error, wait a few minutes and click Run once more "
                     "(each click uses some of the free-tier allowance).")
            st.stop()
        st.session_state["work_base"] = work
    uniq = sorted(work["item_desc"].unique())
    st.session_state["cat_df"] = pd.DataFrame(
        {"item_desc": uniq, "category": [catmap.get(d, "Uncategorized") for d in uniq]})
    st.session_state.pop("work", None)
    st.session_state.pop("summary", None)

# ======================= REVIEW & CORRECT CATEGORIES (human in the loop) =======================
if "work_base" in st.session_state and "cat_df" in st.session_state:
    st.subheader("Review & correct the AI's categories")
    st.caption("The AI assigned each unique item to a category. Fix any it got wrong, then analyse — "
               "you stay in control of the classification (after Spina et al., 2025).")
    cats = sorted(st.session_state["cat_df"]["category"].unique())
    edited = st.data_editor(
        st.session_state["cat_df"], key="cat_editor", use_container_width=True, hide_index=True,
        column_config={
            "item_desc": st.column_config.TextColumn("Item description", disabled=True),
            "category": st.column_config.SelectboxColumn("Category", options=cats, required=True),
        })
    if st.button("Apply corrections & analyze", type="primary"):
        mapping = dict(zip(edited["item_desc"], edited["category"]))
        wb = st.session_state["work_base"].copy()
        wb["category"] = wb["item_desc"].map(lambda d: mapping.get(d, "Uncategorized"))
        st.session_state["work"] = wb
        st.session_state["summary"] = analyze(wb)
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
    d.metric("Est. leverage savings", f"{fmt(low, currency)}–{fmt(high, currency)}")
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

    # ---- Savings opportunity: price consistency ----
    st.divider()
    st.subheader("💸 Savings opportunity — price consistency")
    pv = price_variance(work)
    if pv is None:
        st.info("Map a **Quantity** column in the sidebar (then press Run again) to unlock this — "
                "it needs unit price = amount ÷ quantity.")
    else:
        recoverable = pv["Recoverable"].sum()
        st.caption("Items bought above their normal (median) unit price. 'Recoverable' = the premium paid "
                   "above the median on the overpriced orders — a conservative, defensible target, not a "
                   "fantasy best-price figure.")
        st.metric("Recoverable from price consistency", fmt(recoverable, currency))
        show = pv.head(15).copy()
        show["Median unit price"] = show["Median unit price"].map(lambda v: fmt(v, currency))
        show["Max unit price"] = show["Max unit price"].map(lambda v: fmt(v, currency))
        show["Spread"] = show["Spread"].map(lambda v: f"{v:.1f}×")
        show["Recoverable"] = show["Recoverable"].map(lambda v: fmt(v, currency))
        st.dataframe(show, use_container_width=True, hide_index=True)

    # ---- Savings opportunity: tail-spend consolidation ----
    st.divider()
    st.subheader("📦 Savings opportunity — tail-spend consolidation")
    ts = tail_spend(work)
    st.caption("A few suppliers carry most of your spend; a long tail of small suppliers adds admin cost, "
               "weak leverage, and maverick-spend risk. Consolidating the tail is a classic quick win.")
    n_tail = ts["n_tail"]
    tail_pct = ts["tail_pct_suppliers"]
    tail_spend_pct = ts["tail_spend_pct"]
    tail_spend_val = fmt(ts["tail_spend"], currency)
    m1, m2, m3 = st.columns(3)
    m1.metric("Total suppliers", ts["n_total"])
    m2.metric("Carry ~80% of spend", ts["n_head"])
    m3.metric("Tail suppliers", f"{n_tail} ({tail_pct:.0%})",
              help=f"The tail is only {tail_spend_pct:.0%} of spend = {tail_spend_val}")
    prof = ts["profile"]
    seg_colors = ["#2e9e6f" if s == "Head" else "#7a838f" for s in prof["segment"]]
    pareto = go.Figure()
    pareto.add_bar(x=prof["rank"], y=prof["spend"], marker_color=seg_colors, name="Supplier spend",
                   customdata=prof["supplier"], hovertemplate="%{customdata}<br>%{y:,.0f}<extra></extra>")
    pareto.add_scatter(x=prof["rank"], y=prof["cum_pct"] * 100, yaxis="y2", mode="lines+markers",
                       line=dict(color="#e0922f"), name="Cumulative %")
    pareto.add_scatter(x=[1, ts["n_total"]], y=[80, 80], yaxis="y2", mode="lines",
                       line=dict(dash="dash", color="#d9534f"), name="80% line")
    pareto.update_layout(height=420,
                         xaxis=dict(title="Suppliers ranked by spend (1 = biggest)"),
                         yaxis=dict(title="Spend"),
                         yaxis2=dict(title="Cumulative %", overlaying="y", side="right", range=[0, 105]),
                         legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(pareto, use_container_width=True)

    st.divider()
    st.download_button("⬇ Download cleaned + classified data (CSV)",
                       work.to_csv(index=False).encode("utf-8"), "spendlens_output.csv", "text/csv")
    st.divider()
    st.subheader("🤖 Multi-agent sourcing — from analysis to action")
    st.caption("Two agents work in sequence: a Supplier Risk agent flags supply risks, then a Sourcing "
               "Strategist drafts risk-aware recommendations (after Jannelli & Brintrup, 2025).")
    if st.button("Run sourcing agents"):
        if not api_key:
            st.error("Need your Gemini API key (sidebar) to run the agents.")
        else:
            try:
                with st.spinner("Supplier Risk agent assessing supply risk..."):
                    st.session_state["risk_brief"] = supplier_risk_agent(summary, work, api_key, currency)
                with st.spinner("Sourcing Strategist drafting risk-aware brief..."):
                    st.session_state["brief"] = sourcing_strategist(
                        summary, work, api_key, currency, risk_brief=st.session_state["risk_brief"])
            except Exception as e:
                st.error(f"Agent failed: {e}  (if this is a quota limit, wait a few minutes and retry).")
    if st.session_state.get("risk_brief"):
        st.markdown("### 🛡️ Supplier Risk assessment")
        st.markdown(st.session_state["risk_brief"])
    if st.session_state.get("brief"):
        st.markdown("### 📋 Sourcing Strategist brief (risk-aware)")
        st.markdown(st.session_state["brief"])
        st.download_button("⬇ Download sourcing brief (Markdown)",
                           st.session_state["brief"].encode("utf-8"), "sourcing_brief.md", "text/markdown")
elif "work_base" not in st.session_state:
    st.info("Set your key, map your columns, and press **Run analysis** in the sidebar.")