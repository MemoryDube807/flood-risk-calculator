"""
FloodSense Zambia API.

    pip install -r requirements.txt
    python app.py

Endpoints
    GET /                       short usage note
    GET /api/places             preset places and coordinates
    GET /api/assess?place=Lusaka
    GET /api/assess?lat=-15.86&lon=27.75&drainage=poor
"""

import os

from flask import Flask, jsonify, request

from floodsense import data, places, scoring

app = Flask(__name__)


@app.get("/")
def index():
    return jsonify({
        "service": "FloodSense Zambia",
        "usage": "/api/assess?place=Lusaka or /api/assess?lat=-15.86&lon=27.75&drainage=poor",
        "drainage": list(scoring.DRAINAGE_FACTOR),
        "places": "/api/places",
    })


@app.get("/api/places")
def list_places():
    return jsonify([{"name": k, "lat": v[0], "lon": v[1]} for k, v in places.PLACES.items()])


@app.get("/api/assess")
def assess():
    drainage = request.args.get("drainage", "moderate")
    if drainage not in scoring.DRAINAGE_FACTOR:
        return jsonify({"error": f"drainage must be one of {list(scoring.DRAINAGE_FACTOR)}"}), 400
    try:
        if "place" in request.args:
            name, (lat, lon) = places.find(request.args["place"])
        else:
            lat, lon = float(request.args["lat"]), float(request.args["lon"])
            name = f"{lat:.3f}, {lon:.3f}"
    except (KeyError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    if not (-18.5 <= lat <= -8.0 and 21.5 <= lon <= 34.0):
        return jsonify({"error": "the point is outside Zambia"}), 400
    try:
        result = data.assess_point(lat, lon, drainage)
    except Exception as exc:              # upstream data service unavailable
        return jsonify({"error": f"could not fetch data: {exc}"}), 502
    return jsonify({"place": name, **result})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
