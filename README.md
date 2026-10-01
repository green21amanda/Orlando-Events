# Orlando Events

A static calendar site of upcoming Orlando events, aggregated daily from a
handful of sources and filterable by category.

## How it works

```
scripts/fetch_4roots_farm.py     -> data/sources/4roots-farm.json
scripts/fetch_house_on_lang.py   -> data/sources/house-on-lang.json
scripts/fetch_those_guys_cafe.py -> data/sources/those-guys-cafe.json
                                          \
data/manual-events.json  ------------------+--> scripts/merge.py -> data/events.json -> site/events.json
                                          /
(Instagram screenshots, read by Claude) -'
```

- `scripts/build.py` runs every fetcher (tolerating individual failures),
  merges everything with `scripts/merge.py`, and copies the result into
  `site/events.json` so the static site is self-contained.
- `site/` is the actual deployable static site: `index.html` + `app.js` +
  `style.css`, reading `events.json` client-side. No backend, no build step.

## Running it locally

```bash
source .venv/bin/activate
python3 scripts/build.py
python3 -m http.server 8765 --directory site   # then open http://localhost:8765
```

(The venv already has `requests`, `beautifulsoup4`, `icalendar`, and
`python-dateutil` installed.)

## Sources

| Source | Method | Notes |
|---|---|---|
| 4Roots Farm | Public JSON API (The Events Calendar / Tribe Events plugin) | Most reliable source -- structured title, date, venue, price, categories. |
| The House on Lang | Server-rendered JSON embedded in the page (`#wix-warmup-data`) | Reliable, but only returns the widget's first page of upcoming events (~2-3 weeks out), no pagination. |
| Those Guys Cafe | Instagram post captions embedded in a `<noscript>` fallback on their homepage | Best-effort only: Squarespace truncates captions at ~250 characters, so later days in a multi-day post can get silently dropped. No event times, only a date + Instagram handle for location. |
| Orlando Weekly | *(not automated)* | Their `/events/` page is wired for a CitySpark widget that currently returns zero events and never fires its API call -- the feature appears to be dormant on their end, not just hard to scrape. Re-check periodically; see "Orlando Weekly" below if it comes back online. |
| @stufftodoinorlando, @letsroam.orlando (Instagram) | Manual, via screenshots | See below. |

### Adding events from Instagram screenshots

Instagram has no public API for reading a profile's posts without logging
in, and scraping it is against their ToS / gets blocked quickly -- not
something to run in a daily automated job. Instead:

1. Drop screenshots of posts worth including into `data/screenshots/`.
2. Ask Claude (in a session) to process them -- it reads the images
   directly, extracts event details, and appends them to
   `data/manual-events.json` in the shared event schema (see
   `scripts/schema.py`).
3. Run `python3 scripts/build.py` to fold them into `events.json`.

`data/manual-events.json` is also just a plain JSON array, so any other
one-off event you hear about can be added there by hand the same way.

### If Orlando Weekly's calendar comes back online

Check `https://www.orlandoweekly.com/events/` in a real browser with the
network tab open for a request to `portal.cityspark.com`. If it starts
firing, capture that request's URL/payload and a fetcher can be added the
same way as the others.

## Event schema

Every event (from any source) is normalized to:

```json
{
  "id": "...",            // stable hash of source+title+start
  "title": "...",
  "start": "2026-09-20T16:00:00-04:00",  // ISO datetime, or bare YYYY-MM-DD if no time is known
  "end": "2026-09-20T18:00:00-04:00",    // or null
  "location": "...",       // or null
  "description": "...",    // or null
  "price": "...",          // or null
  "categories": ["workshop-class"],  // see scripts/schema.py CATEGORIES
  "url": "...",
  "image": "...",          // or null
  "source": "house-on-lang"
}
```

`scripts/merge.py` drops events in the past and further out than 120 days,
dedupes by `id`, and sorts by start date.

## Known limitations

- Those Guys Cafe events may be incomplete (see above) and never have a
  time.
- Orlando Weekly isn't included until their events feature is working again.
- Instagram sources depend on someone periodically dropping in screenshots.
