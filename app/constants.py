"""Weights, thresholds, and source notes for the risk score and checklist.

Nothing in this module is an insurance rate. The score is an estimate built
from public weather and satellite feeds so a homeowner can see *why* a day
looks risky. California's Safer from Wildfires regulation (10 CCR § 2644.9)
requires insurers to reflect the checklist measures in their rates, but it
does not publish the percentages. The checklist weights below are a rank
scale for unfinished work, not a premium quote.
"""

from __future__ import annotations

# The primary example button. Change this one string to point the demo elsewhere.
# Verified live: Nominatim resolves it to 36.36297, -82.79874, the NIFC incident
# "Greene - Caney Creek Lane" (wildfire, discovered 2026-11-18).
DEFAULT_EXAMPLE_ADDRESS = "Caney Creek Lane, Greene County, TN"
# Second example button. Not special in the scoring code.
SECOND_EXAMPLE_ADDRESS = "Grizzly Peak Blvd, Berkeley, CA"

USER_AGENT = (
    "Fireline/1.0 (educational US wildfire insurance-risk demo; "
    "+https://github.com/samarthmathur04/fireline; "
    "+https://github.com/saenz-blip/keep-your-home-insurable; "
    "contact: saenz-blip@users.noreply.github.com)"
)

# Preset examples carry coordinates so they never need a geocoder.
DEFAULT_EXAMPLE_LAT = 36.36297
DEFAULT_EXAMPLE_LON = -82.79874
SECOND_EXAMPLE_LAT = 37.8826
SECOND_EXAMPLE_LON = -122.2373

# Two Nominatim hits farther apart than this are treated as different places.
GEOCODE_AMBIGUOUS_KM = 1.0

# --- Fosberg Fire Weather Index -------------------------------------------------
# Equilibrium moisture content is Simard's piecewise regression as used by
# Fosberg (1978) and transcribed by Goodrick (2001) and the University of
# Washington atmospheric-science FFWI definition:
#   h < 10:          m = 0.03229 + 0.281073 h - 0.000578 h T
#   10 <= h <= 50:   m = 2.22749 + 0.160107 h - 0.01478 T
#   h > 50:          m = 21.0606 + 0.005565 h^2 - 0.00035 h T - 0.483199 h
# T is degrees Fahrenheit, h is relative humidity in percent.
# The middle coefficient is 0.01478 (Goodrick / UW FFWI), not the 0.014784
# figure that appears in the NFDRS EMC writeup.
# Moisture damping: eta = 1 - 2(m/30) + 1.5(m/30)^2 - 0.5(m/30)^3
# FFWI = eta * sqrt(1 + U^2) / 0.3002, with U in mph, then capped to [0, 100].
# EMC is clamped to [0, 30] before eta so a wild input cannot push the index
# negative. 30% is the moisture-of-extinction Fosberg assumed.

FFWI_CAP = 100.0
EMC_MIN = 0.0
EMC_MAX = 30.0

# Local afternoon window used to turn hourly NWS grid values into one
# worst-case sample per day. Hours are in the gridpoint time zone.
# 12:00 inclusive, 18:00 exclusive.
AFTERNOON_START_HOUR = 12
AFTERNOON_END_HOUR = 18
FORECAST_DAYS = 4  # today + the next 3 days

# --- Dryness --------------------------------------------------------------------
# Meaningful rain is a wetting rain of at least 2.5 mm in a day (0.10 inch).
# That is enough to damp fine surface fuels; lighter totals often evaporate
# off hot duff. NASA POWER daily PRECTOTCORR is the source.
# The dryness factor is linear from 0 days (normalized 0) to DRYNESS_FULL_DAYS
# (normalized 100). 21 days is long enough for 1-hour and 10-hour fuels to
# have lost a wetting rain and for 100-hour fuels to be well into a dry spell.
# This is a transparent stand-in for a drought index, not KBDI.
MEANINGFUL_RAIN_MM = 2.5
DRYNESS_FULL_DAYS = 21
POWER_LOOKBACK_DAYS = 45  # inside the requested 30–60 day window
# POWER daily files trail real time. Live checks on 2026-11-19 showed the
# newest two or three days as the -999 fill. Values at or below this sentinel
# are dropped, never treated as zero rain.
POWER_FILL_SENTINEL = -900.0
POWER_LAG_NOTE = "POWER data runs ~3 days behind"

