"""Fetch events from 4Roots Farm's public Events Calendar (Tribe Events) API."""
import html
import re
import sys

import requests
from dateutil import parser as dateparser

from schema import make_event, write_source_json

SOURCE = "4roots-farm"
API_URL = "https://4rootsfarm.org/wp-json/tribe/events/v1/events"

CATEGORY_MAP = {
    "classes": "workshop-class",
    "special-events": "community",
    "farmers-market": "market",
    "food-as-medicine": "food-drink",
}


def map_categories(tribe_categories):
    mapped = set()
    for cat in tribe_categories or []:
        slug = cat.get("slug", "")
        mapped.add(CATEGORY_MAP.get(slug, "other"))
    return sorted(mapped) or ["other"]


def strip_html(html_text):
    if not html_text:
        return None
    text = re.sub(r"<[^>]+>", " ", html_text)
    text = re.sub(r"\s+", " ", text).strip()
    text = html.unescape(text)
    return text or None


def to_iso(date_str, tz_name):
    if not date_str:
        return None
    dt = dateparser.parse(date_str)
    from zoneinfo import ZoneInfo

    try:
        dt = dt.replace(tzinfo=ZoneInfo(tz_name or "America/New_York"))
    except Exception:
        dt = dt.replace(tzinfo=ZoneInfo("America/New_York"))
    return dt.isoformat()


def fetch_all_events():
    events = []
    page = 1
    while True:
        resp = requests.get(
            API_URL,
            params={"per_page": 50, "page": page, "start_date": "now"},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        events.extend(data.get("events", []))
        if page >= data.get("total_pages", 1):
            break
        page += 1
    return events


def main():
    raw_events = fetch_all_events()
    out = []
    for ev in raw_events:
        tz = ev.get("timezone") or "America/New_York"
        venue = ev.get("venue") or {}
        location_parts = [venue.get("venue"), venue.get("address"), venue.get("city")]
        location = ", ".join(html.unescape(p) for p in location_parts if p)

        out.append(
            make_event(
                title=html.unescape(ev["title"]),
                start=to_iso(ev.get("start_date"), tz),
                end=to_iso(ev.get("end_date"), tz),
                source=SOURCE,
                url=ev.get("url"),
                location=location or None,
                description=strip_html(ev.get("description")),
                price=ev.get("cost") or None,
                categories=map_categories(ev.get("categories")),
                image=(ev.get("image") or {}).get("url"),
            )
        )
    write_source_json(SOURCE, out)


if __name__ == "__main__":
    sys.exit(main())
