#!/usr/bin/env python3
import re, html, datetime, argparse
from pathlib import Path
import feedparser

def strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10, help="max papers")
    ap.add_argument("--date", type=str, default="", help="override date YYYY-MM-DD")
    args = ap.parse_args()

    url = "https://rss.arxiv.org/rss/cond-mat.str-el+cond-mat.dis-nn+quant-ph+cond-mat.stat-mech+cond-mat.supr-con"
    feed = feedparser.parse(url)

    today = args.date.strip() or datetime.datetime.now().strftime("%Y-%m-%d")
    out_dir = Path("episodes")
    out_dir.mkdir(parents=True, exist_ok=True)

    entries = feed.entries[:args.n]
    if not entries:
        print("No entries found. Nothing to write.")
        return

    for i, e in enumerate(entries, 1):
        title = strip_html(getattr(e, "title", ""))
        link = getattr(e, "link", "")
        summary = strip_html(getattr(e, "summary", ""))

        authors = ""
        if hasattr(e, "author"):
            authors = strip_html(e.author)
        elif hasattr(e, "authors"):
            authors = ", ".join(strip_html(a.get("name", "")) for a in e.authors)

        lines = []
        lines.append(f"Paper {i}. {title}.")
        if authors:
            lines.append(f"Authors: {authors}.")
        lines.append(f"Abstract: {summary}")
        if link:
            lines.append(f"Link: {link}")
        lines.append("")

        out = "\n".join(lines).strip() + "\n"
        filename = out_dir / f"{today}-{i:02d}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"Wrote {filename}")

if __name__ == "__main__":
    main()
