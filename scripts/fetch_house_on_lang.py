"""Fetch events from The House on Lang's Wix Events widget.

Wix server-renders the widget's data into a <script id="wix-warmup-data">
JSON blob, so we can pull structured events straight out of the plain HTML
without running a browser. This only returns the widget's initial page of
upcoming events (no "Load More" pagination), which in practice covers
several weeks out for a venue like this.
"""
import json
import re
import sys

import requests

from schema import make_event, write_source_json

SOURCE = "house-on-lang"
PAGE_URL = "https://www.houseonlang.com/05-a-events"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; OrlandoEventsBot/1.0)"}

# Best-effort keyword -> category mapping since this source has no native
# category taxonomy.
KEYWORD_CATEGORIES = [
    (("yoga", "sound bowl", "healing", "wellness", "meditat"), "wellness"),
    (("wine", "bake", "cooking", "coffee", "cocktail", "mocktail", "tasting"), "food-drink"),
    (("market",), "market"),
    (
        (
            "workshop",
            "class",
            "painting",
            "collage",
            "candle making",
            "dying",
            "print",
            "art",
            "craft",
        ),
        "workshop-class",
    ),
    (("mahjong", "game night", "tarot", "book club", "club"), "community"),
]


def guess_categories(title, description):
    text = f"{title} {description or ''}".lower()
    matched = set()
    for keywords, category in KEYWORD_CATEGORIES:
        if any(kw in text for kw in keywords):
            matched.add(category)
    return sorted(matched) or ["other"]


def find_events_list(node):
    """Recursively search the warmup-data tree for the Wix Events widget's
    events array, rather than hardcoding the widget component id (which can
    change if the page is rebuilt in the Wix editor)."""
    if isinstance(node, dict):
        events = node.get("events")
        if isinstance(events, dict) and isinstance(events.get("events"), list):
            return events["events"]
        for value in node.values():
            found = find_events_list(value)
            if found is not None:
                return found
    elif isinstance(node, list):
        for item in node:
            found = find_events_list(item)
            if found is not None:
                return found
    return None


def fetch_warmup_data():
    resp = requests.get(PAGE_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    match = re.search(
        r'<script[^>]*id="wix-warmup-data"[^>]*>(.*?)</script>', resp.text, re.S
    )
    if not match:
        raise RuntimeError("wix-warmup-data script not found -- page structure may have changed")
    return json.loads(match.group(1))


def main():
    warmup = fetch_warmup_data()
    raw_events = find_events_list(warmup)
    if raw_events is None:
        raise RuntimeError("could not locate events list in wix-warmup-data")

    out = []
    for ev in raw_events:
        scheduling = (ev.get("scheduling") or {}).get("config") or {}
        location = ev.get("location") or {}
        title = ev.get("title", "").strip()
        description = (ev.get("description") or "").strip() or None

        out.append(
            make_event(
                title=title,
                start=scheduling.get("startDate"),
                end=scheduling.get("endDate"),
                source=SOURCE,
                url=f"https://www.houseonlang.com/event-details/{ev['slug']}",
                location=location.get("name") or location.get("address"),
                description=description,
                price=None,
                categories=guess_categories(title, description),
                image=(ev.get("mainImage") or {}).get("url"),
            )
        )
    write_source_json(SOURCE, out)


if __name__ == "__main__":
    sys.exit(main())
