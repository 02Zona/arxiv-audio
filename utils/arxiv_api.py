import datetime as dt
import html
import re
from typing import Dict, List
from urllib.request import urlopen

import feedparser

DEFAULT_CATEGORIES = [
    "cond-mat.str-el",
    "cond-mat.dis-nn",
    "quant-ph",
    "cond-mat.stat-mech",
    "cond-mat.supr-con",
]


def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _date_range_token(date_text: str) -> str:
    date_obj = dt.datetime.strptime(date_text, "%Y-%m-%d")
    start = date_obj.strftime("%Y%m%d0000")
    end = date_obj.strftime("%Y%m%d2359")
    return f"[{start}+TO+{end}]"


def _extract_doi(entry) -> str:
    # arXiv feed often stores DOI in arxiv_doi or doi
    for attr in ("arxiv_doi", "doi"):
        v = getattr(entry, attr, "") or getattr(entry, attr.upper(), "")
        if v:
            return strip_html(str(v))
    # Sometimes DOI appears in links/aux; ignore for now
    return ""


def _extract_categories(entry, default_cat: str) -> List[str]:
    cats = set()
    if default_cat:
        cats.add(default_cat)
    tags = getattr(entry, "tags", []) or []
    for t in tags:
        term = getattr(t, "term", "") or getattr(t, "label", "")
        term = strip_html(term)
        if term:
            cats.add(term)
    return sorted(cats)


def _bare_id(arxiv_id: str) -> str:
    arxiv_id = (arxiv_id or "").strip()
    arxiv_id = arxiv_id.split("/")[-1]
    return re.sub(r"v\d+$", "", arxiv_id)


def _entry_to_item(entry, default_cat: str = "") -> Dict[str, str]:
    item_id = getattr(entry, "id", "") or getattr(entry, "link", "")
    authors = ""
    if hasattr(entry, "authors"):
        authors = ", ".join(strip_html(a.get("name", "")) for a in entry.authors)
    elif hasattr(entry, "author"):
        authors = strip_html(entry.author)

    return {
        "id": item_id,
        "title": strip_html(getattr(entry, "title", "")),
        "summary": strip_html(getattr(entry, "summary", "")),
        "link": item_id,
        "authors": authors,
        "published": getattr(entry, "published", ""),
        "doi": _extract_doi(entry),
        "categories": _extract_categories(entry, default_cat),
    }


def _listing_ids_for_category_date(category: str, date_text: str) -> List[str]:
    date_obj = dt.datetime.strptime(date_text, "%Y-%m-%d")
    url = f"https://arxiv.org/list/{category}/pastweek?show=2000"
    with urlopen(url, timeout=20) as resp:
        page = resp.read().decode("utf-8", errors="replace")

    # New browse pages use short date headings like "Fri, 27 Feb 2026".
    # Older pages may contain "new listings for Friday, 27 February 2026".
    short_label = date_obj.strftime("%a, %d %b %Y")
    h3_match = re.search(rf"<h3>\s*{re.escape(short_label)}[^<]*</h3>", page, flags=re.IGNORECASE)
    if h3_match:
        tail = page[h3_match.end() :]
    else:
        full_label = (
            f"new listings for {date_obj.strftime('%A')}, "
            f"{date_obj.day} {date_obj.strftime('%B')} {date_obj.year}"
        )
        full_m = re.search(re.escape(full_label), page, flags=re.IGNORECASE)
        if not full_m:
            return []
        tail = page[full_m.end() :]

    next_h3 = re.search(r"<h3>\s*[A-Za-z]{3},\s+\d{2}\s+[A-Za-z]{3}\s+\d{4}", tail)
    block = tail[: next_h3.start()] if next_h3 else tail
    ids = re.findall(r'href\s*=\s*"/abs/([^"?#]+)"', block)
    # Keep original order, dedupe locally.
    seen = set()
    ordered = []
    for arxiv_id in ids:
        bare = _bare_id(arxiv_id)
        if bare and bare not in seen:
            seen.add(bare)
            ordered.append(bare)
    return ordered


