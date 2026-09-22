from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from urllib.parse import quote, urlparse, urlunparse, parse_qsl, urlencode
import xml.etree.ElementTree as ET

import requests


PROVIDERS = {
    "newsdata": {
        "label": "NewsData.io",
        "endpoint": "https://newsdata.io/api/1/latest",
        "max_query_len": 100,
        "page_size": 10,
        "max_pages": 1,
    },
    "google_rss": {
        "label": "Google News RSS",
        "endpoint": "https://news.google.com/rss/search",
        "max_query_len": 100,
        "page_size": 100,
        "max_pages": 1,
    },
}

DEFAULT_TIMEOUT = 15

QUERIES = {
    "Transformation": [
        "banking digital transformation",
        "bank artificial intelligence",
    ],
    "Regulation": [
        "banking regulation",
        "banking compliance",
    ],
    "People": [
        "bank CEO appointment",
        "bank leadership",
    ],
    "Cyber & Tech": [
        "bank cybersecurity",
        "bank cyber attack",
    ],
    "Global Banks": [
        "HSBC OR JPMorgan OR Barclays OR Deutsche Bank",
        "Bank of America OR Wells Fargo OR Citi OR UBS",
    ],
}

QUOTA_MARKERS = (
    "ratelimited", "rate limit", "too many requests", "quota",
    "exhausted", "limit reached", "limit exceeded", "daily limit",
    "apikeyexhausted", "429",
)


class QuotaExhausted(RuntimeError):
    pass


def is_quota_error(message, status=None):
    if status in (402, 429):
        return True
    text = str(message or "").lower()
    return any(x in text for x in QUOTA_MARKERS)


def blank(value):
    if value is None:
        return ""
    return str(value).strip()


def fetch_newsdata(query, api_key, from_date, page=None):
    params = {
        "apikey": api_key,
        "q": query[:100],
        "language": "en",
        "size": 10,
    }

    # Latest supports a maximum 48-hour timeframe.
    if from_date:
        try:
            hours = max(
                1,
                int(
                    (
                        datetime.now(timezone.utc)
                        - datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    ).total_seconds()
                    // 3600
                ),
            )
            params["timeframe"] = min(48, hours)
        except Exception:
            params["timeframe"] = 48

    if page:
        params["page"] = page

    response = requests.get(
        "https://newsdata.io/api/1/latest",
        params=params,
        timeout=DEFAULT_TIMEOUT,
    )

    try:
        payload = response.json()
    except Exception:
        payload = {}

    if payload.get("status") != "success":
        result = payload.get("results")
        message = result.get("message") if isinstance(result, dict) else payload.get("message")
        code = result.get("code") if isinstance(result, dict) else ""
        message = message or f"HTTP {response.status_code}"
        if is_quota_error(f"{code} {message}", response.status_code):
            raise QuotaExhausted(message)
        raise RuntimeError(message)

    rows = []
    for item in payload.get("results", []) or []:
        creator = item.get("creator")
        author = ", ".join(creator) if isinstance(creator, list) else blank(creator)
        rows.append({
            "title": blank(item.get("title")),
            "description": blank(item.get("description")),
            "content": blank(item.get("content")),
            "url": blank(item.get("link")),
            "image_url": blank(item.get("image_url")),
            "source": blank(item.get("source_id")) or "NewsData",
            "published_at": blank(item.get("pubDate")),
            "author": author,
        })

    return rows, payload.get("totalResults", 0), payload.get("nextPage")


def fetch_google_rss(query, api_key=None, from_date=None, page=None):
    url = "https://news.google.com/rss/search"
    params = {
        "q": query[:100],
        "hl": "en-IN",
        "gl": "IN",
        "ceid": "IN:en",
    }

    response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    rows = []

    for item in root.findall("./channel/item"):
        title = blank(item.findtext("title"))
        link = blank(item.findtext("link"))
        description = blank(item.findtext("description"))
        pub = blank(item.findtext("pubDate"))
        source_node = item.find("source")
        source = blank(source_node.text if source_node is not None else "") or "Google News"

        rows.append({
            "title": title,
            "description": re.sub(r"<[^>]+>", " ", description).strip(),
            "content": "",
            "url": link,
            "image_url": "",
            "source": source,
            "published_at": pub,
            "author": "",
        })

    return rows, len(rows), None


# ============================================================
# DEDUP
# ============================================================

TRACKING = ("utm_", "fbclid", "gclid", "mc_cid", "mc_eid", "cmpid", "icid")
STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "at", "by", "from", "as", "is", "are", "was", "were", "be", "been",
    "after", "over", "amid", "says", "say", "new", "news", "report",
}


def canonical_url(url):
    if not url:
        return ""
    try:
        p = urlparse(url.strip())
        host = p.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        keep = [
            (k, v) for k, v in parse_qsl(p.query)
            if not any(k.lower().startswith(t) for t in TRACKING)
        ]
        return urlunparse(("", host, p.path.rstrip("/"), "", urlencode(sorted(keep)), "")).lower()
    except Exception:
        return url.strip().lower()


def normalize_title(title):
    text = re.sub(r"[^a-z0-9 ]+", " ", blank(title).lower())
    return re.sub(r"\s+", " ", text).strip()


