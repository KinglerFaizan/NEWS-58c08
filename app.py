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
:root{--bg:#f7f9fc;--ink:#0f172a;--muted:#64748b;--line:#e5eaf1;--blue:#1769ff;--navy:#101b30}
.stApp{background:var(--bg);font-family:Inter,sans-serif;color:var(--ink)}
[data-testid="stAppViewContainer"] .main .block-container{max-width:1500px;padding:0 26px 24px}
header[data-testid="stHeader"]{height:0;background:transparent}
section[data-testid="stSidebar"]{background:#fff;border-right:1px solid #e5e9f0}
section[data-testid="stSidebar"]>div{padding-top:.9rem}
section[data-testid="stSidebar"] .stButton>button{border:0!important;background:transparent!important;color:#64748b!important;text-align:left!important;box-shadow:none!important;border-radius:10px!important;padding:9px 11px!important;font-size:13px!important;font-weight:700!important}
section[data-testid="stSidebar"] .stButton>button:hover{background:#eef4ff!important;color:#1769ff!important}
.sidebar-brand{display:flex;align-items:center;gap:10px;padding:4px 3px 13px}.sidebar-brand-icon{width:34px;height:34px;border-radius:9px;background:#eef4ff;color:#1769ff;display:flex;align-items:center;justify-content:center;font-size:18px}.sidebar-brand-title{font-weight:900;font-size:14px}.sidebar-brand-sub{font-size:8px;color:#94a3b8;letter-spacing:.7px;margin-top:1px}
.side-section{margin:10px 3px 7px;font-size:9px;font-weight:900;color:#94a3b8;letter-spacing:1.1px;text-transform:uppercase}
.live-data{border-top:1px solid #edf0f4;border-bottom:1px solid #edf0f4;padding:11px 3px;margin:7px 0}.live-row{display:flex;justify-content:space-between;align-items:center;font-weight:800;font-size:12px}.live-dot{width:8px;height:8px;background:#18b981;border-radius:50%;display:inline-block;margin-right:6px}.active-pill{background:#dcf8eb;color:#18a56f;border-radius:999px;padding:3px 8px;font-size:9px}
.quick-refresh{margin:5px 0 10px}.quick-refresh .stButton>button{background:#1769ff!important;color:#fff!important;padding:10px!important;border-radius:9px!important}
.top-header{height:86px;margin:0 -26px 20px;padding:0 26px;display:flex;align-items:center;justify-content:space-between;background:#fff;border-bottom:1px solid #e7ebf1;box-shadow:0 1px 8px rgba(15,23,42,.035)}
.brand{display:flex;align-items:center;gap:11px}.brand-icon{width:58px;height:58px;border-radius:13px;background:linear-gradient(145deg,#246bff,#5338dc);display:flex;align-items:center;justify-content:center;color:#fff;font-size:25px;box-shadow:0 7px 18px rgba(37,99,235,.22)}.brand-title{font-size:24px;font-weight:900;letter-spacing:-1px}.brand-title span{color:#2563eb}.brand-sub{color:#64748b;font-size:8px;font-weight:800;letter-spacing:1.7px;margin-top:1px}.live-pill{margin-left:8px;padding:4px 9px;border-radius:999px;background:#eafaf3;color:#18a56f;font-size:9px;font-weight:900}
.header-search{width:330px;padding:10px 17px;border:1px solid #e4e9f1;border-radius:24px;background:#fff;color:#64748b;font-size:12px}.prepared{display:flex;align-items:center;gap:10px}.prepared-meta{text-align:right}.prepared-label{font-size:9px;color:#94a3b8}.prepared-name{font-size:14px;font-weight:800}.prepared-role{font-size:10px;color:#64748b}.avatar{width:40px;height:40px;border-radius:50%;background:linear-gradient(145deg,#2563eb,#4f46e5);color:#fff;display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:800}
.section-head{display:flex;justify-content:space-between;align-items:end;margin:0 0 9px}.section-title{font-size:22px;font-weight:900;letter-spacing:-.65px}.section-title .bolt{color:#4f46e5}.section-sub{color:#7a8799;font-size:11px;margin-top:2px}.view-all{color:#1769ff;font-weight:800;font-size:11px}
.filter-bar{display:flex;align-items:center;gap:7px;flex-wrap:nowrap;margin:0 0 14px}.filter-label{font-size:9px;font-weight:900;color:#94a3b8;letter-spacing:1px;min-width:38px}.filter-bar .stButton>button{height:38px!important;border:1px solid #dfe5ed!important;background:#fff!important;color:#334155!important;border-radius:8px!important;font-size:11px!important;font-weight:700!important;padding:0 12px!important}.filter-bar .stButton>button:hover{border-color:#a9c5ff!important;color:#1769ff!important;background:#f5f8ff!important}
.feature-shell{margin-bottom:28px}.feature-carousel{position:relative;background:#0d172b;border-radius:14px;overflow:hidden;border:1px solid #1c2940;box-shadow:0 10px 26px rgba(15,23,42,.12)}.feature-slide{display:none;position:relative;height:235px;background:#0d172b}.feature-slide.active{display:block}.feature-img{position:absolute;inset:0;height:100%;overflow:hidden}.feature-img img{width:100%;height:100%;object-fit:cover;display:block;opacity:.86}.feature-img:after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,rgba(5,12,25,.96) 0%,rgba(5,12,25,.78) 31%,rgba(5,12,25,.18) 67%,rgba(5,12,25,.22) 100%),linear-gradient(0deg,rgba(5,12,25,.45),transparent 55%)}.feature-body{position:absolute;z-index:2;left:0;bottom:0;width:62%;padding:24px 30px;color:#fff}.feature-kicker{display:flex;align-items:center;gap:8px;font-size:8px;font-weight:900;letter-spacing:1.2px;color:#bfdbfe;text-transform:uppercase;margin-bottom:8px}.feature-kicker:before{content:"";width:22px;height:2px;background:#3b82f6}.feature-title{font-size:23px;font-weight:850;line-height:1.18;letter-spacing:-.45px;color:#fff;max-width:700px}.feature-title a{color:#fff;text-decoration:none}.feature-desc{font-size:11px;color:#cbd5e1;line-height:1.4;margin-top:7px;max-width:650px}.feature-meta{font-size:9px;font-weight:700;color:#94a3b8;margin-top:9px}.feature-counter{position:absolute;z-index:4;right:16px;top:13px;font-size:9px;font-weight:800;letter-spacing:1px;color:#e2e8f0;background:rgba(15,23,42,.62);border:1px solid rgba(255,255,255,.16);border-radius:999px;padding:5px 8px}.feature-dots{position:absolute;z-index:4;right:17px;bottom:14px;display:flex;gap:4px}.feature-dot{width:14px;height:3px;border-radius:999px;background:rgba(255,255,255,.35)}.feature-dot.active{width:26px;background:#60a5fa}
.latest-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px}.latest-card{background:#fff;border:1px solid #e3e8ef;border-radius:11px;padding:8px;box-shadow:0 3px 11px rgba(15,23,42,.045);min-height:0;display:block;transition:transform .16s ease,box-shadow .16s ease}.latest-card:hover{transform:translateY(-2px);box-shadow:0 8px 20px rgba(15,23,42,.08)}.latest-image{width:100%;height:132px;border-radius:8px;overflow:hidden;background:#eef2f7}.latest-image img{width:100%;height:100%;object-fit:cover;display:block}.latest-content{padding:9px 3px 3px}.latest-tags{margin-bottom:6px}.latest-tag{display:inline-block;border-radius:4px;padding:3px 6px;font-size:7px;font-weight:900;letter-spacing:.7px;text-transform:uppercase;background:#eef4ff;color:#2563eb;margin-right:5px}.latest-title{font-size:15px;font-weight:850;line-height:1.28;margin-bottom:5px;letter-spacing:-.15px}.latest-title a{color:#0f172a;text-decoration:none}.latest-title a:hover{color:#2563eb}.latest-desc{font-size:10.5px;line-height:1.4;color:#64748b;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}.latest-meta{margin-top:8px;font-size:8px;color:#64748b;font-weight:700}
@media(max-width:1200px){.latest-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.feature-body{width:72%}}@media(max-width:900px){.header-search{display:none}.latest-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.feature-slide{height:225px}}@media(max-width:600px){.latest-grid{grid-template-columns:1fr}.feature-slide{height:330px}.feature-body{width:100%;padding:22px}.feature-title{font-size:21px}.feature-desc{font-size:11px}}
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
        f'<img src="{image}" alt="" onerror="this.style.display=\'none\';" />'
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
    """Five-story premium hero carousel with manual arrows + 5s auto rotation."""
    rows = rows[:5]
    if not rows:
        return

    slides = []
    dots = []
    for idx, row in enumerate(rows):
        title = escape(str(row.get("title") or "Untitled"))
        desc = escape(str(row.get("description") or row.get("content") or ""))[:420]
        category = escape(str(row.get("category") or "News"))
        source = escape(str(row.get("source") or "Unknown"))
        image = escape(str(row.get("image_url") or ""), quote=True)
        url = str(row.get("url") or "").strip()
        fallback = "https://images.unsplash.com/photo-1559526324-593bc073d938?auto=format&fit=crop&w=1600&q=80"
        img_html = (
            f'<img src="{image}" alt="" onerror="this.onerror=null;this.src=\'{fallback}\';">'
            if image else f'<img src="{fallback}" alt="">'
        )
        title_html = f'<a href="{escape(url, quote=True)}" target="_blank">{title}</a>' if url else title
        slides.append(
            f'<article class="fs"><div class="fi">{img_html}<div class="shade"></div></div>'
            f'<div class="fb"><div class="fk"><span></span>{category}</div>'
            f'<div class="ft">{title_html}</div><div class="fd">{desc}</div>'
            f'<div class="fm">{source} &nbsp;•&nbsp; {fmt_date(row.get("published_at"))}</div></div></article>'
        )
        dots.append(f'<i class="dot {"on" if idx == 0 else ""}"></i>')

    html = f"""
<style>
*{{box-sizing:border-box}}body{{margin:0;background:transparent;font-family:Inter,Arial,sans-serif}}
.hero{{position:relative;width:100%;height:210px;border-radius:12px;overflow:hidden;background:#0d172b;border:1px solid #dce3ec;box-shadow:0 7px 20px rgba(15,23,42,.10)}}
.fs{{position:absolute;inset:0;display:none;background:#0d172b}}
.fs.active{{display:block}}
.fi,.fi img,.shade{{position:absolute;inset:0;width:100%;height:100%}}
.fi img{{object-fit:cover;display:block}}
.shade{{background:linear-gradient(90deg,rgba(7,16,31,.94) 0%,rgba(7,16,31,.72) 34%,rgba(7,16,31,.15) 72%,rgba(7,16,31,.15) 100%),linear-gradient(0deg,rgba(7,16,31,.42),transparent 58%)}}
.fb{{position:absolute;z-index:3;left:0;bottom:0;width:66%;padding:22px 26px;color:#fff}}
.fk{{display:inline-flex;align-items:center;gap:8px;font-size:9px;font-weight:900;letter-spacing:.8px;color:#fff;text-transform:uppercase;background:#1769ff;border-radius:7px;padding:6px 10px;margin-bottom:9px}}
.ft{{font-size:22px;font-weight:850;line-height:1.16;letter-spacing:-.35px;color:#fff}}
.ft a{{color:#fff;text-decoration:none}}.fd{{font-size:11px;line-height:1.4;color:#d8e1ed;margin-top:6px;max-width:670px}}.fm{{font-size:9px;color:#c3cfdd;font-weight:700;margin-top:8px}}
.count{{position:absolute;z-index:6;right:74px;top:16px;color:#0f172a;background:#fff;border:1px solid #dce3ec;border-radius:999px;padding:7px 10px;font-size:9px;font-weight:900;letter-spacing:.7px}}
.arrow{{position:absolute;z-index:7;top:12px;width:40px;height:40px;border-radius:50%;border:1px solid #dce3ec;background:#fff;color:#0f172a;font-size:23px;line-height:36px;text-align:center;cursor:pointer;box-shadow:0 3px 10px rgba(15,23,42,.08)}}
.arrow:hover{{background:#f1f5f9}}.prev{{right:122px}}.next{{right:18px}}
.dots{{position:absolute;z-index:6;right:20px;bottom:14px;display:flex;gap:5px}}.dot{{width:7px;height:7px;border-radius:50%;background:rgba(255,255,255,.65);display:block}}.dot.on{{background:#fff;box-shadow:0 0 0 2px rgba(255,255,255,.22)}}
@media(max-width:700px){{.hero{{height:290px}}.fb{{width:100%;padding:20px}}.ft{{font-size:20px}}.fd{{font-size:10px}}}}
</style>
<div class="hero">
  {''.join(slides)}
  <button class="arrow prev" aria-label="Previous">‹</button>
  <div class="count"><span id="n">01</span> / {len(rows):02d}</div>
  <button class="arrow next" aria-label="Next">›</button>
  <div class="dots">{''.join(dots)}</div>
</div>
<script>
(() => {{
 const root=document.currentScript.parentElement, slides=[...root.querySelectorAll('.fs')], dots=[...root.querySelectorAll('.dot')], n=root.querySelector('#n');
 let i=0;
 function show(x) {{
   i=(x+slides.length)%slides.length;
   slides.forEach((s,k)=>s.classList.toggle('active',k===i));
   dots.forEach((d,k)=>d.classList.toggle('on',k===i));
   n.textContent=String(i+1).padStart(2,'0');
 }}
 root.querySelector('.prev').onclick=()=>show(i-1);
 root.querySelector('.next').onclick=()=>show(i+1);
 show(0);
 setInterval(()=>show(i+1),5000);
}})();
</script>
"""
    components.html(html, height=220, scrolling=False)


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
    """
<div class="top-header">
  <div class="brand">
    <div class="brand-icon">⌁</div>
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
# FEATURED INTELLIGENCE
# ============================================================

st.markdown(
    '<div class="section-head"><div><div class="section-title"><span class="bolt">▌</span> Featured Intelligence</div><div class="section-sub">Key developments in banking, regulation, risk and technology</div></div><div class="view-all">01 — 05</div></div>',
    unsafe_allow_html=True,
)

active_category = st.session_state.get("active_category", "ALL")
visible_news = news if active_category == "ALL" else [r for r in news if r.get("category") == active_category]

featured = visible_news[:5]
if featured:
    render_featured_carousel(featured)

# ============================================================
# LATEST NEWS & FILTERS
# ============================================================

st.markdown(
    '<div class="section-head"><div><div class="section-title"><span class="bolt">▌</span> Latest News &amp; Insights</div><div class="section-sub">Real-time updates from global sources relevant to audit, risk and compliance</div></div><div class="view-all">View All&nbsp; →</div></div>',
    unsafe_allow_html=True,
)

st.markdown('<div class="filter-bar"><span class="filter-label">FILTER</span>', unsafe_allow_html=True)
filter_cols = st.columns(6)
filter_names = ["ALL NEWS","Transformation","Regulation","People","Cyber & Technology","Global Banks"]
filter_keys = ["ALL"] + filter_names[1:]
for col, label, key in zip(filter_cols, filter_names, filter_keys):
    with col:
        if st.button(label, key=f"category_{key}", use_container_width=True, type="primary" if key == active_category else "secondary"):
            st.session_state["active_category"] = key
            st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

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
