"""
Backtest the flood hazard score against documented Zambian floods.

For each of the 12 places in data/flood_events.csv the script rebuilds the
daily hazard score from 1997 to 2026 using reanalysis rainfall (ERA5) and
GloFAS river flow, then asks two questions:

  1. Was the score high in the days of each documented flood?
  2. How often did it go high on rainy-season days with no recorded flood?

It also scores the original calculator's rule (48-hour rainfall in mm against
fixed thresholds) on the same days, so the two can be compared.

Run from the repository root after scripts/fetch_history.py:

    python scripts/backtest.py

Writes data/backtest_results.json, which the dashboard reads.
"""

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from floodsense import scoring  # noqa: E402

HIST = os.path.join("data", "history")
OUT = os.path.join("data", "backtest_results.json")
SEASON_MONTHS = [11, 12, 1, 2, 3, 4]
TEST_START, TEST_END = "1997-07-01", "2026-06-30"     # river data begins in 1997
N_SEASONS = 29
GUARD_DAYS = 3        # days either side of a flood excluded from the false-alarm count
EVENT_LEAD = 1        # the score may peak the day before a reported start date


def load(loc):
    rain = pd.read_csv(os.path.join(HIST, f"{loc}_rain.csv"))
    flow = pd.read_csv(os.path.join(HIST, f"{loc}_discharge.csv"))
    with open(os.path.join(HIST, f"{loc}_terrain.json")) as f:
        terrain = json.load(f)
    rain["rain_mm"] = rain["rain_mm"].fillna(0.0)
    return rain, flow, terrain


def daily_scores(rain, flow):
    """Hazard score for every day, using the same functions as the live tool."""
    dates, r = rain["date"].tolist(), rain["rain_mm"].tolist()
    clim = scoring.rain_climatology(dates, r)
    fl = flow.dropna()
    clim.update(scoring.river_climatology(fl["date"].tolist(), fl["discharge_m3s"].tolist()))
    q = dict(zip(flow["date"], flow["discharge_m3s"]))

    rows = []
    for i in range(scoring.API_DAYS + 2, len(r)):
        d = dates[i]
        r48 = r[i - 1] + r[i]
        api = scoring.antecedent_index(r[i - 2 - scoring.API_DAYS:i - 1])
        qs = [q.get(dates[i - 1]), q.get(d)]
        qs = [x for x in qs if x is not None and not np.isnan(x)]
        h = scoring.hazard_score(r48, api, max(qs) if qs else None, clim)
        rows.append((d, r[i], r48, api, h["ratios"]["rain"], h["ratios"]["wetness"],
                     h["ratios"]["river"], h["score"]))
    df = pd.DataFrame(rows, columns=["date", "rain", "r48", "api", "rain_ratio", "wet_ratio",
                                     "river_ratio", "score"])
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date"), clim


def old_rule_points(r48):
    """Rainfall points of the original calculator (0 to 100) from 48-hour rain in mm."""
    return np.select([r48 < 20, r48 < 40, r48 < 60, r48 < 80, r48 < 100], [5, 20, 40, 60, 80], 100)


def old_rule_score(r48, drainage, soil):
    """Original calculator total. Elevation scores 5 everywhere in Zambia (all land is above 100 m)."""
    d = {"poor": 100, "moderate": 55, "good": 15}[drainage]
    s = {"clay": 100, "loam": 50, "sandy": 15}[soil]
    return 0.4 * old_rule_points(r48) + 0.3 * 5 + 0.2 * d + 0.1 * s


