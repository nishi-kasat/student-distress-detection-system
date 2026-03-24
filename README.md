# FreeMinds — Behavioral Anomaly & Early Distress Detection

> **POC Assignment** — adds the alert layer on top of existing FreeMinds daily JSON output.  
> No new video processing. No OpenCV. No camera experience needed.

---

## Problem Statement

FreeMinds already produces daily wellbeing scores and charts for each student.  
The missing piece: **proactive alerts** — a student could show distress for days before anyone notices.

This project:
1. Reads historical daily JSON files produced by the existing FreeMinds pipeline.
2. Builds a **personal baseline** from the first 3 days of data.
3. Detects **7 anomaly categories** using rule-based logic.
4. Writes:
   - `alert_feed.json` — machine-readable feed consumed by the `/get_alerts` Flask endpoint.
   - `alert_digest.html` — offline counsellor report with sparklines and a daily timeline table.

---

## Repository Structure

```
Senito-poc-anomaly-detection/
│
├── solution.py                 # Main detection script (single file, no notebooks)
├── generate_sample_data.py     # Helper — creates sample_data/ with 8 synthetic days
│
├── sample_data/                # Input: one JSON file per day
│   ├── 2025-01-13.json
│   ├── 2025-01-14.json
│   └── ...
│
├── alert_feed.json             # Output: machine-readable alert feed
├── alert_digest.html           # Output: counsellor HTML report (offline)
│
└── README.md
```

---

## Quick Start

### 1 — Install dependencies
```bash
pip install -r requirements.txt   # only stdlib used; no extra packages required
```
> `solution.py` uses **Python standard library only** (`json`, `statistics`, `argparse`, `os`, `datetime`, `math`).  
> No pip packages are needed to run the detection script.

### 2 — Generate sample data (first time)
```bash
python generate_sample_data.py
```
This creates `sample_data/` with 8 pre-configured days that trigger all anomaly types.

### 3 — Run anomaly detection
```bash
python solution.py
# or with custom paths:
python solution.py --data-dir sample_data --out-dir .
```

### 4 — View outputs
- Open `alert_digest.html` in any browser (works fully offline — no CDN).
- Inspect `alert_feed.json` or pipe it to the Flask endpoint.

---

## Input Format

Each file in `sample_data/` follows the existing FreeMinds JSON schema:

```json
{
  "date": "2025-01-16",
  "person_id": "student_001",
  "detected": true,
  "wellbeing_score": 42,
  "social_engagement": 38,
  "energy_level": 35,
  "focus_score": 30,
  "gaze": {
    "eye_contact_ratio": 0.10,
    "direction": "downward"
  },
  "emotions": {
    "happy": 0.10,
    "neutral": 0.20,
    "sad": 0.50,
    "anxious": 0.20
  },
  "movement": {
    "activity_level": 30,
    "restlessness": 40
  }
}
```

`detected: false` means the person was not present that day (absence detection).

---

## Output Format

### alert_feed.json
```json
{
  "schema_version": "1.0",
  "generated_at": "2025-01-20T10:00:00Z",
  "total_alerts": 8,
  "alerts": [
    {
      "alert_id": "student_001_2025-01-16_SUDDEN_DROP",
      "anomaly_type": "SUDDEN_DROP",
      "severity": "HIGH",
      "date": "2025-01-16",
      "person_id": "student_001",
      "description": "Wellbeing dropped 30.3 pts below personal baseline ...",
      "value": 42.0,
      "baseline_value": 72.3,
      "delta": -30.3,
      "generated_at": "2025-01-20T10:00:00Z"
    }
  ]
}
```

### alert_digest.html
Offline single-file HTML report containing:
- Student overview card (person ID, date range, absent days, alert counts by severity)
- Metric cards with SVG sparklines for wellbeing, social engagement, and energy
- Personal baseline statistics panel
- Full anomaly alert table (date, severity badge, type, description, value, Δ baseline)
- Daily timeline table with colour-coded values

---

## 7 Anomaly Categories

| # | Type | Rule | Severity |
|---|------|------|----------|
| 1 | `SUDDEN_DROP` | Wellbeing drops ≥ 20 pts vs personal baseline in one day | HIGH |
| 2 | `SUSTAINED_LOW` | Wellbeing < 45 for ≥ 3 consecutive days | HIGH |
| 3 | `SOCIAL_WITHDRAWAL` | Social engagement down ≥ 25 pts **and** gaze is downward | MEDIUM |
| 4 | `HYPERACTIVITY_SPIKE` | Combined energy metrics ≥ 40 pts above baseline | MEDIUM |
| 5 | `REGRESSION` | Was recovering 3+ days, then drops > 15 pts in one day | HIGH |
| 6 | `GAZE_AVOIDANCE` | Zero eye contact detected for 3+ consecutive days | MEDIUM |
| 7 | `ABSENCE_FLAG` | Person not detected for 2+ consecutive days | CRITICAL |

---

## Baseline Computation

- **Window:** first 3 detected days (or all data if fewer available).
- **Metrics:** `wellbeing_mean`, `wellbeing_std`, `social_mean`, `energy_mean`, `activity_mean`.
- **Adaptive threshold:** if `wellbeing_std > 15`, the drop threshold is multiplied by **1.5×** to reduce false positives on volatile baselines.

---

## Flask Integration

`solution.py` exposes a `get_alerts_endpoint()` function that returns a JSON-serialisable dict.  
Wire it to Flask with zero changes to the existing analysis pipeline:

```python
# app.py  (existing FreeMinds Flask app — add these lines only)
from solution import get_alerts_endpoint
from flask import jsonify

@app.route("/get_alerts")
def get_alerts():
    return jsonify(get_alerts_endpoint(data_dir="sample_data"))
```

---

## Design Decisions

| Decision | Reason |
|----------|--------|
| Standard library only | No extra install step; runs anywhere with Python 3.9+ |
| Single `solution.py` file | Matches deliverable spec; easy to review |
| SVG sparklines inline in HTML | No CDN; fully offline |
| `alert_id` = `person_id + date + type` | Idempotent — re-running never duplicates alerts |
| Adaptive threshold multiplier | Prevents alert fatigue for naturally variable students |

---

## Branch Naming

Push your work to a branch named:
```
FirstName_LastName_RollNumber
```

---

## Deliverables Checklist

- [x] `solution.py` — anomaly detection script
- [x] `alert_digest.html` — counsellor report with sparklines (offline)
- [x] `alert_feed.json` — machine-readable alert feed
- [ ] `demo.mp4` — screen recording (< 2 min) *(record separately)*

---

