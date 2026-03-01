#!/usr/bin/env python3
import re, html, datetime, argparse
import feedparser

def strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10, help="max papers")
    args = ap.parse_args()

    url = "https://rss.arxiv.org/rss/cond-mat.str-el+cond-mat.dis-nn+quant-ph+cond-mat.stat-mech+cond-mat.supr-con"
    feed = feedparser.parse(url)

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    lines = []
    lines.append(f"Good morning. This is your arXiv brief for {today}.")
    lines.append("Categories: str-el, dis-nn, quant-ph, stat-mech, supr-con.")
    lines.append(f"I will read {min(args.n, len(feed.entries))} items.")
    lines.append("")

    for i, e in enumerate(feed.entries[:args.n], 1):
        title = strip_html(getattr(e, "title", ""))
        link = getattr(e, "link", "")
        summary = strip_html(getattr(e, "summary", ""))

        authors = ""
        if hasattr(e, "author"):
            authors = strip_html(e.author)
        elif hasattr(e, "authors"):
            authors = ", ".join(strip_html(a.get("name","")) for a in e.authors)

        lines.append(f"Paper {i}. {title}.")
        if authors:
            lines.append(f"Authors: {authors}.")
        lines.append(f"Abstract: {summary}")
        if link:
            lines.append(f"Link: {link}")
        lines.append("")

    out = "\n".join(lines).strip() + "\n"
    with open("episode.txt", "w", encoding="utf-8") as f:
        f.write(out)
    print("Wrote episode.txt")

if __name__ == "__main__":
    main()