def tokens(title):
    return frozenset(
        x for x in normalize_title(title).split()
        if x not in STOPWORDS and len(x) > 2
    )


def similarity(a, b):
    ta, tb = a["_tokens"], b["_tokens"]
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    jaccard = inter / len(ta | tb)
    containment = inter / min(len(ta), len(tb))
    ratio = SequenceMatcher(None, a["_norm"], b["_norm"]).ratio()
    return max(jaccard, 0.92 * containment, ratio)


def merge(keep, other):
    keep["providers"] = set(keep.get("providers", set())) | set(other.get("providers", set()))
    for key in ("image_url", "author", "content", "description"):
        if not keep.get(key) and other.get(key):
            keep[key] = other[key]
    if len(other.get("description", "")) > len(keep.get("description", "")):
        keep["description"] = other["description"]


def deduplicate(records, threshold=0.78):
    stats = {"by_url": 0, "by_title": 0, "by_fuzzy": 0}
    by_url, by_title, survivors = {}, {}, []

    for row in records:
        title = blank(row.get("title"))
        if not title or title.lower().startswith("[removed]"):
            continue

        row["providers"] = set(row.get("providers", set()))
        cu = canonical_url(row.get("url", ""))
        nt = normalize_title(title)

        if cu and cu in by_url:
            merge(by_url[cu], row)
            stats["by_url"] += 1
            continue
        if nt and nt in by_title:
            merge(by_title[nt], row)
            stats["by_title"] += 1
            continue

        row["_norm"] = nt
        row["_tokens"] = tokens(title)
        survivors.append(row)
        if cu:
            by_url[cu] = row
        if nt:
            by_title[nt] = row

    final = []
    for row in survivors:
        match = None
        best = 0
        for existing in final:
            score = similarity(row, existing)
            if score >= threshold and score > best:
                best = score
                match = existing
        if match:
            merge(match, row)
            stats["by_fuzzy"] += 1
        else:
            final.append(row)

    for row in final:
        row.pop("_norm", None)
        row.pop("_tokens", None)
        row["providers"] = sorted(row.get("providers", set()))

    return final, stats


# ============================================================
# INGESTION
# ============================================================

def fetch_all(api_keys, lookback_days=2, categories=None, fuzzy_threshold=0.78, max_workers=4):
    from_date = (
        datetime.now(timezone.utc) - timedelta(days=lookback_days)
    ).strftime("%Y-%m-%d")

    per_provider = {
        name: {"requests": 0, "articles": 0, "errors": 0, "quota_hits": 0}
        for name in PROVIDERS
    }
    errors = []
    raw = []

    newsdata_key = blank(api_keys.get("newsdata"))

    # ---- NewsData: four targeted requests, max 10 articles each on free tier.
    if newsdata_key:
        jobs = []
        for category, queries in QUERIES.items():
            if categories and category not in categories:
                continue
            for query in queries:
                jobs.append((category, query))

        def newsdata_job(category, query):
            return category, fetch_newsdata(query, newsdata_key, from_date)

        with __import__("concurrent.futures").futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(newsdata_job, *job) for job in jobs]
            for future in __import__("concurrent.futures").futures.as_completed(futures):
                category, result = None, None
                try:
                    category, result = future.result()
                    rows, _, _ = result
                    per_provider["newsdata"]["requests"] += 1
                    per_provider["newsdata"]["articles"] += len(rows)
                    for row in rows:
                        row["provider_category"] = category
                        row["providers"] = {"newsdata"}
                        raw.append(row)
                except QuotaExhausted as exc:
                    per_provider["newsdata"]["requests"] += 1
                    per_provider["newsdata"]["quota_hits"] += 1
                    errors.append(f"NewsData.io quota: {exc}")
                except Exception as exc:
                    per_provider["newsdata"]["requests"] += 1
                    per_provider["newsdata"]["errors"] += 1
                    errors.append(f"NewsData.io: {exc}")

    # ---- Google News RSS: free fallback/source. It runs even when NewsData
    # fails, so the dashboard is not blank because of an API-key problem.
    jobs = []
    for category, queries in QUERIES.items():
        if categories and category not in categories:
            continue
        for query in queries:
            jobs.append((category, query))

    def rss_job(category, query):
        return category, fetch_google_rss(query)

    with __import__("concurrent.futures").futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(rss_job, *job) for job in jobs]
        for future in __import__("concurrent.futures").futures.as_completed(futures):
            try:
                category, result = future.result()
                rows, _, _ = result
                per_provider["google_rss"]["requests"] += 1
                per_provider["google_rss"]["articles"] += len(rows)
                for row in rows:
                    row["provider_category"] = category
                    row["providers"] = {"google_rss"}
                    raw.append(row)
            except Exception as exc:
                per_provider["google_rss"]["requests"] += 1
                per_provider["google_rss"]["errors"] += 1
                errors.append(f"Google News RSS: {exc}")

    unique, dedup = deduplicate(raw, threshold=fuzzy_threshold)

    return unique, errors, {
        "per_provider": per_provider,
        "raw": len(raw),
        "unique": len(unique),
        "dedup": dedup,
    }
