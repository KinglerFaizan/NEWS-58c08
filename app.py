import os
import re
from datetime import datetime, timedelta, timezone
from html import escape
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
:root{
 --bg:#f7f9fc;--card:#fff;--ink:#0f172a;--muted:#64748b;--line:#e6eaf0;
 --blue:#2563eb;--blue2:#4f46e5;--green:#18b981;
}
.stApp{background:var(--bg);color:var(--ink);font-family:Inter,sans-serif}
[data-testid="stAppViewContainer"] .main .block-container{max-width:1500px;padding:0 28px 40px}
header[data-testid="stHeader"]{height:0;background:transparent}
section[data-testid="stSidebar"]{border-right:1px solid #e5e9f0;background:#fff}
section[data-testid="stSidebar"]>div{padding-top:1.1rem}
.top-header{height:82px;margin:0 -28px 25px;padding:0 28px;display:flex;align-items:center;justify-content:space-between;
background:rgba(255,255,255,.97);border-bottom:1px solid #e8ecf2;box-shadow:0 1px 8px rgba(15,23,42,.04)}
.brand{display:flex;align-items:center;gap:14px}.brand-icon{width:62px;height:62px;border-radius:16px;background:linear-gradient(145deg,#3346e8,#6d28d9);
display:flex;align-items:center;justify-content:center;color:#fff;font-size:31px;box-shadow:0 9px 22px rgba(79,70,229,.24)}
.brand-title{font-size:29px;font-weight:900;letter-spacing:-1.2px}.brand-title span{color:#2563eb}
.brand-sub{margin-top:2px;color:#64748b;font-size:10px;font-weight:800;letter-spacing:2px}
.live-pill{margin-left:10px;padding:6px 12px;border-radius:999px;background:#eafaf3;color:#18a56f;font-size:10px;font-weight:900;text-transform:uppercase}
.header-search{width:350px;padding:13px 20px;border:1px solid #e5e9f0;border-radius:28px;background:#fff;color:#64748b;font-size:13px;box-shadow:0 2px 8px rgba(15,23,42,.03)}
.prepared{display:flex;align-items:center;gap:13px}.prepared-meta{text-align:right}.prepared-label{font-size:10px;color:#94a3b8}.prepared-name{font-size:16px;font-weight:800}.prepared-role{font-size:11px;color:#64748b}.avatar{width:48px;height:48px;border-radius:50%;background:linear-gradient(145deg,#2563eb,#4f46e5);color:#fff;
display:flex;align-items:center;justify-content:center;font-size:21px;font-weight:800}
.sidebar-brand{display:flex;align-items:center;gap:10px;padding:5px 4px 20px}.sidebar-brand-icon{width:34px;height:34px;border-radius:10px;background:#eef4ff;color:#2563eb;
display:flex;align-items:center;justify-content:center;font-size:20px}.sidebar-brand-title{font-weight:900;font-size:15px}.sidebar-brand-sub{font-size:9px;color:#94a3b8;letter-spacing:.6px}
section[data-testid="stSidebar"] .stButton>button{border:0!important;background:transparent!important;color:#64748b!important;text-align:left!important;box-shadow:none!important;border-radius:12px!important;padding:11px 13px!important;font-weight:700!important}
section[data-testid="stSidebar"] .stButton>button:hover{background:#eef4ff!important;color:#2563eb!important}
.side-section{margin:12px 4px 8px;font-size:10px;font-weight:900;color:#94a3b8;letter-spacing:1.2px;text-transform:uppercase}
.live-data{border-top:1px solid #edf0f4;border-bottom:1px solid #edf0f4;padding:15px 4px;margin:10px 0}.live-row{display:flex;justify-content:space-between;align-items:center;font-weight:800;font-size:13px}.live-dot{width:9px;height:9px;background:#18b981;border-radius:50%;display:inline-block;margin-right:7px}.active-pill{background:#dcf8eb;color:#18a56f;border-radius:999px;padding:4px 10px;font-size:10px}
.quick-refresh{margin:8px 0 15px}
.quick-refresh .stButton>button{background:#1769ff!important;color:#fff!important;padding:12px!important;border-radius:9px!important}
.section-head{display:flex;justify-content:space-between;align-items:end;margin:4px 0 16px}
.section-title{font-size:27px;font-weight:900;letter-spacing:-.8px}.section-title .bolt{color:#6538ed}.section-sub{color:#7a8799;font-size:13px;margin-top:3px}.view-all{color:#1769ff;font-weight:800;font-size:13px}
.feature-shell{margin-bottom:30px}
.feature-carousel{position:relative;background:#0b1220;border-radius:18px;overflow:hidden;border:1px solid #1e293b;box-shadow:0 18px 42px rgba(15,23,42,.16)}
.feature-slide{display:none;position:relative;height:390px;background:#0b1220}
.feature-slide.active{display:block}
.feature-img{position:absolute;inset:0;height:100%;background:linear-gradient(135deg,#172033,#0b1220);overflow:hidden}
.feature-img img{width:100%;height:100%;object-fit:cover;display:block;opacity:.82}
.feature-img:after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,rgba(5,10,20,.94) 0%,rgba(5,10,20,.72) 35%,rgba(5,10,20,.18) 72%,rgba(5,10,20,.38) 100%),linear-gradient(0deg,rgba(5,10,20,.62),transparent 45%)}
.feature-body{position:absolute;z-index:2;left:0;bottom:0;width:68%;padding:42px 46px 44px;color:#fff}
.feature-kicker{display:flex;align-items:center;gap:10px;font-size:10px;font-weight:800;letter-spacing:1.5px;color:#bfdbfe;text-transform:uppercase;margin-bottom:15px}
.feature-kicker:before{content:"";width:28px;height:2px;background:#3b82f6}
.feature-title{font-size:31px;font-weight:850;line-height:1.18;letter-spacing:-.8px;color:#fff;max-width:850px}
.feature-title a{color:#fff;text-decoration:none}
.feature-title a:hover{color:#bfdbfe}
.feature-desc{font-size:13px;color:#cbd5e1;line-height:1.55;margin-top:12px;max-width:760px}
.feature-meta{font-size:10px;font-weight:700;color:#94a3b8;margin-top:18px;letter-spacing:.2px}
.feature-counter{position:absolute;z-index:4;right:24px;top:22px;font-size:10px;font-weight:800;letter-spacing:1px;color:#e2e8f0;background:rgba(15,23,42,.62);border:1px solid rgba(255,255,255,.16);border-radius:999px;padding:7px 11px;backdrop-filter:blur(8px)}
.feature-dots{position:absolute;z-index:4;left:46px;bottom:22px;display:flex;gap:6px}
.feature-dot{width:22px;height:3px;border-radius:999px;background:rgba(255,255,255,.28);transition:all .25s}
.feature-dot.active{width:38px;background:#60a5fa}
.latest-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
.latest-card{background:#fff;border:1px solid #e5e9f0;border-radius:14px;padding:11px;box-shadow:0 4px 16px rgba(15,23,42,.045);min-height:0;display:block;transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease}
.latest-card:hover{transform:translateY(-2px);border-color:#cbd5e1;box-shadow:0 10px 26px rgba(15,23,42,.08)}
.latest-image{width:100%;height:205px;border-radius:9px;overflow:hidden;background:#eef2f7}
.latest-image img{width:100%;height:100%;object-fit:cover;display:block}
.latest-content{padding:13px 7px 8px}
.latest-tags{margin-bottom:8px}
.latest-tag{display:inline-block;border-radius:5px;padding:4px 7px;font-size:8px;font-weight:900;letter-spacing:.8px;text-transform:uppercase;background:#f1f5f9;color:#475569;margin-right:7px}
.latest-title{font-size:18px;font-weight:850;line-height:1.3;margin-bottom:7px;letter-spacing:-.25px}
.latest-title a{color:#0f172a;text-decoration:none}
.latest-title a:hover{color:#2563eb}
.latest-desc{font-size:12px;line-height:1.52;color:#64748b}
.latest-meta{margin-top:12px;font-size:10px;color:#64748b;font-weight:700}
@media(max-width:1000px){.header-search{display:none}.feature-slide{height:350px}.feature-body{width:78%;padding:34px}.feature-title{font-size:26px}.latest-grid{grid-template-columns:1fr}}
@media(max-width:650px){.feature-slide{height:430px}.feature-body{width:100%;padding:24px}.feature-title{font-size:22px}.feature-desc{font-size:12px}.feature-dots{left:24px}.latest-grid{grid-template-columns:1fr}.latest-image{height:190px}.brand-sub{display:none}}
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
    desc = escape(str(row.get("description") or row.get("content") or "No description available."))[:300]
    url = str(row.get("url") or "").strip()
    source = escape(str(row.get("source") or "Unknown"))
    category = escape(str(row.get("category") or "News"))
    image = escape(str(row.get("image_url") or ""), quote=True)
    img_html = (
        f'<img src="{image}" alt="" />'
        if image else '<div style="height:100%;display:flex;align-items:center;justify-content:center;color:#94a3b8;font-size:28px">◈</div>'
    )
    link = f'<a href="{escape(url, quote=True)}" target="_blank">{title}</a>' if url else title
    return f"""
<div class="latest-card">
  <div class="latest-image">{img_html}</div>
  <div class="latest-content">
    <div class="latest-tags"><span class="latest-tag">{category}</span></div>
    <div class="latest-title">{link}</div>
    <div class="latest-desc">{desc}</div>
    <div class="latest-meta">{source} &nbsp;•&nbsp; {fmt_date(row.get("published_at"))}</div>
  </div>
</div>
"""


def render_featured_carousel(rows):
    """Render a five-story executive newsroom carousel; one story at a time."""
    rows = rows[:5]
    if not rows:
        return

    slides = []
    dots = []
    for idx, row in enumerate(rows):
        title = escape(str(row.get("title") or "Untitled"))
        desc = escape(str(row.get("description") or row.get("content") or ""))[:430]
        category = escape(str(row.get("category") or "News"))
        source = escape(str(row.get("source") or "Unknown"))
        image = escape(str(row.get("image_url") or ""), quote=True)
        url = str(row.get("url") or "").strip()

        fallback = "data:image/svg+xml;charset=UTF-8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1200 700'%3E%3Cdefs%3E%3ClinearGradient id='g' x1='0' x2='1'%3E%3Cstop stop-color='%231e293b'/%3E%3Cstop offset='1' stop-color='%230f172a'/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='1200' height='700' fill='url(%23g)'/%3E%3Ctext x='70' y='620' fill='%2394a3b8' font-family='Arial' font-size='30'%3EAUDIT INTELLIGENCE%3C/text%3E%3C/svg%3E"
        if image:
            img_html = f'<img src="{image}" alt="" onerror="this.onerror=null;this.src=\'{fallback}\';" />'
        else:
            img_html = f'<img src="{fallback}" alt="" />'

        title_html = f'<a href="{escape(url, quote=True)}" target="_blank">{title}</a>' if url else title
        active = " active" if idx == 0 else ""
        slides.append(
            f'<article class="feature-slide{active}">'
            f'<div class="feature-img">{img_html}</div>'
            f'<div class="feature-body">'
            f'<div class="feature-kicker">{category} &nbsp;·&nbsp; Featured Intelligence</div>'
            f'<div class="feature-title">{title_html}</div>'
            f'<div class="feature-desc">{desc}</div>'
            f'<div class="feature-meta">{source} &nbsp;•&nbsp; {fmt_date(row.get("published_at"))}</div>'
            f'</div></article>'
        )
        dots.append(f'<span class="feature-dot{" active" if idx == 0 else ""}"></span>')

    html = f"""
<div class="feature-shell">
  <div class="feature-carousel">
    {''.join(slides)}
    <div class="feature-counter"><span id="feature-index">01</span> — {len(rows):02d}</div>
    <div class="feature-dots">{''.join(dots)}</div>
  </div>
</div>
<script>
(function() {{
  const root = document.currentScript.parentElement;
  const slides = root.querySelectorAll('.feature-slide');
  const dots = root.querySelectorAll('.feature-dot');
  const counter = root.querySelector('#feature-index');
  let current = 0;
  function show(i) {{
    slides.forEach((s, n) => s.classList.toggle('active', n === i));
    dots.forEach((d, n) => d.classList.toggle('active', n === i));
    if (counter) counter.textContent = String(i + 1).padStart(2, '0');
  }}
  if (slides.length > 1) {{
    setInterval(() => {{
      current = (current + 1) % slides.length;
      show(current);
    }}, 5000);
  }}
}})();
</script>
"""
    components.html(html, height=410, scrolling=False)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
      <div class="sidebar-brand-icon">⌂</div>
      <div><div class="sidebar-brand-title">News Intelligence</div>
      <div class="sidebar-brand-sub">Audit &amp; Banking Briefing</div></div>
    </div>
    """, unsafe_allow_html=True)

    nav = ["⌂  News Feed","▦  Categories","♧  Global Banks","♧  Watchlist","▱  Saved","⇧  Export","⚙  Diagnostics"]
    for idx, label in enumerate(nav):
        st.button(label, key=f"nav_{idx}", use_container_width=True)

    st.markdown('<div class="side-section">Live Data</div>', unsafe_allow_html=True)
    st.markdown('<div class="live-data"><div class="live-row"><span><span class="live-dot"></span>NewsData.io</span><span class="active-pill">Active</span></div><div style="font-size:10px;color:#94a3b8;margin-top:9px">Live banking intelligence feed</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="side-section">Quick Controls</div>', unsafe_allow_html=True)
    st.markdown('<div class="quick-refresh">', unsafe_allow_html=True)
    refresh = st.button("⟳  Refresh All Data", use_container_width=True, key="refresh_news")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="side-section">Filters & Settings</div>', unsafe_allow_html=True)
    lookback = st.slider("News lookback", 1, 7, 7, 1)
    selected = st.multiselect("Categories", list(CATEGORY_TERMS.keys()), default=list(CATEGORY_TERMS.keys()))

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
<div class="top-header">
  <div class="brand">
    <div class="brand-icon">⌕</div>
    <div>
      <div><span class="brand-title">Audit<span> Intelligence</span></span><span class="live-pill">● LIVE</span></div>
      <div class="brand-sub">GLOBAL BANKING RISK &amp; CONTROLS BRIEFING</div>
    </div>
  </div>
  <div class="header-search">⌕ &nbsp; Search news, banks, regulation, audit...</div>
  <div class="prepared">
    <div class="prepared-meta"><div class="prepared-label">Prepared for</div><div class="prepared-name">Pragati</div><div class="prepared-role">Head of Internal Audit</div></div>
    <div class="avatar">P</div>
  </div>
</div>
""", unsafe_allow_html=True,
)

# ============================================================
# TOP NEWS
# ============================================================

st.markdown(
    f'<div class="section-head"><div><div class="section-title"><span class="bolt">ϟ</span> Today’s Top Banking News</div><div class="section-sub">Key developments in banking, regulation, risk and technology</div></div><div class="view-all">{datetime.now(timezone.utc).strftime("%A, %d %B %Y")} &nbsp; →</div></div>',
    unsafe_allow_html=True,
)

# Category controls remain functional while visually matching the reference.
st.markdown('<div class="filter-bar"><span class="filter-label">FILTER</span>', unsafe_allow_html=True)
filter_cols = st.columns(5)
filter_names = ["ALL NEWS","Transformation","Regulation","People","Global Banks"]
filter_keys = ["ALL"] + filter_names[1:]
for col, label, key in zip(filter_cols, filter_names, filter_keys):
    with col:
        if st.button(label, key=f"category_{key}", use_container_width=True):
            st.session_state["active_category"] = key
            st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

active_category = st.session_state.get("active_category", "ALL")
visible_news = news if active_category == "ALL" else [r for r in news if r.get("category") == active_category]

featured = visible_news[:5]
if featured:
    render_featured_carousel(featured)

# ============================================================
# LATEST NEWS
# ============================================================

st.markdown(
    '<div class="section-head"><div><div class="section-title">▣ Latest News &amp; Insights</div><div class="section-sub">Real-time updates from global sources relevant to audit, risk and compliance</div></div><div class="view-all">Latest&nbsp;⌄</div></div>',
    unsafe_allow_html=True,
)

if not visible_news:
    st.markdown('<div class="empty"><h3>No banking stories were returned.</h3><p>Try another category or refresh the feed.</p></div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="latest-grid">', unsafe_allow_html=True)
    for row in visible_news:
        st.markdown(card(row), unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# FOOTER
# ============================================================

st.markdown("---")
st.caption(
    f"Last refresh: {datetime.now(timezone.utc).strftime('%d %b %Y %H:%M UTC')} · "
    "Audit Intelligence"
)
