#!/usr/bin/env python3
import argparse
import datetime
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.arxiv_api import DEFAULT_CATEGORIES, fetch_entries_by_date

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10, help="max papers")
    ap.add_argument("--date", type=str, default="", help="override date YYYY-MM-DD")
    ap.add_argument(
        "--categories",
        type=str,
        default=",".join(DEFAULT_CATEGORIES),
        help="comma-separated arXiv categories",
    )
    args = ap.parse_args()

    today = args.date.strip() or datetime.datetime.now().strftime("%Y-%m-%d")
    categories = [c.strip() for c in args.categories.split(",") if c.strip()]
    out_dir = Path("episodes")
    out_dir.mkdir(parents=True, exist_ok=True)

    entries = fetch_entries_by_date(today, args.n, categories)
    if not entries:
        print("No entries found. Nothing to write.")
        return

    metadata = []
    for e in entries:
        i = int(e["index"])
        lines = []
        lines.append(f"Paper {i}. {e['title']}.")
        if e["authors"]:
            lines.append(f"Authors: {e['authors']}.")
        lines.append(f"Abstract: {e['summary']}")
        if e["link"]:
            lines.append(f"Link: {e['link']}")
        lines.append("")

        out = "\n".join(lines).strip() + "\n"
        filename = out_dir / f"{today}-{i:02d}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"Wrote {filename}")
        metadata.append(
            {
                "index": i,
                "date": today,
                "title": e["title"],
                "authors": e["authors"],
                "summary": e["summary"],
                "link": e["link"],
                "txt_path": str(filename),
            }
        )

    meta_path = out_dir / f"{today}.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"Wrote {meta_path}")

if __name__ == "__main__":
    main()