# --- Nearby fire ----------------------------------------------------------------
# Full factor inside NEARBY_FIRE_FULL_KM, linear decay to 0 at
# NEARBY_FIRE_ZERO_KM. 5 km is "this can spot onto the neighborhood today".
# 50 km is the edge of "nearby" for a hills homeowner looking at active heat,
# not a smoke-transport model.
NEARBY_FIRE_FULL_KM = 5.0
NEARBY_FIRE_ZERO_KM = 50.0
# The weighted nearby-fire term tops out at 12 points, so a fire on the
# doorstep can still look Moderate. After the weighted sum, a kept detection
# that is not industrial, not low-confidence, and not under 1 MW
# (STATIC_HEAT_MAX_FRP_MW) imposes a floor. The published score is the
# higher of the weighted sum and this floor.
#   <= 2 km: 85 (Extreme)
#   <= 5 km: 70 (High)
#   5 to 15 km: linear from 70 down to 0
#   >= 15 km, or no qualifying detection: 0
PROXIMITY_FLOOR_INNER_KM = 2.0
PROXIMITY_FLOOR_INNER = 85.0
PROXIMITY_FLOOR_NEAR_KM = 5.0
PROXIMITY_FLOOR_NEAR = 70.0
PROXIMITY_FLOOR_ZERO_KM = 15.0
# Search box is wider than the decay distance so a fire just past 50 km is
# still listed, with a factor of 0.
FIRMS_SEARCH_RADIUS_KM = 70.0
FIRMS_DAYS = 3  # FIRMS area API day window; allowed range the brief asked is 1–3
FIRMS_SOURCES = (
    "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA21_NRT",
)
# Detections closer than this to a stronger one are the same hotspot seen by
# another satellite. The kept row is the highest FRP in the cluster.
FIRMS_DEDUPE_KM = 1.0

# Possible static heat that is not on the named-site list. A cluster is left
# out of the score only when every one of these is true:
#   - at least STATIC_HEAT_MIN_DETECTIONS points within STATIC_HEAT_CLUSTER_KM
#   - every point is nominal confidence (low confidence is counted separately;
#     any high-confidence point keeps the whole cluster)
#   - every point has fire radiative power under STATIC_HEAT_MAX_FRP_MW
#   - the points come from two or more satellites, or from two calendar days
# One weak overpass is not enough: a single nominal detection under 1 MW stays
# in the score. Matched clusters are still listed, with this reason.
STATIC_HEAT_MAX_FRP_MW = 1.0
STATIC_HEAT_CLUSTER_KM = 1.0
STATIC_HEAT_MIN_DETECTIONS = 2

# NIFC current incidents, attached to a detection when the incident point is
# within this distance. Used for names and for the WF / RX label, not as a
# replacement for the FIRMS distance factor.
WFIGS_SEARCH_RADIUS_KM = 70.0
WFIGS_ATTACH_KM = 15.0
WFIGS_QUERY = (
    "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/"
    "WFIGS_Incident_Locations_Current/FeatureServer/0/query"
)

