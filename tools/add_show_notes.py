#!/usr/bin/env python3
import re
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
FEED_PATH = ROOT / "feed.xml"
EP_DIR = ROOT / "episodes"

NAMESPACES = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"}


def _arxiv_id_from_link(link: str) -> str:
    # https://arxiv.org/abs/1234.5678v1 -> 1234.5678v1
    if not link:
        return ""
    return link.rstrip("/").split("/")[-1]


def build_notes(entry: dict, limit: int = 1400) -> str:
    title = entry.get("title", "").strip()
    authors = entry.get("authors", "").strip()
    cats = entry.get("categories") or []
    doi = (entry.get("doi") or "").strip()
    link = (entry.get("link") or "").strip()
    summary = entry.get("summary") or ""

    notes = []
    if title:
        notes.append(title)
    if authors:
        notes.append(f"Authors: {authors}")
    if cats:
        notes.append(f"Categories: {', '.join(cats)}")
    if doi:
        notes.append(f"DOI: {doi}")
    if link:
        notes.append(f"Link: {link}")

    if len(summary) > limit:
        summary = summary[:limit].rstrip() + "…"
    notes.append("Abstract:")
    notes.append(summary)

    return "\n".join(notes).strip()


def load_json(date_text: str):
    p = EP_DIR / f"{date_text}.json"
    if not p.exists():
        return {}
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {int(e["index"]): e for e in data}


def add_if_missing(parent, tag, text):
    existing = parent.find(tag, NAMESPACES) if ":" in tag else parent.find(tag)
    if existing is None:
        existing = ET.SubElement(parent, tag)
    if not (existing.text or "").strip():
        existing.text = text


def _set_or_replace_title(title_el, replacement: str):
    old_title = (title_el.text or "").strip()
    if not old_title:
        title_el.text = replacement
        return
    # Replace the last segment after the last "·"
    parts = [p.strip() for p in old_title.split("·")]
    if len(parts) >= 2:
        parts[-1] = replacement.strip()
        title_el.text = " · ".join(parts)
    else:
        title_el.text = replacement.strip()


def main():
    ET.register_namespace("itunes", NAMESPACES["itunes"])

    tree = ET.parse(FEED_PATH)
    root = tree.getroot()
    channel = root.find("channel")
    if channel is None:
        raise SystemExit("No <channel> found in feed.xml")

    meta_cache = {}

    for item in channel.findall("item"):
        guid_el = item.find("guid")
        title_el = item.find("title")

        if guid_el is None or not (guid_el.text or "").strip() or title_el is None:
            continue

        guid = guid_el.text.strip()
        m = re.match(r"(\d{4}-\d{2}-\d{2})-(\d+)$", guid)
        if not m:
            continue

        date_text, idx_s = m.group(1), m.group(2)
        idx = int(idx_s)

        if date_text not in meta_cache:
            meta_cache[date_text] = load_json(date_text)
        entry = meta_cache[date_text].get(idx)
        if not entry:
            continue

        notes = build_notes(entry)

        add_if_missing(item, "description", notes)
        add_if_missing(item, "itunes:summary", notes)

        # Replace title's last segment with DOI (or arXiv ID fallback)
        replacement = entry.get("doi") or _arxiv_id_from_link(entry.get("link", ""))
        replacement = replacement.strip()
        if replacement:
            _set_or_replace_title(title_el, replacement)

    tree.write(FEED_PATH, encoding="utf-8", xml_declaration=True)
    print("Updated feed.xml: show notes + title suffix replaced with DOI/arXivID")


if __name__ == "__main__":
    main()
