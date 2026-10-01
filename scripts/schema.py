"""Shared event schema and helpers used by every fetcher."""
import hashlib
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Categories every fetcher should map its events into. Keep this list short
# and broad -- the frontend filters on these, not on freeform tags.
CATEGORIES = [
    "food-drink",
    "arts-culture",
    "music",
    "wellness",
    "market",
    "workshop-class",
    "community",
    "family-kids",
    "other",
]


def make_event(
    *,
    title,
    start,  # ISO 8601 string, e.g. "2026-09-12T09:00:00-04:00"
    source,  # short slug, e.g. "4roots-farm"
    url,
    end=None,
    location=None,
    description=None,
    price=None,
    categories=None,
    image=None,
):
    """Build a normalized event dict and a stable id (hash of source+title+start)."""
    categories = categories or ["other"]
    raw_id = f"{source}|{title}|{start}"
    event_id = hashlib.sha1(raw_id.encode("utf-8")).hexdigest()[:12]
    return {
        "id": event_id,
        "title": title.strip(),
        "start": start,
        "end": end,
        "location": location,
        "description": description,
        "price": price,
        "categories": categories,
        "url": url,
        "image": image,
        "source": source,
    }


def write_source_json(source_slug, events):
    """Each fetcher writes its own file; merge.py combines them later."""
    out_path = DATA_DIR / "sources" / f"{source_slug}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(events, indent=2, ensure_ascii=False))
    print(f"[{source_slug}] wrote {len(events)} events -> {out_path}")