# Known static industrial heat. A real wildfire inside one of these radii
# would be hidden, so the radii stay on the facility, not the town.
# Richmond and Martinez are the flares a live FIRMS read for the East Bay
# actually returns (FRP often under 1 MW). The other centers are OpenStreetMap
# facility points looked up once and written down here; they are not fetched
# at runtime and they are not a fire archive.
INDUSTRIAL_HEAT_SOURCES = (
    {
        "id": "chevron_richmond",
        "name": "Chevron Richmond Refinery",
        "lat": 37.9415,
        "lon": -122.3950,
        "radius_km": 1.8,
        "why": "OSM facility center. Covers the flare cluster near 37.94–37.95 N, 122.39–122.40 W.",
    },
    {
        "id": "martinez_refineries",
        "name": "Martinez refineries",
        "lat": 38.020,
        "lon": -122.085,
        "radius_km": 3.0,
        "why": "Static heat verified near 38.02 N, 122.06–122.11 W. OSM has no single facility point.",
    },
    {
        "id": "valero_benicia",
        "name": "Valero Benicia Refinery",
        "lat": 38.0720,
        "lon": -122.1382,
        "radius_km": 1.8,
        "why": "OSM facility center.",
    },
    {
        "id": "chevron_el_segundo",
        "name": "Chevron El Segundo Refinery",
        "lat": 33.9158,
        "lon": -118.4191,
        "radius_km": 2.0,
        "why": "OSM facility center.",
    },
    {
        "id": "motiva_port_arthur",
        "name": "Motiva Port Arthur Refinery",
        "lat": 29.8861,
        "lon": -93.9607,
        "radius_km": 2.5,
        "why": "OSM facility center.",
    },
    {
        "id": "bp_whiting",
        "name": "BP Whiting Refinery",
        "lat": 41.6658,
        "lon": -87.4804,
        "radius_km": 2.5,
        "why": "OSM facility center.",
    },
    {
        "id": "marathon_anacortes",
        "name": "Marathon Anacortes Refinery",
        "lat": 48.4892,
        "lon": -122.5632,
        "radius_km": 2.0,
        "why": "OSM facility center.",
    },
    {
        "id": "phillips66_rodeo",
        "name": "Rodeo San Francisco Refinery",
        "lat": 38.0429,
        "lon": -122.2532,
        "radius_km": 1.6,
        "why": "OSM industrial point for the Rodeo refinery (Phillips 66).",
    },
    {
        "id": "exxon_baytown",
        "name": "Baytown Refinery",
        "lat": 29.7420,
        "lon": -95.0270,
        "radius_km": 2.5,
        "why": "OSM point named Baytown Refinery.",
    },
    {
        "id": "marathon_garyville",
        "name": "Garyville Refinery",
        "lat": 30.0618,
        "lon": -90.5956,
        "radius_km": 2.5,
        "why": "OSM works point for the Garyville refinery.",
    },
    {
        "id": "wood_river",
        "name": "Wood River Refinery",
        "lat": 38.8407,
        "lon": -90.0616,
        "radius_km": 2.0,
        "why": "OSM industrial point in Roxana, Illinois.",
    },
    {
        "id": "chevron_pascagoula",
        "name": "Pascagoula Refinery",
        "lat": 30.3443,
        "lon": -88.4826,
        "radius_km": 2.0,
        "why": "OSM industrial point for the Pascagoula refinery.",
    },
)

# VIIRS NRT confidence is the text low / nominal / high (sometimes l / n / h).
# A numeric value, as in MODIS, is treated as low below this threshold.
LOW_CONFIDENCE_NUMERIC_BELOW = 30.0

# --- Score blend ----------------------------------------------------------------
# Each component is normalized to 0–100, multiplied by its weight, and summed.
# Weights sum to 1. If a component has no live data and no cache, it is left
# out and the remaining weights are rescaled to 1. The result is marked partial.
#   ffwi         Day-of fire weather. FFWI is already a 0–100 index.
#   dryness      Days since a wetting rain, from POWER.
#   nearby_fire  Distance to the closest FIRMS detection that survived filters.
#   red_flag     100 if an NWS Red Flag Warning overlaps that local day, else 0.
# Weather dominates because it changes every afternoon. Dryness is the fuel
# context Goodrick added on top of FFWI, here as days-since-rain because that
# is what POWER actually gives us. Nearby fire is down-weighted because one
# hotspot is not a spread model and industrial false positives are common.
# Red Flag is a small official bump: the weather that triggered it is already
# inside FFWI.
SCORE_WEIGHTS = {
    "ffwi": 0.55,
    "dryness": 0.25,
    "nearby_fire": 0.12,
    "red_flag": 0.08,
}

RISK_BANDS = (
    (75, "Extreme"),
    (50, "High"),
    (25, "Moderate"),
    (0, "Low"),
)

DISCLAIMER = (
    "Estimated risk from public data. This is not an insurer's score, "
    "not a premium, and not a prediction that a fire will reach this address."
)

# --- Checklist ------------------------------------------------------------------
# Rank weights sum to 100. They order what is left to do. They are not the
# discount a carrier will file.
#
# Legal list: 10 CCR § 2644.9 (Safer from Wildfires), property-level measures
# in (d)(1)(B) and the community-level Firewise / Fire Risk Reduction
# Community recognition in (d)(1)(A). Descriptions also match the California
# Department of Insurance "Safer from Wildfires" consumer page.
#
# Filed discount ranges, used only as a relative signal because the regulation
# itself sets no percentages:
#   Class A roof 0.3–5%, multi-pane windows 0.1–5%, ember-resistant vents
#   0.1–2%, 6 inches of noncombustible wall base 0.1–2%, enclosed eaves
#   0.1–1%, Firewise USA 0.3–20%
#   (ranges compiled from the 15 largest California homeowners filings, as
#   summarized in public rate-filing comparisons; Kousky & You, "Do California
#   Insurers Reward Wildfire Resilience," report the same spread: Class A
#   under 1% to 5%, Firewise under 1% to 20%).
# The 5-foot zone, under-deck clearing, 30-foot outbuildings, and defensible
# space do not have a single clean midpoint in that summary. Those weights
# follow IBHS Wildfire Prepared Home and CAL FIRE: embers in the first five
# feet start most home ignitions, then vents, windows, and near-home fuels.
# Firewise is not given the midpoint of 0.3–20 (about 10), because that range
# is skewed by a few large filings and a community recognition is not a
# substitute for work on the parcel.

