#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.rss_feed import parse_afinfo_duration, upsert_date_items


def _afinfo_duration(path: Path) -> str:
    out = subprocess.check_output(["afinfo", str(path)], text=True, stderr=subprocess.STDOUT)
    return parse_afinfo_duration(out)


def _load_metadata(path: Path):
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--base-url", default="https://02Zona.github.io/arxiv-audio")
    ap.add_argument("--tz-offset", default="-0800")
    ap.add_argument("--feed-path", default="feed.xml")
    ap.add_argument("--notice-title", default="")
    ap.add_argument("--notice-description", default="Daily arXiv audio brief.")
    args = ap.parse_args()

    date_text = args.date
    feed_path = ROOT / args.feed_path
    ep_dir = ROOT / "episodes"
    meta = _load_metadata(ep_dir / f"{date_text}.json")

    items = []
    for entry in meta:
        idx = int(entry["index"])
        stem = f"{date_text}-{idx:02d}"
        m4a = ep_dir / f"{stem}.m4a"
        if not m4a.exists():
            continue
        title_suffix = entry.get("title", "").strip() or "arXiv brief"
        items.append(
            {
                "title": f"{date_text} · cond-mat/quant-ph 合集 · #{idx:02d} · {title_suffix}",
                "guid": stem,
                "enclosure_url": f"{args.base_url}/episodes/{stem}.m4a",
                "length": os.path.getsize(m4a),
                "duration": _afinfo_duration(m4a),
                "description": "Daily arXiv audio brief.",
            }
        )

    if not items and args.notice_title:
        stem = f"{date_text}-01"
        m4a = ep_dir / f"{stem}.m4a"
        if not m4a.exists():
            raise SystemExit(f"Notice audio missing: {m4a}")
        items.append(
            {
                "title": args.notice_title,
                "guid": stem,
                "enclosure_url": f"{args.base_url}/episodes/{stem}.m4a",
                "length": os.path.getsize(m4a),
                "duration": _afinfo_duration(m4a),
                "description": args.notice_description,
            }
        )

    if not items:
        print("No items to upsert.")
        return

    upsert_date_items(feed_path, date_text, items, args.tz_offset)
    print(f"Updated {feed_path} with {len(items)} items for {date_text}")


if __name__ == "__main__":
    main()
