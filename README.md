# FloodSense Zambia

**A 48-hour flood check for any point in Zambia, built on live rainfall, river and terrain data and backtested against 18 documented floods.**

**Live tool, backtest dashboard and write-up:** https://memorydube807.github.io/projects/flood-risk-calculator/

Pick a point and FloodSense pulls the rainfall forecast for today and tomorrow, the last month of rain, the flow of the nearest river and the shape of the land around it. It compares each with that place's own records since 1991, returns LOW, MODERATE or HIGH, and gives practical advice. The same scoring code runs in the browser, on the command line, behind a Flask API and in the backtest.

## Why it was rebuilt

The first version scored four typed-in values (48-hour rainfall, elevation, drainage, soil) with hand-picked weights. Tested against real floods it didn't hold up:

- Elevation was height above sea level, with under 5 m scoring highest. All of Zambia lies above about 330 m, so the factor carrying 30% of the weight scored the minimum everywhere.
- Rainfall used fixed millimetre thresholds, so 60 mm meant the same in dry Lundazi as in wet Samfya, and the same on dry ground as on soaked ground.
- Its HIGH level needed 100 mm in 48 hours plus poor drainage and clay soil. Over the 18 floods below it would have issued HIGH for 3.

## How the score works

| Factor | Question | Reference for the place | Weight |
|---|---|---|---|
| Rain | How big is the 48-hour forecast? | Median yearly maximum 2-day rainfall, 1991 to 2019 (about a 2-year fall) | 50 |
| Ground wetness | How wet were the previous 30 days? (antecedent precipitation index, decay 0.9) | 90th percentile of November to March values | 30 |
| River | How high is the nearest GloFAS river cell? | Median yearly peak flow, 1997 to 2019 | 20 |

Each factor is a ratio to its reference, capped (1.5, 1.5 and 2.0), weighted and scaled to 100. MODERATE starts at 35 and HIGH at 50. Where the river's yearly peak is under 1 m³/s there is no real river at the point, and its share follows ground wetness.

Exposure is applied on top: terrain height relative to the lowest ground within about 1 km (Copernicus 90 m DEM) and the user's drainage answer multiply the score by 0.77 to 1.32. This adjustment is judgement-based and isn't tested by the backtest.

## Backtest

The daily score was rebuilt for 1997 to 2026 at the 12 places in `data/flood_events.csv`, using ERA5 rainfall and GloFAS river flow, and checked against 18 floods documented by OCHA, IFRC, the DMMU, GDACS, the International Charter and news reports.

| Result | Value |
|---|---|
| Floods reaching MODERATE or HIGH | 15 of 18 (all 13 outside Lusaka, 2 of 5 in Lusaka) |
| Floods reaching HIGH | 9 of 18 |
| MODERATE episodes with no recorded flood | 5.2 per place per rainy season |
| HIGH episodes with no recorded flood | 1.9 per place per rainy season |
| Old rule at the same catch rate (poor drainage, clay) | 11.7 MODERATE episodes per season |
| Old rule's HIGH level | 3 of 18 floods |
| Mean rank of flood windows among other rainy-season windows | 0.844 |

The weights were set before the backtest. Ten other combinations, from 40/20/40 to 70/30/0, gave mean ranks between 0.830 and 0.848, so the result doesn't depend on fine-tuning.

The score misses most of Lusaka's urban floods: on three of them the reanalysis shows only 7 to 16 mm over two days. City storms are smaller than the rainfall grid, and blocked or built-over drains flood from rain that would run off elsewhere. Getting Lusaka right needs city rain gauges or radar and a drainage map.

## Use it

```bash
pip install -r requirements.txt

python -m floodsense --place Mazabuka --drainage poor     # command line
python -m floodsense --lat -15.445 --lon 28.245

python app.py                                            # API on http://localhost:5000
# GET /api/assess?place=Lusaka
# GET /api/assess?lat=-15.86&lon=27.75&drainage=poor
# GET /api/places

python scripts/fetch_history.py                          # download the backtest history
python scripts/backtest.py                               # rebuild data/backtest_results.json
pytest                                                   # ten checks on the scoring rules
```

All live data comes from free Open-Meteo APIs with no key.

## Repository structure

```
.
├── floodsense/
│   ├── scoring.py          climate references, hazard score, exposure, levels, advice (no dependencies)
│   ├── data.py             live forecast, climatology, river flow and terrain for a point
│   ├── places.py           preset towns
│   └── __main__.py         command-line tool
├── app.py                  Flask API
├── scripts/
│   ├── fetch_history.py    rainfall, river and terrain history for the backtest places
│   └── backtest.py         daily score 1997 to 2026, old-rule comparison, sensitivity
├── data/
│   ├── flood_events.csv    18 documented floods with dates, places and sources
│   ├── history/            downloaded history, one set of files per place
│   └── backtest_results.json
├── tests/test_scoring.py
├── render.yaml             one-click deploy of the API on Render
└── requirements.txt
```

## Limitations

- Eighteen floods is a small sample; the thresholds are reasonable, not precise.
- The backtest uses reanalysis rainfall; the live tool uses a forecast, which adds forecast error.
- Flood reports are often vague about dates and places, and unreported floods count as false alarms.
- GloFAS models large rivers on a 5 km grid; at several towns the flooding river is a few kilometres from the cell used.
- Dam releases and dam failures are not modelled.
- This is not an official warning service. Follow Zambia Meteorological Department and DMMU alerts.

## Data sources

ERA5 reanalysis (Hersbach et al. 2020) and the Open-Meteo forecast API for rainfall; GloFAS (Harrigan et al. 2020) for river discharge; Copernicus 90 m DEM for terrain; all through [Open-Meteo](https://open-meteo.com). Flood records from OCHA, IFRC DREF reports MDRZM013 and MDRZM019, FloodList, GDACS, the International Charter, Lusaka Times, Open Zambia and WION; full references in `data/flood_events.csv`.

## Author

**Memory Dube**, [portfolio](https://memorydube807.github.io/), [LinkedIn](https://www.linkedin.com/in/memory-d-347bab246/) and [GitHub](https://github.com/MemoryDube807)

## License

MIT