CHECKLIST = (
    {
        "id": "class_a_roof",
        "title": "Class A fire-rated roof",
        "detail": "Asphalt shingles, tile, metal, or another Class A assembly. Wood shake is not Class A.",
        "weight": 18,
        "source": "10 CCR § 2644.9. Largest structural filing range among large California insurers (about 0.3–5%).",
    },
    {
        "id": "zone0_5ft",
        "title": "5-ft ember-resistant buffer",
        "detail": "Clear plants, mulch, wood fences, and stored combustibles within 5 feet of the building. Rock or bare soil is fine.",
        "weight": 16,
        "source": "10 CCR § 2644.9 five-foot zone. IBHS: most home ignitions start from embers in the first 5 feet. No separate filing midpoint, so it ranks just under the roof.",
    },
    {
        "id": "windows",
        "title": "Dual-pane windows or shutters",
        "detail": "Multi-pane glass, or shutters that close over the whole window with no gaps.",
        "weight": 14,
        "source": "10 CCR § 2644.9. Filing range about 0.1–5%, second among structural items.",
    },
    {
        "id": "vents",
        "title": "Ember-resistant vents",
        "detail": "1/16- to 1/8-inch noncombustible mesh, or listed ember-resistant vents, on exterior openings.",
        "weight": 10,
        "source": "10 CCR § 2644.9. Filing range about 0.1–2%. Vents are the usual path for embers into an attic.",
    },
    {
        "id": "defensible_space",
        "title": "Defensible space brush clearing",
        "detail": "Trim trees and clear brush and debris the way Public Resources Code 4291 and your local rules require, beyond the 5-foot zone.",
        "weight": 10,
        "source": "10 CCR § 2644.9 and PRC 4291. Weighted with vents as a major fuel-reduction item; filings do not publish one shared midpoint.",
    },
    {
        "id": "wall_base_6in",
        "title": "Noncombustible bottom 6 inches of exterior walls",
        "detail": "At least 6 vertical inches of brick, stone, fiber-cement, or concrete from the ground and from attached decks.",
        "weight": 8,
        "source": "10 CCR § 2644.9. Filing range about 0.1–2%.",
    },
    {
        "id": "outbuildings_30ft",
        "title": "Sheds and outbuildings 30 ft or farther",
        "detail": "Move combustible sheds, gazebos, playhouses, and similar structures at least 30 feet from the home, or as far as the lot allows.",
        "weight": 8,
        "source": "10 CCR § 2644.9 thirty-foot combustible-structure distance. Limits structure-to-structure spread.",
    },
    {
        "id": "under_decks",
        "title": "Clear under decks",
        "detail": "Remove vegetation, leaves, and stored combustibles from under decks. Bare soil, gravel, or concrete can stay.",
        "weight": 6,
        "source": "10 CCR § 2644.9 under-deck clearing. A localized ember trap, so it ranks under the 30-foot outbuilding distance.",
    },
    {
        "id": "enclosed_eaves",
        "title": "Enclosed eaves",
        "detail": "Soffits under the eaves, preferably ignition-resistant, so heat and embers are not trapped in open rafters.",
        "weight": 5,
        "source": "10 CCR § 2644.9. Smallest structural filing range in the comparison (about 0.1–1%).",
    },
    {
        "id": "firewise",
        "title": "Firewise USA community",
        "detail": "The neighborhood is a recognized Firewise USA site, or an equivalent Fire Risk Reduction Community under the regulation.",
        "weight": 5,
        "source": "10 CCR § 2644.9 community level. Filing range 0.3–20% is too skewed to use as a midpoint; ranked as a supplement to work on the house.",
    },
)

assert sum(item["weight"] for item in CHECKLIST) == 100
assert abs(sum(SCORE_WEIGHTS.values()) - 1.0) < 1e-9
