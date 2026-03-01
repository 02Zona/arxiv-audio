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


def main() -> None:
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

    date_text = args.date.strip() or datetime.datetime.now().strftime("%Y-%m-%d")
    categories = [c.strip() for c in args.categories.split(",") if c.strip()]
    out_dir = Path("episodes")
    out_dir.mkdir(parents=True, exist_ok=True)

    entries = fetch_entries_by_date(date_text, args.n, categories)
    if not entries:
        print("No entries found. Nothing to write.")
        return

    metadata = []
    for entry in entries:
        idx = int(entry["index"])
        lines = [
            f"Paper {idx}. {entry['title']}.",
        ]
        if entry["authors"]:
            lines.append(f"Authors: {entry['authors']}.")
        lines.append(f"Abstract: {entry['summary']}")
        if entry["link"]:
            lines.append(f"Link: {entry['link']}")
        lines.append("")

        txt_path = out_dir / f"{date_text}-{idx:02d}.txt"
        txt_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
        print(f"Wrote {txt_path}")

        metadata.append(
            {
                "index": idx,
                "date": date_text,
                "title": entry.get("title", ""),
                "authors": entry.get("authors", ""),
                "summary": entry.get("summary", ""),
                "link": entry.get("link", ""),
                "doi": entry.get("doi", ""),
                "categories": entry.get("categories", []),
                "txt_path": str(txt_path),
            }
        )

    meta_path = out_dir / f"{date_text}.json"
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {meta_path}")


if __name__ == "__main__":
    main()
