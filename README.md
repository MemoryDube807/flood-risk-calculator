# FloodSense Action — Flood Risk Calculator

A Python-based flood risk assessment tool with a CLI interface and a Flask web dashboard. Built as a prototype component for the **FloodSense Action** platform — an open-data flood risk intelligence and early-warning system for Eastern and Southern Africa.

---

## What It Does

Takes four inputs about a location:

| Input | Description |
|---|---|
| Rainfall (mm) | Total rainfall in the last 48 hours |
| Elevation (m) | Height above sea level |
| Drainage quality | Poor / Moderate / Good |
| Soil type | Clay / Loam / Sandy |

Outputs a **risk score (0–100)**, a **risk level** (Low / Moderate / High), and a plain-language **action advisory** — e.g.:

> *"IMMEDIATE ACTION REQUIRED. Move crops, fertiliser, tools, and livestock to higher ground today."*

---

## Risk Scoring Model

| Factor | Weight | Rationale |
|---|---|---|
| Rainfall (48hr) | 40% | Primary short-term flood trigger |
| Elevation | 30% | Structural geographical vulnerability |
| Drainage quality | 20% | How fast water moves away |
| Soil type | 10% | Ground absorption capacity |

**Thresholds:**
- 🟢 **LOW** — 0 to 34
- 🟠 **MODERATE** — 35 to 64
- 🔴 **HIGH** — 65 to 100

---

## Project Structure

```
flood-risk-calculator/
│
├── flood_engine.py      # Core risk scoring logic (no dependencies)
├── app.py               # Flask web application
├── requirements.txt     # Python dependencies
│
└── templates/
    └── index.html       # Web dashboard UI
```

---

## Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/flood-risk-calculator.git
cd flood-risk-calculator
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3a. Run the CLI

```bash
python flood_engine.py
```

Example session:
```
Location name: Kitwe, Zambia
Rainfall in last 48 hrs (mm): 92
Elevation above sea level (metres): 12
Drainage quality [poor/moderate/good]: poor
Soil type [clay/loam/sandy]: clay

══════════════════════════════════════════════════════
  FLOOD RISK ASSESSMENT — KITWE, ZAMBIA
══════════════════════════════════════════════════════

  Risk Level  :  🔴  HIGH
  Risk Score  :  82.0 / 100

  Score breakdown:
    rainfall      36.8 pts  ████████████████████
    elevation     24.0 pts  ████████████
    drainage      20.0 pts  ██████████
    soil          10.0 pts  █████
```

### 3b. Run the web dashboard

```bash
python app.py
```

Open **http://localhost:5000** in your browser.

---

## Use Cases

- Smallholder farmers assessing local flood risk before a weather event
- Agricultural extension workers advising communities
- Disaster management officers prioritising response areas
- Demonstration of the FloodSense Action platform concept

---

## Part of FloodSense Action

This calculator is one component of the larger **FloodSense Action** platform — a proposed open-data flood risk intelligence system for Eastern and Southern Africa, designed to deliver action-based early warnings via web dashboard and SMS/USSD to communities with basic phones and limited internet access.

---

## Built With

- Python 3.x (core engine — zero external dependencies)
- Flask (web interface)
- Jinja2 (HTML templating)

---

## Authors

Team WorldChangers — Copperbelt University, Zambia  
*4th UbuntuNet Alliance Women Hackathon 2026*

---

## License

MIT — free to use, adapt, and build on.
