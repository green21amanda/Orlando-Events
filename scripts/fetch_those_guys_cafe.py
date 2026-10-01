"""Fetch Those Guys Cafe's weekly pop-up schedule.

They don't run a real events calendar -- their schedule lives entirely in
Instagram captions ("Thurs, Sept 3rd / @parkwaycrossings"), and their
Squarespace homepage embeds the last ~3 Instagram posts' images with the
caption text in a <noscript><img alt="..."> fallback (server-rendered, no
JS needed to read it).

KNOWN LIMITATIONS (best-effort source, not authoritative):
  - Squarespace truncates the alt text around ~250 chars, so a post that
    lists several days can get cut off mid-caption -- later days in that
    post are silently dropped rather than guessed at.
  - No event times are given, only a date and a rough location (an
    Instagram handle, not an address) -- events are emitted as all-day.
  - Only the ~3 most recent posts are available at all, so this covers at
    most the current + upcoming week, not a full calendar.
"""
import re
import sys
from datetime import date

import requests
from bs4 import BeautifulSoup

from schema import make_event, write_source_json

SOURCE = "those-guys-cafe"
PAGE_URL = "https://www.thoseguyscafe.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; OrlandoEventsBot/1.0)"}

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}

DATE_LINE_RE = re.compile(
    r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\w*,?\s+"
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\w*\s+"
    r"(\d{1,2})(?:st|nd|rd|th)?",
    re.IGNORECASE,
)
HANDLE_RE = re.compile(r"@([\w.]+)")


def resolve_year(month, day, today=None):
    """Captions never include a year. Assume the nearest occurrence of
    month/day relative to today (handles the Dec -> Jan rollover)."""
    today = today or date.today()
    year = today.year
    candidate = date(year, month, day)
    if (candidate - today).days < -60:
        candidate = date(year + 1, month, day)
    return candidate


def parse_caption(caption):
    """Yield (event_date, handle) for each complete date+location pair found
    before the caption gets cut off."""
    html_unescaped = caption.replace("&bull;", "•").replace("&rsquo;", "'")
    lines = [l.strip() for l in html_unescaped.split("\n") if l.strip()]

    i = 0
    while i < len(lines):
        m = DATE_LINE_RE.search(lines[i])
        if not m:
            i += 1
            continue
        month = MONTHS[m.group(2).lower()]
        day = int(m.group(3))
        # Look ahead a couple of lines for the first @handle (the location).
        handle = None
        for j in range(i + 1, min(i + 3, len(lines))):
            hm = HANDLE_RE.search(lines[j])
            if hm:
                handle = hm.group(1)
                break
        if handle:
            yield resolve_year(month, day), handle
        i += 1


def fetch_captions():
    resp = requests.get(PAGE_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    return [img.get("alt", "") for img in soup.select("noscript img") if img.get("alt")]


def main():
    out = []
    for caption in fetch_captions():
        for event_date, handle in parse_caption(caption):
            out.append(
                make_event(
                    title=f"Those Guys Cafe Pop-Up @{handle}",
                    start=event_date.isoformat(),
                    end=None,
                    source=SOURCE,
                    url=f"https://instagram.com/{handle}",
                    location=f"@{handle} (see Instagram for exact address)",
                    description=(
                        "Time not listed -- check Those Guys Cafe's Instagram "
                        "for exact hours and any last-minute changes."
                    ),
                    price=None,
                    categories=["food-drink"],
                    image=None,
                )
            )
    write_source_json(SOURCE, out)


if __name__ == "__main__":
    sys.exit(main())