def main():
    events = pd.read_csv(os.path.join("data", "flood_events.csv"), parse_dates=["start_date", "end_date"])
    places = {}
    for loc, grp in events.groupby("location_id", sort=False):
        rain, flow, terrain = load(loc)
        df, clim = daily_scores(rain, flow)
        rel = scoring.relative_height(terrain["elevation"], terrain["half_steps"])
        # background: rainy-season days in the test period, away from any documented flood
        mask = (df.index.month.isin(SEASON_MONTHS)) & (df.index >= TEST_START) & (df.index <= TEST_END)
        mask = pd.Series(mask, index=df.index)
        for _, e in grp.iterrows():
            mask.loc[e.start_date - pd.Timedelta(days=GUARD_DAYS):e.end_date + pd.Timedelta(days=GUARD_DAYS)] = False
        places[loc] = {"df": df, "clim": clim, "rel_height": rel, "mask": mask,
                       "lat": float(grp.lat.iloc[0]), "lon": float(grp.lon.iloc[0]),
                       "place": grp.district.iloc[0], "province": grp.province.iloc[0],
                       "mean_annual": float(rain.groupby(rain.date.str[:4]).rain_mm.sum().loc["1991":"2020"].mean())}

    # ---- each documented flood
    ev_rows = []
    for _, e in events.iterrows():
        p = places[e.location_id]
        win = p["df"].loc[e.start_date - pd.Timedelta(days=EVENT_LEAD):e.end_date]
        peak = win["score"].idxmax()
        row = win.loc[peak]
        L = len(win)
        wmax = p["df"]["score"].rolling(L).max()[p["mask"]].dropna()
        pct = float((wmax < row.score).mean() + 0.5 * (wmax == row.score).mean())
        around = p["df"].loc[e.start_date - pd.Timedelta(days=30):e.end_date + pd.Timedelta(days=15)]
        ev_rows.append({
            "id": e.event_id, "location": e.location_id, "place": e.place, "district": e.district,
            "province": e.province, "start": e.start_date.date().isoformat(), "end": e.end_date.date().isoformat(),
            "type": e.flood_type, "source": e.source, "peak_date": peak.date().isoformat(),
            "rain_48h": round(float(row.r48), 1), "rain_ratio": float(row.rain_ratio),
            "antecedent": round(float(row.api), 1), "wet_ratio": float(row.wet_ratio),
            "river_ratio": None if pd.isna(row.river_ratio) else float(row.river_ratio),
            "score": float(row.score), "level": scoring.level(row.score),
            "old_score_poor_clay": float(old_rule_score(row.r48, "poor", "clay")),
            "old_score_moderate_loam": float(old_rule_score(row.r48, "moderate", "loam")),
            "percentile": round(pct, 3),
            "series": {"dates": [d.date().isoformat() for d in around.index],
                       "score": around["score"].round(1).tolist(),
                       "rain": around["rain"].round(1).tolist()},
        })
    ev_df = pd.DataFrame(ev_rows)

    # ---- hit rate against false alarms, new score and the old rainfall rule
    def curve(values_of, event_values, thresholds):
        out = []
        for t in thresholds:
            hits = int(sum(v >= t for v in event_values))
            episodes = 0
            days = 0
            for loc, p in places.items():
                a = (values_of(p) >= t) & p["mask"]
                days += int(a.sum())
                episodes += int((a & ~a.shift(1, fill_value=False)).sum())
            out.append({"threshold": t, "caught": hits,
                        "episodes": round(episodes / (N_SEASONS * len(places)), 2),
                        "days": round(days / (N_SEASONS * len(places)), 1)})
        return out

    new_curve = curve(lambda p: p["df"]["score"], ev_df["score"].tolist(), list(range(20, 91, 5)))
    old_ev = [max(places[r["location"]]["df"].loc[r["start"]:r["end"]].r48.max(),
                  places[r["location"]]["df"].loc[pd.Timestamp(r["start"]) - pd.Timedelta(days=EVENT_LEAD):r["end"]].r48.max())
              for r in ev_rows]
    old_curve = curve(lambda p: p["df"]["r48"], old_ev, list(range(10, 151, 10)))
    old_points = []
    for label, d, s in [("Poor drainage, clay soil", "poor", "clay"), ("Moderate drainage, loam", "moderate", "loam")]:
        for lv, t in [("Moderate", 35), ("High", 65)]:
            c = curve(lambda p, d=d, s=s: pd.Series(old_rule_score(p["df"]["r48"].values, d, s), index=p["df"].index),
                      [old_rule_score(v, d, s) for v in old_ev], [t])[0]
            old_points.append({"label": f"{label}, {lv}", **c})

    lus = ev_df["location"] == "lusaka"
    summary = {
        "n_events": int(len(ev_df)), "n_places": len(places), "n_seasons": N_SEASONS,
        "caught_moderate": int((ev_df.score >= scoring.MODERATE).sum()),
        "caught_high": int((ev_df.score >= scoring.HIGH).sum()),
        "caught_moderate_outside_lusaka": int((ev_df[~lus].score >= scoring.MODERATE).sum()),
        "n_outside_lusaka": int((~lus).sum()),
        "caught_moderate_lusaka": int((ev_df[lus].score >= scoring.MODERATE).sum()),
        "n_lusaka": int(lus.sum()),
        "mean_percentile": round(float(ev_df.percentile.mean()), 3),
        "moderate": next(c for c in new_curve if c["threshold"] == scoring.MODERATE),
        "high": next(c for c in new_curve if c["threshold"] == scoring.HIGH),
    }

    # ---- sensitivity of the ranking to the weights
    sens = []
    base = dict(scoring.WEIGHTS)
    for wr in (0.4, 0.5, 0.6, 0.7):
        for ww in (0.2, 0.3, 0.4):
            wq = round(1 - wr - ww, 2)
            if wq < 0:
                continue
            pcts = []
            for r in ev_rows:
                p = places[r["location"]]
                d = p["df"]
                rr = np.clip(d.rain_ratio / scoring.CAPS["rain"], 0, 1)
                ww_ = np.clip(d.wet_ratio / scoring.CAPS["wetness"], 0, 1)
                qq = np.clip(d.river_ratio.astype(float) / scoring.CAPS["river"], 0, 1).fillna(ww_)
                s = 100 * (wr * rr + ww * ww_ + wq * qq)
                win = s.loc[pd.Timestamp(r["start"]) - pd.Timedelta(days=EVENT_LEAD):r["end"]]
                bg = s.rolling(len(win)).max()[p["mask"]].dropna()
                v = win.max()
                pcts.append((bg < v).mean() + 0.5 * (bg == v).mean())
            sens.append({"rain": wr, "wetness": ww, "river": wq, "mean_percentile": round(float(np.mean(pcts)), 3)})
    scoring.WEIGHTS.update(base)

    result = {
        "settings": {"weights": scoring.WEIGHTS, "caps": scoring.CAPS, "moderate": scoring.MODERATE,
                     "high": scoring.HIGH, "test_period": [TEST_START, TEST_END]},
        "summary": summary,
        "places": [{"id": k, "place": p["place"], "province": p["province"], "lat": p["lat"], "lon": p["lon"],
                    "rl2": round(p["clim"]["rl2"], 1), "api90": round(p["clim"]["api90"], 1),
                    "q2": round(p["clim"]["q2"], 2), "rel_height": round(p["rel_height"], 1),
                    "mean_annual": round(p["mean_annual"], 0),
                    "alert_days_moderate": round(float(((p["df"].score >= scoring.MODERATE) & p["mask"]).sum() / N_SEASONS), 1),
                    "alert_days_high": round(float(((p["df"].score >= scoring.HIGH) & p["mask"]).sum() / N_SEASONS), 1)}
                   for k, p in places.items()],
        "events": ev_rows,
        "curve_new": new_curve, "curve_old_mm": old_curve, "old_points": old_points,
        "sensitivity": sens,
    }
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)

    print(f"Events caught at MODERATE or above: {summary['caught_moderate']}/{summary['n_events']} "
          f"({summary['caught_moderate_outside_lusaka']}/{summary['n_outside_lusaka']} outside Lusaka)")
    print(f"Events caught at HIGH: {summary['caught_high']}/{summary['n_events']}")
    print(f"MODERATE alerts: {summary['moderate']['episodes']} episodes a season per place; "
          f"HIGH: {summary['high']['episodes']}")
    print(f"Mean percentile of flood windows against other rainy-season windows: {summary['mean_percentile']}")
    print(ev_df[["id", "location", "peak_date", "rain_48h", "rain_ratio", "wet_ratio", "river_ratio", "score", "level",
                 "old_score_poor_clay", "percentile"]].to_string(index=False))
    print("Saved", OUT)


if __name__ == "__main__":
    main()
