"""
FloodSense Action — Flood Risk Engine
======================================
Core risk scoring and advisory logic.
No external dependencies — pure Python.

Usage (CLI):
    python flood_engine.py

Usage (as module):
    from flood_engine import assess_flood_risk
    result = assess_flood_risk(rainfall_mm=90, elevation_m=5, drainage="poor", soil="clay")
"""

# ── Risk factor weights (must sum to 100) ────────────────────────────────────
WEIGHTS = {
    "rainfall":  40,   # Most critical short-term trigger
    "elevation": 30,   # Structural/geographical vulnerability
    "drainage":  20,   # How fast water moves away
    "soil":      10,   # Absorption capacity
}

# ── Scoring tables ────────────────────────────────────────────────────────────
def score_rainfall(mm: float) -> int:
    """Score rainfall in mm over 48 hours (0–100)."""
    if mm < 20:   return 5
    if mm < 40:   return 20
    if mm < 60:   return 40
    if mm < 80:   return 60
    if mm < 100:  return 80
    return 100

def score_elevation(metres: float) -> int:
    """Score elevation in metres (0–100). Lower ground = higher flood risk."""
    if metres < 5:    return 100
    if metres < 15:   return 80
    if metres < 30:   return 60
    if metres < 60:   return 35
    if metres < 100:  return 15
    return 5

DRAINAGE_SCORES = {
    "poor":     100,
    "moderate": 55,
    "good":     15,
}

SOIL_SCORES = {
    "clay":   100,   # Absorbs least, runoff highest
    "loam":   50,
    "sandy":  15,    # Absorbs most
}

# ── Risk classification ───────────────────────────────────────────────────────
def classify_risk(score: float) -> dict:
    if score >= 65:
        return {
            "level": "HIGH",
            "colour": "red",
            "emoji": "🔴",
            "advisory": (
                "IMMEDIATE ACTION REQUIRED. Move crops, fertiliser, tools, "
                "and livestock to higher ground today. Do not wait for water "
                "to appear. Alert neighbours and local authorities."
            ),
        }
    if score >= 35:
        return {
            "level": "MODERATE",
            "colour": "orange",
            "emoji": "🟠",
            "advisory": (
                "Stay alert. Monitor rainfall closely over the next 24–48 hours. "
                "Prepare to move valuables to higher ground quickly if conditions worsen. "
                "Clear drainage channels around your property now."
            ),
        }
    return {
        "level": "LOW",
        "colour": "green",
        "emoji": "🟢",
        "advisory": (
            "Conditions are currently stable. Continue to monitor local weather updates. "
            "Maintain drainage around your property as a precaution."
        ),
    }

# ── Main assessment function ──────────────────────────────────────────────────
def assess_flood_risk(
    rainfall_mm: float,
    elevation_m: float,
    drainage: str,
    soil: str,
    location: str = "Your area",
) -> dict:
    """
    Assess flood risk for a given location.

    Parameters
    ----------
    rainfall_mm : float  — Rainfall in mm over last 48 hours
    elevation_m : float  — Elevation in metres. Lower ground increases local flood risk.
    drainage    : str    — One of: 'poor', 'moderate', 'good'
    soil        : str    — One of: 'clay', 'loam', 'sandy'
    location    : str    — Human-readable location name

    Returns
    -------
    dict with keys: location, score, level, colour, emoji, advisory, breakdown
    """
    drainage = drainage.lower().strip()
    soil = soil.lower().strip()

    if drainage not in DRAINAGE_SCORES:
        raise ValueError(f"drainage must be one of: {list(DRAINAGE_SCORES)}")
    if soil not in SOIL_SCORES:
        raise ValueError(f"soil must be one of: {list(SOIL_SCORES)}")

    breakdown = {
        "rainfall":  round(score_rainfall(rainfall_mm)  * WEIGHTS["rainfall"]  / 100, 1),
        "elevation": round(score_elevation(elevation_m) * WEIGHTS["elevation"] / 100, 1),
        "drainage":  round(DRAINAGE_SCORES[drainage]    * WEIGHTS["drainage"]  / 100, 1),
        "soil":      round(SOIL_SCORES[soil]            * WEIGHTS["soil"]      / 100, 1),
    }
    total_score = round(sum(breakdown.values()), 1)
    classification = classify_risk(total_score)

    return {
        "location":  location,
        "score":     total_score,
        "breakdown": breakdown,
        **classification,
    }

# ── CLI interface ─────────────────────────────────────────────────────────────
def _prompt_float(prompt, min_val=0, max_val=9999):
    while True:
        try:
            val = float(input(prompt))
            if min_val <= val <= max_val:
                return val
            print(f"  Please enter a value between {min_val} and {max_val}.")
        except ValueError:
            print("  Please enter a number.")

def _prompt_choice(prompt, choices):
    choices_lower = [c.lower() for c in choices]
    while True:
        val = input(prompt).lower().strip()
        if val in choices_lower:
            return val
        print(f"  Please enter one of: {', '.join(choices)}")

def run_cli():
    print("\n" + "═" * 54)
    print("  FloodSense Action — Flood Risk Calculator (CLI)")
    print("═" * 54)

    location  = input("\nLocation name (e.g. Kitwe, Zambia): ").strip() or "Unknown"
    rainfall  = _prompt_float("Rainfall in last 48 hrs (mm, 0–300): ", 0, 300)
    elevation = _prompt_float("Elevation above sea level (metres): ", 0, 5000)
    drainage  = _prompt_choice("Drainage quality [poor / moderate / good]: ", ["poor","moderate","good"])
    soil      = _prompt_choice("Soil type [clay / loam / sandy]: ", ["clay","loam","sandy"])

    result = assess_flood_risk(rainfall, elevation, drainage, soil, location)

    print("\n" + "═" * 54)
    print(f"  FLOOD RISK ASSESSMENT — {result['location'].upper()}")
    print("═" * 54)
    print(f"\n  Risk Level  :  {result['emoji']}  {result['level']}")
    print(f"  Risk Score  :  {result['score']} / 100")
    print(f"\n  Score breakdown:")
    for factor, pts in result["breakdown"].items():
        bar = "█" * int(pts / 2)
        print(f"    {factor:<12} {pts:>5} pts  {bar}")
    print(f"\n  ⚠  Advisory:\n")
    # Word-wrap advisory at 50 chars
    words = result["advisory"].split()
    line = "  "
    for word in words:
        if len(line) + len(word) > 52:
            print(line)
            line = "  " + word + " "
        else:
            line += word + " "
    if line.strip():
        print(line)
    print("\n" + "═" * 54 + "\n")

if __name__ == "__main__":
    run_cli()
