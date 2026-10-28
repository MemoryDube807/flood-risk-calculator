"""
Flood hazard scoring for a single point.

The score asks three questions about the next 48 hours, each measured against
the place's own climate rather than a fixed number of millimetres:

1. Rain:    how big is the 48-hour rainfall compared with the 2-day fall this
            place gets about once every two years?
2. Wetness: how wet is the ground already, from the rain of the previous 30 days?
3. River:   how high is the nearest river compared with its usual yearly peak?

Each answer becomes a ratio, the ratio is capped, and the three are combined
with fixed weights into a hazard score from 0 to 100. Local exposure (how low
the point sits and how well it drains) then adjusts the score.

Pure Python, no third-party packages, so the same rules run in the CLI, the
Flask API, the backtest and the tests. The browser tool mirrors these numbers.
"""

from statistics import median

# ---------------------------------------------------------------- settings
WEIGHTS = {"rain": 0.5, "wetness": 0.3, "river": 0.2}
CAPS = {"rain": 1.5, "wetness": 1.5, "river": 2.0}   # ratio at which a factor is maxed out
API_DECAY = 0.9                                         # antecedent precipitation index
API_DAYS = 30
MIN_RIVER_FLOW = 1.0      # m3/s: below this yearly peak the point isn't on a real river
MODERATE = 35             # thresholds chosen from the backtest (see README)
HIGH = 50

DRAINAGE_FACTOR = {"good": 0.9, "moderate": 1.0, "poor": 1.15}


# ---------------------------------------------------------------- climatology
def hydrological_year(iso_date):
    """Zambia's rainy season straddles the new year, so years run July to June."""
    y, m = int(iso_date[:4]), int(iso_date[5:7])
    return y if m >= 7 else y - 1


def two_day_totals(rain):
    return [None] + [a + b if a is not None and b is not None else None
                     for a, b in zip(rain[:-1], rain[1:])]


def antecedent_index(rain_before, decay=API_DECAY, days=API_DAYS):
    """Weighted sum of the last `days` daily totals, most recent first weight 1."""
    recent = list(rain_before)[-days:]
    total = 0.0
    for i, r in enumerate(reversed(recent)):
        if r is not None:
            total += r * decay ** i
    return total


def rain_climatology(dates, rain, first_year=1991, last_year=2019):
    """
    Returns
      rl2:   median of the yearly maximum 2-day rainfall (a fall this size comes
             about once every two years)
      api90: 90th percentile of the antecedent index on November to March days
    """
    r2 = two_day_totals(rain)
    yearly_max = {}
    for d, v in zip(dates, r2):
        hy = hydrological_year(d)
        if v is None or not first_year <= hy <= last_year:
            continue
        yearly_max[hy] = max(yearly_max.get(hy, 0.0), v)
    rl2 = median(yearly_max.values())

    apis = []
    for i in range(API_DAYS + 2, len(rain)):
        d = dates[i]
        if int(d[5:7]) in (11, 12, 1, 2, 3) and first_year <= hydrological_year(d) <= last_year:
            apis.append(antecedent_index(rain[i - 2 - API_DAYS:i - 1]))
    apis.sort()
    api90 = apis[int(0.9 * (len(apis) - 1))]
    return {"rl2": rl2, "api90": api90}


def river_climatology(dates, flow, first_year=1997, last_year=2019):
    """Median yearly peak flow, roughly the 2-year flood flow for the river cell."""
    yearly_max = {}
    for d, q in zip(dates, flow):
        hy = hydrological_year(d)
        if q is None or not first_year <= hy <= last_year:
            continue
        yearly_max[hy] = max(yearly_max.get(hy, 0.0), q)
    return {"q2": median(yearly_max.values()) if yearly_max else 0.0}


# ---------------------------------------------------------------- scoring
def _capped(x, cap):
    return max(0.0, min(x / cap, 1.0))


def hazard_score(rain_48h, antecedent, river_flow, clim):
    """
    rain_48h:   rainfall total for the 48-hour window, mm
    antecedent: antecedent index for the 30 days before that window
    river_flow: peak river discharge in the window, m3/s, or None
    clim:       dict with rl2, api90 and q2 for this point
    """
    rain_ratio = rain_48h / clim["rl2"] if clim["rl2"] > 0 else 0.0
    wet_ratio = antecedent / clim["api90"] if clim["api90"] > 0 else 0.0
    has_river = river_flow is not None and clim.get("q2", 0) >= MIN_RIVER_FLOW
    river_ratio = river_flow / clim["q2"] if has_river else None

    parts = {
        "rain": WEIGHTS["rain"] * _capped(rain_ratio, CAPS["rain"]),
        "wetness": WEIGHTS["wetness"] * _capped(wet_ratio, CAPS["wetness"]),
        # with no river at the point, its share follows ground wetness instead
        "river": WEIGHTS["river"] * (_capped(river_ratio, CAPS["river"]) if has_river
                                      else _capped(wet_ratio, CAPS["wetness"])),
    }
    score = 100 * sum(parts.values())
    return {
        "score": round(score, 1),
        "points": {k: round(100 * v, 1) for k, v in parts.items()},
        "ratios": {"rain": round(rain_ratio, 2), "wetness": round(wet_ratio, 2),
                   "river": None if river_ratio is None else round(river_ratio, 2)},
        "has_river": has_river,
        "level": level(score),
    }


def relative_height(grid, half_steps):
    """Height of the centre point above the lowest point in the surrounding grid, m."""
    centre = grid[len(grid) // 2]
    return centre - min(grid)


def exposure_factor(rel_height_m, drainage="moderate"):
    """
    Judgement-based adjustment for local exposure. Not validated by the backtest,
    because each test location has one fixed terrain value.
    """
    if rel_height_m < 5:
        terrain = 1.15          # in a hollow or on a flat floodplain
    elif rel_height_m < 20:
        terrain = 1.0
    else:
        terrain = 0.85          # on a slope or rise
    return terrain * DRAINAGE_FACTOR[drainage]


def level(score):
    if score >= HIGH:
        return "HIGH"
    if score >= MODERATE:
        return "MODERATE"
    return "LOW"


ADVICE = {
    "HIGH": ("Flooding is likely in low-lying areas. Move people, livestock, seed, fertiliser "
             "and tools to higher ground today. Avoid crossing streams and flooded roads, and "
             "alert neighbours and the District Disaster Management Committee."),
    "MODERATE": ("Conditions could turn to flooding. Clear drains and culverts around homes and "
                 "fields, keep valuables off the floor, and check river levels and Zambia "
                 "Meteorological Department warnings over the next two days."),
    "LOW": ("No flood signal for the next 48 hours. Keep drains clear and keep an eye on "
            "forecasts during the rainy season."),
}


def assess(rain_48h, antecedent, river_flow, clim, rel_height_m=None, drainage="moderate"):
    """Hazard score, exposure-adjusted risk, level and advice."""
    h = hazard_score(rain_48h, antecedent, river_flow, clim)
    factor = exposure_factor(rel_height_m, drainage) if rel_height_m is not None else DRAINAGE_FACTOR[drainage]
    risk = min(100.0, h["score"] * factor)
    lv = level(risk)
    return {**h, "exposure_factor": round(factor, 2), "risk": round(risk, 1),
            "risk_level": lv, "advice": ADVICE[lv]}
