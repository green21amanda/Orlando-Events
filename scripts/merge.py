"""Combine every source's events into the single data/events.json the
frontend reads. Run this after all fetch_*.py scripts (see build.py)."""
import json
import sys
from datetime import date, datetime, timedelta

from dateutil import parser as dateparser

from schema import DATA_DIR

SOURCES_DIR = DATA_DIR / "sources"
MANUAL_FILE = DATA_DIR / "manual-events.json"
OUTPUT_FILE = DATA_DIR / "events.json"

# Don't show events further out than this -- keeps the file small and the
# calendar focused on things actually worth planning for.
HORIZON_DAYS = 120


def parse_start(event):
    return dateparser.parse(event["start"])


def sort_key(event):
    """Comparable regardless of whether the source gave us a timezone-aware
    or naive datetime (or just a bare date) -- exact cross-timezone ordering
    doesn't matter here since every source is a local Orlando event."""
    dt = parse_start(event)
    return dt.replace(tzinfo=None) if isinstance(dt, datetime) else dt


def is_upcoming(event, today):
    try:
        start = parse_start(event)
    except (ValueError, TypeError):
        return False
    start_date = start.date() if isinstance(start, datetime) else start
    return today <= start_date <= today + timedelta(days=HORIZON_DAYS)


def load_all_events():
    manual = json.loads(MANUAL_FILE.read_text()) if MANUAL_FILE.exists() else []
    auto = []
    if SOURCES_DIR.exists():
        for path in sorted(SOURCES_DIR.glob("*.json")):
            auto.extend(json.loads(path.read_text()))
    return manual, auto


def event_date_key(event):
    return (event["source"], parse_start(event).date())


def main():
    today = date.today()
    manual, auto = load_all_events()

    # A hand-entered event (read from a flyer/screenshot) beats an automated
    # one for the same source and day, e.g. the same pop-up seen both ways.
    manual_keys = {event_date_key(ev) for ev in manual}
    auto = [ev for ev in auto if event_date_key(ev) not in manual_keys]
    all_events = manual + auto

    seen_ids = set()
    deduped = []
    for ev in all_events:
        if ev["id"] in seen_ids:
            continue
        seen_ids.add(ev["id"])
        deduped.append(ev)

    upcoming = [ev for ev in deduped if is_upcoming(ev, today)]
    upcoming.sort(key=sort_key)

    OUTPUT_FILE.write_text(json.dumps(upcoming, indent=2, ensure_ascii=False))
    print(f"merged {len(upcoming)} upcoming events (of {len(deduped)} total) -> {OUTPUT_FILE}")

    by_source = {}
    for ev in upcoming:
        by_source[ev["source"]] = by_source.get(ev["source"], 0) + 1
    for source, count in sorted(by_source.items()):
        print(f"  {source}: {count}")


if __name__ == "__main__":
    sys.exit(main())
