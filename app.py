"""
FloodSense Action — Flask Web Application
==========================================
Run locally:
    pip install -r requirements.txt
    python app.py

Then open: http://localhost:5000
"""

import os
from flask import Flask, render_template, request, jsonify
from flood_engine import assess_flood_risk

app = Flask(__name__)

# ── Sample regional nodes (used to populate the demo map) ────────────────────
DEMO_NODES = [
    {"location": "Kitwe, Zambia",       "rainfall": 92,  "elevation": 12,  "drainage": "poor",     "soil": "clay"},
    {"location": "Blantyre, Malawi",    "rainfall": 74,  "elevation": 28,  "drainage": "moderate", "soil": "loam"},
    {"location": "Beira, Mozambique",   "rainfall": 110, "elevation": 4,   "drainage": "poor",     "soil": "clay"},
    {"location": "Dar es Salaam, TZ",   "rainfall": 55,  "elevation": 8,   "drainage": "moderate", "soil": "loam"},
    {"location": "Harare, Zimbabwe",    "rainfall": 38,  "elevation": 95,  "drainage": "good",     "soil": "loam"},
]

@app.route("/")
def index():
    # Pre-compute demo results for the dashboard
    demo_results = []
    for node in DEMO_NODES:
        r = assess_flood_risk(
            rainfall_mm=node["rainfall"],
            elevation_m=node["elevation"],
            drainage=node["drainage"],
            soil=node["soil"],
            location=node["location"],
        )
        demo_results.append(r)
    return render_template("index.html", demo_results=demo_results)

@app.route("/assess", methods=["POST"])
def assess():
    """JSON API endpoint — accepts form data, returns risk assessment."""
    try:
        data = request.get_json()
        result = assess_flood_risk(
            rainfall_mm=float(data["rainfall"]),
            elevation_m=float(data["elevation"]),
            drainage=data["drainage"],
            soil=data["soil"],
            location=data.get("location", "Your area"),
        )
        return jsonify({"success": True, "result": result})
    except (KeyError, ValueError) as e:
        return jsonify({"success": False, "error": str(e)}), 400

if __name__ == "__main__":
    print("\n  FloodSense Action is running.")
    print("  Open http://localhost:5000 in your browser.\n")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
