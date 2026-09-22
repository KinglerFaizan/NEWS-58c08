import os
import re
from datetime import datetime, timedelta, timezone
from html import escape
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st

import news_providers as npv

# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="Audit Intelligence | Global Banking News",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# The supplied key is kept as a fallback for this deployment.
# Prefer Streamlit Secrets / environment variables in production.
NEWSDATA_API_KEY_HARDCODED = "pub_cb85f4550d47494e98426daa602dd2bf"


def get_newdata_api_key():
    for name in ("NEWSDATA_API_KEY", "NEWSDATA_KEY"):
        value = os.getenv(name, "").strip()
        if value:
            return value
    try:
        for name in ("NEWSDATA_API_KEY", "NEWSDATA_KEY"):
            value = str(st.secrets.get(name, "")).strip()
            if value:
                return value
    except Exception:
        pass
    return NEWSDATA_API_KEY_HARDCODED.strip()


# ============================================================
# UI
# ============================================================

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600&display=swap');

:root {
  --bg:#f6f8fb; --card:#fff; --ink:#0b1220; --muted:#64748b;
  --line:#e2e8f0; --blue:#2563eb; --blue2:#1d4ed8;
}
.stApp { background:var(--bg); color:var(--ink); font-family:Inter,sans-serif; }
[data-testid="stAppViewContainer"] .main .block-container {
  max-width:1500px; padding-top:1rem; padding-bottom:3rem;
}
header[data-testid="stHeader"] { background:transparent; }
.hero {
  display:flex; justify-content:space-between; align-items:center; gap:24px;
  background:linear-gradient(135deg,#0b1220,#172554 58%,#1e40af);
  color:white; border-radius:22px; padding:28px 32px; margin-bottom:18px;
  box-shadow:0 16px 40px rgba(15,23,42,.16);
}
.hero h1 { margin:0; font-size:34px; font-weight:900; letter-spacing:-1px; }
.hero p { margin:7px 0 0; color:#cbd5e1; font-size:13px; }
.hero-badge {
  border:1px solid rgba(255,255,255,.2); background:rgba(255,255,255,.08);
  border-radius:14px; padding:12px 16px; text-align:center; min-width:130px;
}
.hero-badge b { display:block; font-size:22px; }
.hero-badge span { font-size:9px; letter-spacing:1px; text-transform:uppercase; color:#bfdbfe; }
.metric {
  background:#fff; border:1px solid var(--line); border-radius:14px;
  padding:14px 16px; box-shadow:0 2px 8px rgba(15,23,42,.04);
}
.metric b { display:block; font-size:23px; }
.metric span { font-size:9px; text-transform:uppercase; letter-spacing:.8px; color:var(--muted); font-weight:800; }
.news-card {
  background:#fff; border:1px solid var(--line); border-radius:16px;
  padding:18px 20px; margin-bottom:12px;
  box-shadow:0 2px 10px rgba(15,23,42,.04);
}
.news-card:hover { border-color:#bfdbfe; box-shadow:0 7px 22px rgba(37,99,235,.08); }
.news-title { font-size:17px; line-height:1.3; font-weight:800; margin:0 0 7px; }
.news-title a { color:#0b1220; text-decoration:none; }
.news-title a:hover { color:var(--blue); }
.news-desc { color:#475569; font-size:12.5px; line-height:1.55; }
.meta { color:#94a3b8; font:600 10px 'JetBrains Mono',monospace; margin-top:10px; }
.tag {
  display:inline-block; border-radius:999px; padding:4px 9px; margin-right:6px;
  font-size:9px; font-weight:800; letter-spacing:.6px; text-transform:uppercase;
  background:#eff6ff; color:#1d4ed8; border:1px solid #dbeafe;
}
.source { color:#64748b; font-size:10px; font-weight:700; }
.empty {
  background:#fff; border:1px dashed #cbd5e1; border-radius:16px;
  padding:40px; text-align:center; color:#64748b;
}
.stButton>button { border-radius:9px; font-weight:700; }
[data-testid="stTabs"] button[role="tab"] { font-weight:800 !important; }
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# CLASSIFICATION
# ============================================================

CATEGORY_TERMS = {
    "Transformation": [
        "digital transformation", "artificial intelligence", "generative ai",
        "machine learning", "automation", "cloud", "open banking",
        "digital banking", "payments", "fintech", "data analytics",
        "technology", "cybersecurity", "cyber security",
    ],
    "Regulation": [
        "regulation", "regulatory", "regulator", "compliance", "directive",
        "guidance", "legislation", "rulemaking", "supervisory", "sanction",
        "fine", "penalty", "capital requirement", "basel",
    ],
    "People": [
        "appointed", "appointment", "ceo", "cfo", "chief executive",
        "chief financial officer", "joins", "joined", "resigns",
        "resignation", "steps down", "leadership", "executive",
    ],
    "Cyber & Tech": [
        "cyber", "cybersecurity", "ransomware", "data breach", "breach",
        "hack", "hacking", "malware", "phishing", "fraud", "identity theft",
        "technology", "software", "ai", "artificial intelligence",
    ],
    "Global Banks": [
        "hsbc", "jpmorgan", "jp morgan", "barclays", "deutsche bank",
        "bank of america", "wells fargo", "citigroup", "citi",
        "standard chartered", "ubs", "credit suisse", "morgan stanley",
        "goldman sachs", "bnpparibas", "bnp paribas", "santander",
    ],
}

BANKING_TERMS = [
    "bank", "banking", "lender", "lending", "credit", "mortgage",
    "financial institution", "financial services", "retail bank",
    "commercial bank", "central bank", "investment bank", "payments",
]


def present(text, term):
    return bool(re.search(r"(?<![a-z0-9])" + re.escape(term.lower()) + r"(?![a-z0-9])", text))


def classify(row):
    text = " ".join(
        str(row.get(k) or "") for k in ("title", "description", "content", "source")
    ).lower()

    non_banking = (
        "power bank", "blood bank", "food bank", "data bank", "memory bank",
        "sperm bank", "gene bank", "seed bank", "river bank", "bank holiday",
        "bank shot",
    )
    if any(phrase in text for phrase in non_banking):
        return None

    scores = {cat: 0 for cat in CATEGORY_TERMS}
    for cat, terms in CATEGORY_TERMS.items():
        scores[cat] = sum(1 for term in terms if present(text, term))

    banking_context = any(present(text, term) for term in BANKING_TERMS)
    if not banking_context:
        return None

    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "Global Banks" if any(
            present(text, x) for x in CATEGORY_TERMS["Global Banks"]
        ) else "Transformation"

    return best


# ============================================================
# DATA
# ============================================================

@st.cache_data(ttl=600, show_spinner=False)
def load_news(api_key, lookback_days, selected_categories):
    rows, errors, diagnostics = npv.fetch_all(
        {"newsdata": api_key},
        lookback_days=lookback_days,
        categories=None,
        max_workers=4,
    )

    cleaned = []
    for row in rows:
        category = classify(row)
        if category is None:
            continue
        if selected_categories and category not in selected_categories:
            continue

        item = dict(row)
        item["category"] = category
        cleaned.append(item)

    cleaned.sort(
        key=lambda x: str(x.get("published_at") or ""),
        reverse=True,
    )
    return cleaned, errors, diagnostics


def fmt_date(value):
    if not value:
        return "Unknown time"
    try:
        dt = pd.to_datetime(value, utc=True)
        return dt.strftime("%d %b %Y · %H:%M UTC")
    except Exception:
        return str(value)[:32]


def card(row):
    title = escape(str(row.get("title") or "Untitled"))
    desc = escape(str(row.get("description") or row.get("content") or "No description available."))
    desc = desc[:420]
    url = str(row.get("url") or "").strip()
    source = escape(str(row.get("source") or "Unknown"))
    category = escape(str(row.get("category") or "News"))

    link = (
        f'<a href="{escape(url, quote=True)}" target="_blank">{title}</a>'
        if url else title
    )

    st.markdown(
        f"""
<div class="news-card">
  <div><span class="tag">{category}</span><span class="source">{source}</span></div>
  <div class="news-title">{link}</div>
  <div class="news-desc">{desc}</div>
  <div class="meta">{fmt_date(row.get("published_at"))}</div>
</div>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("## ⚙️ Intelligence Controls")
    lookback = st.slider("News lookback", 1, 7, 2, 1)
    selected = st.multiselect(
        "Categories",
        list(CATEGORY_TERMS.keys()),
        default=list(CATEGORY_TERMS.keys()),
    )

    refresh = st.button("🔄 Refresh News", use_container_width=True)

    st.markdown("---")
    st.caption("Sources")
    st.write("• NewsData.io")
    st.write("• Google News RSS fallback")
    st.caption("The fallback uses public RSS and does not consume NewsData credits.")

    if refresh:
        load_news.clear()
        st.rerun()


# ============================================================
# LOAD
# ============================================================

api_key = get_newdata_api_key()

with st.spinner("Collecting banking intelligence…"):
    news, errors, diagnostics = load_news(api_key, lookback, tuple(selected))

# ============================================================
# HEADER
# ============================================================

st.markdown(
    f"""
<div class="hero">
  <div>
    <h1>Audit Intelligence</h1>
    <p>Global banking news · regulation · transformation · people · cyber & technology</p>
  </div>
  <div class="hero-badge">
    <b>{len(news)}</b>
    <span>Relevant stories</span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# ============================================================
# METRICS
# ============================================================

counts = {cat: sum(1 for r in news if r.get("category") == cat) for cat in CATEGORY_TERMS}

cols = st.columns(6)
metric_names = [
    ("Total", len(news)),
    ("Transformation", counts["Transformation"]),
    ("Regulation", counts["Regulation"]),
    ("People", counts["People"]),
    ("Cyber & Tech", counts["Cyber & Tech"]),
    ("Global Banks", counts["Global Banks"]),
]
for col, (name, value) in zip(cols, metric_names):
    with col:
        st.markdown(
            f'<div class="metric"><b>{value}</b><span>{escape(name)}</span></div>',
            unsafe_allow_html=True,
        )

st.markdown("")

if errors:
    with st.expander("⚠️ Ingestion diagnostics", expanded=True):
        for err in errors:
            st.warning(err)

        pp = diagnostics.get("per_provider", {})
        for provider, info in pp.items():
            st.write(
                f"**{provider}** — requests: {info.get('requests', 0)} · "
                f"articles: {info.get('articles', 0)} · "
                f"errors: {info.get('errors', 0)} · "
                f"quota hits: {info.get('quota_hits', 0)}"
            )

# ============================================================
# NEWSROOM
# ============================================================

if not news:
    st.markdown(
        """
<div class="empty">
  <h3>No banking stories were returned.</h3>
  <p>Use <b>Refresh News</b>. If the API is unavailable, the app will use its public RSS fallback.</p>
</div>
""",
        unsafe_allow_html=True,
    )
else:
    tabs = ["ALL"] + list(CATEGORY_TERMS.keys())
    tab_objs = st.tabs(tabs)

    for tab, name in zip(tab_objs, tabs):
        with tab:
            subset = news if name == "ALL" else [r for r in news if r.get("category") == name]
            st.caption(f"{len(subset)} stories")
            if not subset:
                st.info("No stories in this category for the selected period.")
            else:
                for row in subset:
                    card(row)

# ============================================================
# FOOTER
# ============================================================

st.markdown("---")
st.caption(
    f"Last refresh: {datetime.now(timezone.utc).strftime('%d %b %Y %H:%M UTC')} · "
    "Audit Intelligence"
)
