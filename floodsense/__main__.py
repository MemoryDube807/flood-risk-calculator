"""
Command line:

    python -m floodsense --place Lusaka
    python -m floodsense --lat -15.86 --lon 27.75 --drainage poor
"""

import argparse
import sys
import textwrap

from . import data, places, scoring

COLOURS = {"LOW": "\033[32m", "MODERATE": "\033[33m", "HIGH": "\033[31m"}


def main(argv=None):
    p = argparse.ArgumentParser(prog="floodsense", description="48-hour flood hazard for a point in Zambia")
    p.add_argument("--place", help="preset place name, e.g. Lusaka or Mazabuka")
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float)
    p.add_argument("--drainage", choices=list(scoring.DRAINAGE_FACTOR), default="moderate",
                   help="how well the immediate area drains (local knowledge)")
    a = p.parse_args(argv)

    if a.place:
        name, (lat, lon) = places.find(a.place)
    elif a.lat is not None and a.lon is not None:
        name, lat, lon = f"{a.lat:.3f}, {a.lon:.3f}", a.lat, a.lon
    else:
        p.error("give --place or both --lat and --lon")

    print(f"Fetching rainfall, river and terrain data for {name} ...")
    r = data.assess_point(lat, lon, a.drainage)
    i = r["inputs"]
    c, end = COLOURS.get(r["risk_level"], ""), "\033[0m"
    print()
    print(f"  {name}: {c}{r['risk_level']}{end}  (risk {r['risk']} out of 100, hazard {r['score']})")
    print()
    print(f"  Rain, next 48 h      {i['rain_48h']:>6} mm   {r['ratios']['rain']:.2f} x the 2-year 2-day fall ({i['rl2']} mm)")
    print(f"  Ground wetness       {i['antecedent']:>6}      {r['ratios']['wetness']:.2f} x a wet-season high ({i['api90']})")
    if r["has_river"]:
        print(f"  River flow           {i['river_flow']:>6} m3/s {r['ratios']['river']:.2f} x the usual yearly peak ({i['q2']} m3/s)")
    else:
        print("  River flow           no sizeable river at this point")
    print(f"  Terrain              {i['rel_height']:>6} m above the lowest ground within 1 km")
    print(f"  Exposure factor      {r['exposure_factor']:>6}      ({a.drainage} drainage)")
    print()
    print(textwrap.fill(r["advice"], width=72, initial_indent="  ", subsequent_indent="  "))
    print()


if __name__ == "__main__":
    sys.exit(main())
