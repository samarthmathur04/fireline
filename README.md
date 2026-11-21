# Fireline

**Built for the Grok Bot Hackathon — Berkeley × Stanford, Track 3 (Most Technically Complex).**

**Live demo: https://keep-your-home-insurable.onrender.com** (free Render instance: the first load after idle can take about 50 seconds)

Portfolio repo: https://github.com/samarthmathur04/fireline-showcase · Fork mirror: https://github.com/samarthmathur04/fireline · Upstream: https://github.com/saenz-blip/keep-your-home-insurable

**Fireline** turns public weather and satellite data into one wildfire **insurance risk signal** for a US address. It is not an insurer's score.

> The original project name was *Keep Your Home Insurable*; the deployed URL still uses that name on Render.

## Docs (this fork)

- [Demo script](docs/DEMO.md) · [Fork vs upstream](docs/FORK.md)
- [Frontend notes](docs/frontend/README.md) (globe, hero, feeds, outage demo)

## Inspiration

Homeowners in fire country are losing coverage and cannot see the number an insurer used. The public ingredients of a bad fire day are already online: afternoon heat, dry air, wind, days since rain, and satellite hotspots. This is a hackathon tool (Berkeley x Stanford Grok Bot Hackathon, Track 3) that puts those feeds in one place and pairs them with California's Safer from Wildfires checklist.

## What it does

Enter a US address. The page returns:

1. A 0–100 risk score for today and the next three days, plus one plain alert from the highest day.
2. Nearby satellite heat detections, with distance in km and miles and a compass direction. Known refinery flares are removed. Low-confidence hits and repeated weak nominal hits are listed separately and left out of the score.
3. The Safer from Wildfires checklist. Checking an item stores it in this browser and re-ranks what is left.
4. A label on every result: **Estimated risk from public data.** Not the insurer's score.
5. A dark map of the address with nearby detections and 5 / 15 / 50 km "fire proximity gradient" rings (Leaflet + OpenStreetMap).
6. A night globe hero (globe.gl) that flies to the address and plots kept detections in orange and filtered flares in gray.
7. "Today from orbit": NASA GIBS VIIRS true color plus NOAA-20 and NOAA-21 thermal anomalies for today (falls back to yesterday, hides if both fail).
8. A USDA NAIP aerial photo of the lot (about 1 m, updated every 2–3 years, labeled as not today's image).
9. A "Did you mean" line when the geocoder's match looks loose.

The default example is Caney Creek Lane, Greene County, TN. The second example is Grizzly Peak Blvd, Berkeley, CA. Both are buttons on the page. Change the default in `DEFAULT_EXAMPLE_ADDRESS` in `app/constants.py`.

If a feed fails and a previous response is on disk, the page says the data is hours old. If there is no cache, that piece is left out and the score is marked partial. The app does not invent numbers.

## How we built it

Python, FastAPI, one static page. Run with `uvicorn app.main:app`.

- Geocoding: OpenStreetMap Nominatim, `countrycodes=us`, one request per second, a descriptive User-Agent.
- Forecast: National Weather Service `api.weather.gov` `/points/{lat},{lon}`, then `forecastGridData`. Hourly grid values become an afternoon worst case (local 12:00–18:00): max temperature, min relative humidity, max of sustained wind and gust. Active alerts come from `/alerts/active?point=`. A Red Flag Warning bumps only the days it overlaps.
- Rain: NASA POWER daily `PRECTOTCORR`, 45 days. Meaningful rain is at least 2.5 mm in a day.
- Fires: NASA FIRMS area CSV for `VIIRS_SNPP_NRT`, `VIIRS_NOAA20_NRT`, and `VIIRS_NOAA21_NRT`, last 3 days. The key is `FIRMS_MAP_KEY`. If it is missing, the score is partial and the page says so.
- HTTP: `httpx` with a 15s timeout and `tenacity` retries (3 tries, exponential backoff) on timeouts and 429/5xx.
- Cache: `cache/`, gitignored, keyed by feed and location rounded to 0.01°. `SIMULATE_OUTAGE` or `?simulate_outage=` forces the cache path.
- Page: Samarth's dark globe.gl shell (Instrument Serif / IBM Plex Mono / Inter) with the score hero, plus the PR #2 sections below it: Leaflet fire-proximity map (5/15/50 km), NASA GIBS "Today from orbit", USDA NAIP aerial, full score breakdown, nearby detections, data freshness, and the Safer from Wildfires checklist in `localStorage`.
- Deploy: Render free web service from `main`, `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. `FIRMS_MAP_KEY` is a Render secret environment variable, never in the repo. `CACHE_DIR=/tmp/kyhi-cache` keeps the disk cache on a writable path. Every push to `main` redeploys.

NIFC WFIGS current incidents are queried when the score runs, and named incidents within 70 km are shown if that feed answers. Prescribed burns stay in the list and are labeled RX. They are not required for the score.

## Scoring formula and weights

Fosberg Fire Weather Index, as transcribed by Goodrick (2001) and the University of Washington atmospheric-science definition. Temperature is °F, humidity is percent, wind is mph.

Equilibrium moisture content:

- humidity under 10%: `m = 0.03229 + 0.281073 h − 0.000578 h T`
- 10% through 50% inclusive: `m = 2.22749 + 0.160107 h − 0.01478 T`
- above 50%: `m = 21.0606 + 0.005565 h² − 0.00035 h T − 0.483199 h`

`m` is clamped to 0–30. Then:

```
eta = 1 − 2(m/30) + 1.5(m/30)² − 0.5(m/30)³
FFWI = eta × sqrt(1 + U²) / 0.3002
```

capped at 100. Afternoon wind is the greater of sustained speed and gust when both exist.

The daily score is a weighted sum of four 0–100 pieces. Weights live in `SCORE_WEIGHTS` in `app/constants.py` and sum to 1. If a piece is missing, the rest are rescaled to 1 and the day is marked partial.

| Piece | Weight | Normalized how |
| --- | --- | --- |
| FFWI | 0.55 | The index itself, already 0–100. Day-of fire weather dominates. |
| Days since meaningful rain | 0.25 | 0 days → 0, 21 days → 100, linear between. 2.5 mm/day is the wetting-rain line (about 0.10 inch). Counted only through the latest valid POWER day. |
| Nearby detection | 0.12 | 100 within 5 km, 0 at 50 km, linear between. No detection left after filters is 0, which is a real reading. A missing FIRMS feed is left out. |
| Red Flag Warning | 0.08 | 100 if an NWS Red Flag Warning overlaps that local day, else 0. |

That nearby term is at most 12 points, so a fire a few hundred meters away can still land in Moderate. After the weighted sum, a kept detection of at least 1 MW (not an industrial flare, not a low-confidence hit, not persistent sub-1 MW heat) sets a floor. The published score is the higher of the weighted sum and the floor. Within 2 km the floor is 85 (Extreme). Within 5 km it is 70 (High). From 5 km to 15 km it fades linearly from 70 to 0. At 15 km or with no qualifying detection, the floor is 0. The breakdown has its own "Proximity floor" line with that reason. The numbers are `PROXIMITY_FLOOR_*` in `app/constants.py`.

Bands from the rounded score: 0–24 Low, 25–49 Moderate, 50–74 High, 75–100 Extreme. The alert sentence comes from the highest day. It is only the "High risk Saturday…" form when afternoon fire weather exists. Otherwise the line says the estimate is partial.

Each component in the API and on the page includes the raw input, the 0–100 value, the weight, and the points contributed.

### Checklist weights

These rank unfinished work. They sum to 100. They do not change the weather score and they are not a premium. The regulation, 10 CCR § 2644.9, lists the measures and sets no percentages. Filed discount ranges from large California insurers are only a relative hint (Class A roof about 0.3–5%, windows 0.1–5%, vents 0.1–2%, 6-inch noncombustible base 0.1–2%, enclosed eaves 0.1–1%, Firewise USA 0.3–20%, the last range too skewed to use as a midpoint). The 5-foot zone is ranked just under the roof because IBHS finds most home ignitions start in that zone.

| Item | Points |
| --- | --- |
| Class A roof | 18 |
| 5-ft ember-resistant buffer | 16 |
| Dual-pane windows or shutters | 14 |
| Ember-resistant vents | 10 |
| Defensible space brush clearing | 10 |
| Noncombustible bottom 6 inches | 8 |
| Sheds and outbuildings 30 ft away | 8 |
| Clear under decks | 6 |
| Enclosed eaves | 5 |
| Firewise USA community | 5 |

## Refinery flares

A live FIRMS read for the Berkeley/Oakland area (about 37.87, −122.23) put the nearest detections on the Richmond Chevron refinery (about 37.94–37.95, −122.39 to −122.40) and the Martinez refineries (about 38.02, −122.06 to −122.11). Fire radiative power was often under 1 MW. Those are industrial flares, not wildfires.

`INDUSTRIAL_HEAT_SOURCES` in `app/constants.py` is a short list of facility circles, including those two. Anything inside a circle is counted, named, and left out of the score, including a high-FRP hit. A real fire inside a circle would be hidden, so the radii stay on the plants.

Separate from that list: a cluster is treated as possible static heat when it has at least two detections within 1 km, every one is nominal confidence with FRP under 1 MW, and they come from two satellites or two days. Those are listed and not scored. One weak detection is not enough to drop. Low-confidence rows are listed separately and not scored.

On 19 Nov 2026 the live Berkeley lookup filtered 7 refinery detections (4 Chevron Richmond, 3 Martinez) and set aside 2 low-FRP detections, scoring 10 (Low). The filter is also covered by `tests/test_firms.py` with an inline CSV string, which the app does not use.

## POWER lag

NASA POWER daily data runs about three days behind. On 19 Nov 2026 a live pull for both example addresses ended at 16 Nov 2026. The newer days came back as −999. The app drops fill values (anything at or below −900) and out-of-range values, counts them, and always shows "POWER data runs ~3 days behind" plus the latest valid day. Trailing fill days are not counted as dry days. Days since rain are measured back from the last valid day to the last day with at least 2.5 mm. If every day is fill, dryness is left out of the score.

## Challenges we ran into

- Nominatim and NWS both reject generic clients. Each request sends a descriptive User-Agent, and Nominatim is limited to one request per second.
- NWS grid steps are not always one hour, and the units are Celsius and km/h. The aggregator converts them and keeps only local afternoon hours.
- `/points` returns 404 outside the forecast grid. That is a partial score, not a 500.
- POWER's −999 fill looks like a number. Treating it as zero rain would invent a dry or wet day.
- FIRMS will report refinery flares as fire. The key is also easy to not have. Missing key, empty CSV, and a simulated outage each have their own message.
- Several US towns share a name. More than one match farther than 1 km apart comes back as a choice, not a guess.

## Accomplishments

A deployed, public, all-live app. On 19 Nov 2026 the default address, Caney Creek Lane, Greene County, TN (36.36297, −82.79874), sat next to the active "Greene - Caney Creek Lane" wildfire (WF in NIFC WFIGS, not a prescribed burn). It scored 85 (Extreme) with the alert "Active wildfire 0.4 km W (Greene - Caney Creek Lane). Extreme risk today. Clear brush within 30 ft now." Grizzly Peak Blvd, Berkeley, CA scored 10 (Low) with the refinery flares filtered out. Both were checked on the Render deployment, and 32 tests pass. The outage switch serves the cached NWS and POWER payloads and labels them as under an hour old. Unit tests cover the Fosberg index against hand-computed values, the flare filter, an all-fill POWER window, and the cache fallback.

## What we learned

A fire-weather index is not an insurance rate, and the page has to say so in the same place as the number. The useful version of "robust" is a missing feed with an honest gap, not a filled-in score. Most of the East Bay hotspots in a casual FIRMS glance are stacks, not hills on fire.

## What's next

Parcel-level fuel data (vegetation within 30 and 100 ft). Wind-direction-aware fire proximity, since a fire upwind matters more. More of the industrial list only where a live read shows a repeating flare. Evacuation and smoke, still labeled as public data.

## How Grok Bot helped build it

The team drove the project from a Grok Bot chat. Grok Bot planned the work, pulled and checked the live feeds itself (raw FIRMS detections, POWER −999 fill days, NWS grids), found the live WF incident used as the demo default through NIFC WFIGS, and verified the GIBS and NAIP image requests before any code used them. It launched and steered a Cursor cloud agent that wrote the code in pull requests ([#1](https://github.com/saenz-blip/keep-your-home-insurable/pull/1), [#2](https://github.com/saenz-blip/keep-your-home-insurable/pull/2)). Before each merge, Grok Bot ran the tests and the Greene TN and Berkeley lookups on its own computer. It also deployed the app to Render through the Render connector, ran scheduled check-ins against the hackathon timeline, and rechecked the fire feeds before the demo. The exported session, with personal details and keys removed, is in [`docs/grok-bot-session.md`](docs/grok-bot-session.md). The formula, the 2.5 mm rain line, the refinery circles, and the checklist points are documented in `app/constants.py` so a person can check them without trusting the chat.

## How to run it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# optional: put a NASA FIRMS MAP key in .env as FIRMS_MAP_KEY=
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000

Tests:

```bash
python3 -m pytest
```

### Demo the outage fallback

Look up an address once so `cache/` has NWS and POWER. Then either:

```bash
SIMULATE_OUTAGE=nws,power python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

or, with the server already running, add this to the "Demo a feed outage" box on the page, or to the URL:

```
?simulate_outage=nws,power
```

The score should still appear, with a line that those feeds are saved data and how many hours old. `firms` can be included. With no key and no earlier successful FIRMS response, that feed stays "unavailable" instead of showing fake fires.

`cache/` and `.env` are gitignored. Do not commit a MAP key.
