"""
Live data for one point, from free Open-Meteo services (no API key):

  - rainfall forecast and the last 32 days    api.open-meteo.com/v1/forecast
  - rainfall climatology, 1991 to 2019 (ERA5) archive-api.open-meteo.com/v1/archive
  - river discharge (GloFAS), history and forecast  flood-api.open-meteo.com/v1/flood
  - terrain heights around the point (90 m DEM)     api.open-meteo.com/v1/elevation

Standard library only.
"""

import json
import urllib.parse
import urllib.request
from datetime import date

from . import scoring

TIMEZONE = "Africa/Lusaka"


def _get(url, params, timeout=60):
    with urllib.request.urlopen(url + "?" + urllib.parse.urlencode(params), timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def rain_now(lat, lon):
    """48-hour rainfall (today and tomorrow) and the antecedent index before it."""
    d = _get("https://api.open-meteo.com/v1/forecast", {
        "latitude": lat, "longitude": lon, "daily": "precipitation_sum",
        "past_days": scoring.API_DAYS + 2, "forecast_days": 3, "timezone": TIMEZONE})
    days, rain = d["daily"]["time"], [r or 0.0 for r in d["daily"]["precipitation_sum"]]
    i = days.index(date.today().isoformat()) if date.today().isoformat() in days else len(days) - 3
    return {
        "dates": days, "rain": rain, "today_index": i,
        "rain_48h": rain[i] + rain[i + 1],
        "antecedent": scoring.antecedent_index(rain[:i]),
    }


def climatology(lat, lon):
    d = _get("https://archive-api.open-meteo.com/v1/archive", {
        "latitude": lat, "longitude": lon, "start_date": "1991-01-01", "end_date": "2020-06-30",
        "daily": "precipitation_sum", "timezone": TIMEZONE}, timeout=120)
    clim = scoring.rain_climatology(d["daily"]["time"], [r or 0.0 for r in d["daily"]["precipitation_sum"]])
    f = _get("https://flood-api.open-meteo.com/v1/flood", {
        "latitude": lat, "longitude": lon, "daily": "river_discharge",
        "start_date": "1997-01-01", "end_date": "2020-06-30"}, timeout=120)
    clim.update(scoring.river_climatology(f["daily"]["time"], f["daily"]["river_discharge"]))
    return clim


def river_now(lat, lon):
    f = _get("https://flood-api.open-meteo.com/v1/flood", {
        "latitude": lat, "longitude": lon, "daily": "river_discharge", "past_days": 7, "forecast_days": 7})
    days, q = f["daily"]["time"], f["daily"]["river_discharge"]
    today = date.today().isoformat()
    i = days.index(today) if today in days else 7
    window = [x for x in q[i:i + 2] if x is not None]
    return {"dates": days, "flow": q, "flow_48h": max(window) if window else None}


def terrain(lat, lon, half=5, step=0.002):
    pts = [(lat + i * step, lon + j * step) for i in range(-half, half + 1) for j in range(-half, half + 1)]
    heights = []
    for k in range(0, len(pts), 100):
        chunk = pts[k:k + 100]
        d = _get("https://api.open-meteo.com/v1/elevation", {
            "latitude": ",".join(f"{p[0]:.4f}" for p in chunk),
            "longitude": ",".join(f"{p[1]:.4f}" for p in chunk)})
        heights += d["elevation"]
    return {"elevation": heights[len(heights) // 2], "rel_height": scoring.relative_height(heights, half)}


def assess_point(lat, lon, drainage="moderate"):
    """Everything the live tool shows, for one point."""
    rn, rv, clim, ter = rain_now(lat, lon), river_now(lat, lon), climatology(lat, lon), terrain(lat, lon)
    result = scoring.assess(rn["rain_48h"], rn["antecedent"], rv["flow_48h"], clim,
                            rel_height_m=ter["rel_height"], drainage=drainage)
    return {"lat": lat, "lon": lon, "drainage": drainage, "inputs": {
                "rain_48h": round(rn["rain_48h"], 1), "antecedent": round(rn["antecedent"], 1),
                "river_flow": rv["flow_48h"], **{k: round(v, 2) for k, v in clim.items()}, **ter},
            **result}
