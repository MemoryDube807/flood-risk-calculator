"""
Download the historical data used to backtest the flood score.

For every location in data/flood_events.csv this saves:
  - daily rainfall, 1991 to the latest available day (ERA5 reanalysis, Open-Meteo archive API)
  - daily river discharge, 1984 to today (GloFAS, Open-Meteo flood API)
  - an 11 x 11 grid of terrain heights around the point, about 2 km across
    (Copernicus 90 m DEM, Open-Meteo elevation API)

Uses only the Python standard library. Run from the repository root:

    python scripts/fetch_history.py

Files land in data/history/. Re-running skips locations that are already saved.
"""

import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta

EVENTS = os.path.join("data", "flood_events.csv")
OUT_DIR = os.path.join("data", "history")
RAIN_START = "1991-01-01"
FLOW_START = "1984-01-01"
GRID_HALF_STEPS = 5          # 11 x 11 points
GRID_STEP_DEG = 0.002        # about 220 m, so the grid spans roughly 2.2 km


def get_json(url, params, tries=4):
    full = url + "?" + urllib.parse.urlencode(params)
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(full, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:          # network hiccups or rate limits: wait and retry
            wait = 10 * (attempt + 1)
            print(f"    request failed ({exc}); retrying in {wait} s")
            time.sleep(wait)
    raise RuntimeError(f"Could not download {full}")


def save_daily(path, dates, values, column):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", column])
        for d, v in zip(dates, values):
            w.writerow([d, "" if v is None else v])


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(EVENTS, newline="") as f:
        rows = list(csv.DictReader(f))
    locations = {}
    for r in rows:
        locations.setdefault(r["location_id"], (float(r["lat"]), float(r["lon"])))

    end = (date.today() - timedelta(days=7)).isoformat()   # ERA5 runs about five days behind
    for loc, (lat, lon) in locations.items():
        print(f"{loc}: {lat}, {lon}")

        rain_path = os.path.join(OUT_DIR, f"{loc}_rain.csv")
        if not os.path.exists(rain_path):
            d = get_json("https://archive-api.open-meteo.com/v1/archive", {
                "latitude": lat, "longitude": lon, "start_date": RAIN_START, "end_date": end,
                "daily": "precipitation_sum", "timezone": "Africa/Lusaka"})
            save_daily(rain_path, d["daily"]["time"], d["daily"]["precipitation_sum"], "rain_mm")
            print(f"    rainfall: {len(d['daily']['time'])} days")
            time.sleep(2)

        flow_path = os.path.join(OUT_DIR, f"{loc}_discharge.csv")
        if not os.path.exists(flow_path):
            d = get_json("https://flood-api.open-meteo.com/v1/flood", {
                "latitude": lat, "longitude": lon, "start_date": FLOW_START,
                "end_date": date.today().isoformat(), "daily": "river_discharge"})
            save_daily(flow_path, d["daily"]["time"], d["daily"]["river_discharge"], "discharge_m3s")
            print(f"    river discharge: {len(d['daily']['time'])} days")
            time.sleep(2)

        terrain_path = os.path.join(OUT_DIR, f"{loc}_terrain.json")
        if not os.path.exists(terrain_path):
            pts = [(lat + i * GRID_STEP_DEG, lon + j * GRID_STEP_DEG)
                   for i in range(-GRID_HALF_STEPS, GRID_HALF_STEPS + 1)
                   for j in range(-GRID_HALF_STEPS, GRID_HALF_STEPS + 1)]
            heights = []
            for k in range(0, len(pts), 100):              # the API takes up to 100 points a call
                chunk = pts[k:k + 100]
                d = get_json("https://api.open-meteo.com/v1/elevation", {
                    "latitude": ",".join(f"{p[0]:.4f}" for p in chunk),
                    "longitude": ",".join(f"{p[1]:.4f}" for p in chunk)})
                heights += d["elevation"]
            with open(terrain_path, "w") as f:
                json.dump({"lat": lat, "lon": lon, "step_deg": GRID_STEP_DEG,
                           "half_steps": GRID_HALF_STEPS, "elevation": heights}, f)
            print(f"    terrain: centre {heights[len(heights) // 2]} m")
            time.sleep(2)

    print("Done. Files are in", OUT_DIR)


if __name__ == "__main__":
    sys.exit(main())
