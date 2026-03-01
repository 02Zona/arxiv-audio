import datetime as dt
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List

ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ET.register_namespace("itunes", ITUNES_NS)


def _pubdate_for(date_text: str, tz_offset: str, time_hms: str = "09:00:00") -> str:
    date_obj = dt.datetime.strptime(date_text, "%Y-%m-%d")
    weekday = date_obj.strftime("%a")
    month = date_obj.strftime("%b")
    return f"{weekday}, {date_obj.day:02d} {month} {date_obj.year} {time_hms} {tz_offset}"


def _duration_hhmmss(seconds_float: float) -> str:
    seconds = int(round(seconds_float))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def parse_afinfo_duration(afinfo_output: str) -> str:
    m = re.search(r"estimated duration:\s*([0-9.]+)\s*sec", afinfo_output)
    if not m:
        return "00:00:00"
    return _duration_hhmmss(float(m.group(1)))


def upsert_date_items(feed_path: Path, date_text: str, items: List[Dict[str, str]], tz_offset: str) -> None:
    tree = ET.parse(feed_path)
    root = tree.getroot()
    channel = root.find("channel")
    if channel is None:
        raise RuntimeError("feed.xml missing <channel>")

    old_items = channel.findall("item")
    for old in old_items:
        guid_el = old.find("guid")
        guid = (guid_el.text or "").strip() if guid_el is not None else ""
        if guid.startswith(f"{date_text}-"):
            channel.remove(old)

    insert_at = len(channel)
    for idx, child in enumerate(list(channel)):
        if child.tag == "item":
            insert_at = idx
            break

    for item in items:
        node = ET.Element("item")
        ET.SubElement(node, "title").text = item["title"]
        ET.SubElement(node, "description").text = item.get("description", "Daily arXiv audio brief.")
        ET.SubElement(node, "pubDate").text = _pubdate_for(date_text, tz_offset)
        ET.SubElement(node, "guid").text = item["guid"]

        enclosure = ET.SubElement(node, "enclosure")
        enclosure.set("url", item["enclosure_url"])
        enclosure.set("length", str(item["length"]))
        enclosure.set("type", "audio/mp4")

        ET.SubElement(node, f"{{{ITUNES_NS}}}duration").text = item["duration"]
        channel.insert(insert_at, node)
        insert_at += 1

    ET.indent(tree, space="  ")
    tree.write(feed_path, encoding="utf-8", xml_declaration=True)