def _listing_entries_for_category_date(category: str, date_text: str) -> List[Dict[str, str]]:
    date_obj = dt.datetime.strptime(date_text, "%Y-%m-%d")
    url = f"https://arxiv.org/list/{category}/pastweek?show=2000"
    with urlopen(url, timeout=20) as resp:
        page = resp.read().decode("utf-8", errors="replace")

    short_label = date_obj.strftime("%a, %d %b %Y")
    h3_match = re.search(rf"<h3>\s*{re.escape(short_label)}[^<]*</h3>", page, flags=re.IGNORECASE)
    if h3_match:
        tail = page[h3_match.end() :]
    else:
        full_label = (
            f"new listings for {date_obj.strftime('%A')}, "
            f"{date_obj.day} {date_obj.strftime('%B')} {date_obj.year}"
        )
        full_m = re.search(re.escape(full_label), page, flags=re.IGNORECASE)
        if not full_m:
            return []
        tail = page[full_m.end() :]

    next_h3 = re.search(r"<h3>\s*[A-Za-z]{3},\s+\d{2}\s+[A-Za-z]{3}\s+\d{4}", tail)
    block = tail[: next_h3.start()] if next_h3 else tail

    entries: List[Dict[str, str]] = []
    pairs = re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", block, flags=re.DOTALL | re.IGNORECASE)
    for dt_html, dd_html in pairs:
        id_m = re.search(r'href\s*=\s*"/abs/([^"?#]+)"', dt_html, flags=re.IGNORECASE)
        if not id_m:
            continue
        arxiv_id = _bare_id(id_m.group(1))
        link = f"http://arxiv.org/abs/{arxiv_id}"

        title_m = re.search(
            r"list-title[^>]*>.*?Title:\s*</span>\s*(.*?)\s*</div>",
            dd_html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        authors_m = re.search(
            r"list-authors[^>]*>.*?Authors?:\s*</span>\s*(.*?)\s*</div>",
            dd_html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        abs_m = re.search(r"<p[^>]*class=\"mathjax\"[^>]*>(.*?)</p>", dd_html, flags=re.DOTALL | re.IGNORECASE)
        if not abs_m:
            abs_m = re.search(r"<p[^>]*>(.*?)</p>", dd_html, flags=re.DOTALL | re.IGNORECASE)

        doi_m = re.search(r"https?://doi\.org/([^\"<\s]+)", dd_html, flags=re.IGNORECASE)
        doi = doi_m.group(1).strip() if doi_m else ""

        entries.append(
            {
                "id": arxiv_id,
                "title": strip_html(title_m.group(1) if title_m else ""),
                "summary": strip_html(abs_m.group(1) if abs_m else ""),
                "link": link,
                "authors": strip_html(authors_m.group(1) if authors_m else ""),
                "published": "",
                "doi": strip_html(doi),
                "categories": [category],
            }
        )

    return entries


def fetch_entries_by_date(date_text: str, limit: int, categories: List[str]) -> List[Dict[str, str]]:
    pool: Dict[str, Dict[str, str]] = {}

    for category in categories:
        query = f"cat:{category} AND submittedDate:{_date_range_token(date_text)}"
        query = query.replace(" ", "+")
        url = (
            "https://export.arxiv.org/api/query"
            f"?search_query={query}&start=0&max_results={limit}"
            "&sortBy=submittedDate&sortOrder=descending"
        )
        feed = feedparser.parse(url)
        for entry in feed.entries:
            item_id = getattr(entry, "id", "") or getattr(entry, "link", "")
            if not item_id or item_id in pool:
                continue

            authors = ""
            if hasattr(entry, "authors"):
                authors = ", ".join(strip_html(a.get("name", "")) for a in entry.authors)
            elif hasattr(entry, "author"):
                authors = strip_html(entry.author)

            pool[item_id] = {
                "title": strip_html(getattr(entry, "title", "")),
                "summary": strip_html(getattr(entry, "summary", "")),
                "link": item_id,
                "authors": authors,
                "published": getattr(entry, "published", ""),
                "doi": _extract_doi(entry),
                "categories": _extract_categories(entry, category),
            }

    ordered = sorted(pool.values(), key=lambda x: x["published"], reverse=True)[:limit]

    entries: List[Dict[str, str]] = []
    for idx, item in enumerate(ordered, 1):
        entries.append(
            {
                "index": idx,
                "title": item["title"],
                "summary": item["summary"],
                "link": item["link"],
                "authors": item["authors"],
                "doi": item["doi"],
                "categories": item["categories"],
            }
        )
    return entries


def fetch_entries_by_listing_date(date_text: str, limit: int, categories: List[str]) -> List[Dict[str, str]]:
    pooled: List[Dict[str, str]] = []
    seen = set()
    for category in categories:
        for item in _listing_entries_for_category_date(category, date_text):
            arxiv_id = item.get("id", "")
            if not arxiv_id or arxiv_id in seen:
                continue
            seen.add(arxiv_id)
            pooled.append(item)
            if len(pooled) >= limit:
                break
        if len(pooled) >= limit:
            break

    if not pooled:
        return []

    entries: List[Dict[str, str]] = []
    for idx, item in enumerate(pooled, 1):
        entries.append(
            {
                "index": idx,
                "title": item["title"],
                "summary": item["summary"],
                "link": item["link"],
                "authors": item["authors"],
                "doi": item["doi"],
                "categories": item["categories"],
            }
        )
    return entries[:limit]
