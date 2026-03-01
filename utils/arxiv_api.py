import datetime as dt
import html
import re
from typing import Dict, List

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
            }
        )
    return entries
