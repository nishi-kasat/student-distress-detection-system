"""
solution.py – Behavioral Anomaly & Early Distress Detection
============================================================
Reads Sentio Mind daily JSON files from sample_data/, computes personal
baselines, detects 7 anomaly categories, and writes:
  • alert_feed.json   – machine-readable alert feed
  • alert_digest.html – counsellor-facing report with sparklines

Usage:
    python solution.py [--data-dir sample_data] [--out-dir .]

Python 3.9+ required. No OpenCV / camera dependencies.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
from datetime import date, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASELINE_DAYS = 3          # number of leading days used for personal baseline
SUSTAINED_LOW_THRESHOLD = 45
SUSTAINED_LOW_DAYS = 3
SOCIAL_WITHDRAWAL_DROP = 25
HYPERACTIVITY_DELTA = 40
REGRESSION_RECOVERY_DAYS = 3
REGRESSION_DROP = 15
GAZE_AVOIDANCE_DAYS = 3
ABSENCE_DAYS = 2
HIGH_STD_THRESHOLD = 15
HIGH_STD_MULTIPLIER = 1.5   # increase drop threshold by 50 %

SEVERITY_MAP = {
    "SUDDEN_DROP": "HIGH",
    "SUSTAINED_LOW": "HIGH",
    "SOCIAL_WITHDRAWAL": "MEDIUM",
    "HYPERACTIVITY_SPIKE": "MEDIUM",
    "REGRESSION": "HIGH",
    "GAZE_AVOIDANCE": "MEDIUM",
    "ABSENCE_FLAG": "CRITICAL",
}

# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def load_daily_records(data_dir: str) -> list[dict[str, Any]]:
    """Load and sort all JSON files in *data_dir* by date ascending."""
    records: list[dict[str, Any]] = []
    for fname in os.listdir(data_dir):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(data_dir, fname)
        with open(fpath, "r", encoding="utf-8") as fh:
            record = json.load(fh)
        # ensure date field exists
        if "date" not in record:
            record["date"] = fname.replace(".json", "")
        records.append(record)
    records.sort(key=lambda r: datetime.fromisoformat(r["date"]))
    return records


def safe_float(value: Any, default: float = 0.0) -> float:
    """Return float or *default* when value is None / missing."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Baseline computation
# ---------------------------------------------------------------------------

def compute_baseline(records: list[dict[str, Any]]) -> dict[str, float]:
    """
    Compute personal baseline statistics from the first BASELINE_DAYS
    detected records (or all detected records if fewer are available).
    Returns a dict with mean and std for key metrics.
    """
    detected = [r for r in records if r.get("detected", True)]
    window = detected[:BASELINE_DAYS] if len(detected) >= BASELINE_DAYS else detected

    def mean_of(key: str) -> float:
        vals = [safe_float(r.get(key)) for r in window if r.get(key) is not None]
        return statistics.mean(vals) if vals else 0.0

    def std_of(key: str) -> float:
        vals = [safe_float(r.get(key)) for r in window if r.get(key) is not None]
        return statistics.pstdev(vals) if len(vals) > 1 else 0.0

    wellbeing_vals = [
        safe_float(r.get("wellbeing_score"))
        for r in window
        if r.get("wellbeing_score") is not None
    ]

    baseline = {
        "wellbeing_mean": mean_of("wellbeing_score"),
        "wellbeing_std": std_of("wellbeing_score"),
        "social_mean": mean_of("social_engagement"),
        "energy_mean": mean_of("energy_level"),
        "activity_mean": statistics.mean(
            [safe_float(r.get("movement", {}).get("activity_level")) for r in window
             if r.get("movement", {}).get("activity_level") is not None]
        ) if window else 0.0,
    }

    # Adaptive threshold: if wellbeing std > HIGH_STD_THRESHOLD, relax thresholds
    if baseline["wellbeing_std"] > HIGH_STD_THRESHOLD:
        baseline["drop_threshold_multiplier"] = HIGH_STD_MULTIPLIER
    else:
        baseline["drop_threshold_multiplier"] = 1.0

    return baseline


# ---------------------------------------------------------------------------
# Anomaly detectors  (one function per category)
# ---------------------------------------------------------------------------

def detect_sudden_drop(
    records: list[dict], baseline: dict, idx: int
) -> dict | None:
    """SUDDEN_DROP – wellbeing drops ≥ 20 pts vs baseline in one day."""
    rec = records[idx]
    if not rec.get("detected", True):
        return None
    score = rec.get("wellbeing_score")
    if score is None:
        return None

    threshold = 20 * baseline["drop_threshold_multiplier"]
    drop = baseline["wellbeing_mean"] - safe_float(score)
    if drop >= threshold:
        return _make_alert(
            anomaly_type="SUDDEN_DROP",
            date=rec["date"],
            person_id=rec.get("person_id", "unknown"),
            description=(
                f"Wellbeing dropped {drop:.1f} pts below personal baseline "
                f"(baseline={baseline['wellbeing_mean']:.1f}, today={score})."
            ),
            value=safe_float(score),
            baseline_value=baseline["wellbeing_mean"],
            delta=-drop,
        )
    return None


def detect_sustained_low(
    records: list[dict], baseline: dict, idx: int
) -> dict | None:
    """SUSTAINED_LOW – wellbeing < 45 for ≥ 3 consecutive days ending at idx."""
    if idx < SUSTAINED_LOW_DAYS - 1:
        return None
    window = records[idx - SUSTAINED_LOW_DAYS + 1 : idx + 1]
    for r in window:
        if not r.get("detected", True):
            return None
        score = r.get("wellbeing_score")
        if score is None or safe_float(score) >= SUSTAINED_LOW_THRESHOLD:
            return None
    rec = records[idx]
    avg = statistics.mean(
        safe_float(r["wellbeing_score"]) for r in window
    )
    return _make_alert(
        anomaly_type="SUSTAINED_LOW",
        date=rec["date"],
        person_id=rec.get("person_id", "unknown"),
        description=(
            f"Wellbeing below {SUSTAINED_LOW_THRESHOLD} for "
            f"{SUSTAINED_LOW_DAYS} consecutive days (avg={avg:.1f})."
        ),
        value=avg,
        baseline_value=baseline["wellbeing_mean"],
        delta=avg - baseline["wellbeing_mean"],
    )


def detect_social_withdrawal(
    records: list[dict], baseline: dict, idx: int
) -> dict | None:
    """SOCIAL_WITHDRAWAL – social_engagement down ≥ 25 pts + gaze mostly downward."""
    rec = records[idx]
    if not rec.get("detected", True):
        return None
    social = rec.get("social_engagement")
    gaze_dir = rec.get("gaze", {}).get("direction", "")
    if social is None:
        return None

    drop = baseline["social_mean"] - safe_float(social)
    gaze_down = str(gaze_dir).lower() in ("downward", "down")
    if drop >= SOCIAL_WITHDRAWAL_DROP and gaze_down:
        return _make_alert(
            anomaly_type="SOCIAL_WITHDRAWAL",
            date=rec["date"],
            person_id=rec.get("person_id", "unknown"),
            description=(
                f"Social engagement dropped {drop:.1f} pts vs baseline "
                f"(baseline={baseline['social_mean']:.1f}, today={social}) "
                f"with gaze direction='{gaze_dir}'."
            ),
            value=safe_float(social),
            baseline_value=baseline["social_mean"],
            delta=-drop,
        )
    return None


def detect_hyperactivity_spike(
    records: list[dict], baseline: dict, idx: int
) -> dict | None:
    """HYPERACTIVITY_SPIKE – combined energy traits ≥ 40 pts above baseline."""
    rec = records[idx]
    if not rec.get("detected", True):
        return None
    energy = safe_float(rec.get("energy_level"))
    activity = safe_float(rec.get("movement", {}).get("activity_level"))
    restlessness = safe_float(rec.get("movement", {}).get("restlessness", 0))

    combined_today = (energy + activity + restlessness) / 3
    combined_baseline = (baseline["energy_mean"] + baseline["activity_mean"] + baseline["restlessness_mean"]) / 3
    delta = combined_today - combined_baseline

    if delta >= HYPERACTIVITY_DELTA:
        return _make_alert(
            anomaly_type="HYPERACTIVITY_SPIKE",
            date=rec["date"],
            person_id=rec.get("person_id", "unknown"),
            description=(
                f"Combined energy metrics {delta:.1f} pts above baseline "
                f"(energy={energy}, activity={activity}, restlessness={restlessness})."
            ),
            value=combined_today,
            baseline_value=combined_baseline,
            delta=delta,
        )
    return None


def detect_regression(
    records: list[dict], baseline: dict, idx: int
) -> dict | None:
    """REGRESSION – was recovering 3+ days then drops > 15 pts in one day."""
    if idx < REGRESSION_RECOVERY_DAYS:
        return None
    rec = records[idx]
    if not rec.get("detected", True):
        return None
    today_score = rec.get("wellbeing_score")
    if today_score is None:
        return None

    # check 3 prior days were all increasing
    prior = records[idx - REGRESSION_RECOVERY_DAYS : idx]
    prev_scores = []
    for r in prior:
        if not r.get("detected", True) or r.get("wellbeing_score") is None:
            return None
        prev_scores.append(safe_float(r["wellbeing_score"]))

    # all consecutive pairs must be non-decreasing (recovery)
    recovering = all(prev_scores[i] <= prev_scores[i + 1] for i in range(len(prev_scores) - 1))
    if not recovering:
        return None

    drop = prev_scores[-1] - safe_float(today_score)
    if drop > REGRESSION_DROP:
        return _make_alert(
            anomaly_type="REGRESSION",
            date=rec["date"],
            person_id=rec.get("person_id", "unknown"),
            description=(
                f"Was recovering for {REGRESSION_RECOVERY_DAYS}+ days then dropped "
                f"{drop:.1f} pts in one day (prev={prev_scores[-1]:.1f}, today={today_score})."
            ),
            value=safe_float(today_score),
            baseline_value=prev_scores[-1],
            delta=-drop,
        )
    return None


def detect_gaze_avoidance(
    records: list[dict], baseline: dict, idx: int
) -> dict | None:
    """GAZE_AVOIDANCE – zero eye contact for 3+ consecutive days."""
    if idx < GAZE_AVOIDANCE_DAYS - 1:
        return None
    window = records[idx - GAZE_AVOIDANCE_DAYS + 1 : idx + 1]
    for r in window:
        if not r.get("detected", True):
            return None
        ratio = r.get("gaze", {}).get("eye_contact_ratio")
        if ratio is None or safe_float(ratio) > 0.0:
            return None
    rec = records[idx]
    return _make_alert(
        anomaly_type="GAZE_AVOIDANCE",
        date=rec["date"],
        person_id=rec.get("person_id", "unknown"),
        description=(
            f"Zero eye contact detected for {GAZE_AVOIDANCE_DAYS} consecutive days."
        ),
        value=0.0,
        baseline_value=None,
        delta=None,
    )


def detect_absence_flag(
    records: list[dict], baseline: dict, idx: int
) -> dict | None:
    """ABSENCE_FLAG – person not detected for 2+ consecutive days."""
    if idx < ABSENCE_DAYS - 1:
        return None
    window = records[idx - ABSENCE_DAYS + 1 : idx + 1]
    for r in window:
        if r.get("detected", True):   # True = present
            return None
    rec = records[idx]
    return _make_alert(
        anomaly_type="ABSENCE_FLAG",
        date=rec["date"],
        person_id=rec.get("person_id", "unknown"),
        description=(
            f"Person not detected for {ABSENCE_DAYS} consecutive days — welfare check needed."
        ),
        value=0,
        baseline_value=None,
        delta=None,
    )


# ---------------------------------------------------------------------------
# Alert builder
# ---------------------------------------------------------------------------

def _make_alert(
    *,
    anomaly_type: str,
    date: str,
    person_id: str,
    description: str,
    value: float | None,
    baseline_value: float | None,
    delta: float | None,
) -> dict:
    return {
        "alert_id": f"{person_id}_{date}_{anomaly_type}",
        "anomaly_type": anomaly_type,
        "severity": SEVERITY_MAP.get(anomaly_type, "MEDIUM"),
        "date": date,
        "person_id": person_id,
        "description": description,
        "value": round(value, 2) if value is not None else None,
        "baseline_value": round(baseline_value, 2) if baseline_value is not None else None,
        "delta": round(delta, 2) if delta is not None else None,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


# ---------------------------------------------------------------------------
# Main detection runner
# ---------------------------------------------------------------------------

DETECTORS = [
    detect_sudden_drop,
    detect_sustained_low,
    detect_social_withdrawal,
    detect_hyperactivity_spike,
    detect_regression,
    detect_gaze_avoidance,
    detect_absence_flag,
]


def run_detection(records: list[dict]) -> tuple[dict, list[dict]]:
    """Run all detectors across all records. Returns (baseline, alerts)."""
    baseline = compute_baseline(records)
    alerts: list[dict] = []
    seen_ids: set[str] = set()

    for idx in range(len(records)):
        for detector in DETECTORS:
            alert = detector(records, baseline, idx)
            if alert and alert["alert_id"] not in seen_ids:
                alerts.append(alert)
                seen_ids.add(alert["alert_id"])

    return baseline, alerts


# ---------------------------------------------------------------------------
# alert_feed.json writer
# ---------------------------------------------------------------------------

def write_alert_feed(alerts: list[dict], out_path: str) -> None:
    """Write machine-readable alert_feed.json."""
    feed = {
        "schema_version": "1.0",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_alerts": len(alerts),
        "alerts": alerts,
    }
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(feed, fh, indent=2)
    print(f"[✓] alert_feed.json written → {out_path}")


# ---------------------------------------------------------------------------
# alert_digest.html writer  (offline, no CDN)
# ---------------------------------------------------------------------------

SEVERITY_COLOR = {
    "CRITICAL": ("#7f1d1d", "#fee2e2"),
    "HIGH":     ("#78350f", "#fef3c7"),
    "MEDIUM":   ("#1e3a5f", "#dbeafe"),
    "LOW":      ("#14532d", "#dcfce7"),
}

SEVERITY_BADGE = {
    "CRITICAL": "#dc2626",
    "HIGH":     "#f59e0b",
    "MEDIUM":   "#3b82f6",
    "LOW":      "#22c55e",
}


def _sparkline_svg(values: list[float | None], width: int = 120, height: int = 32) -> str:
    """Return an inline SVG sparkline for a list of numeric values."""
    clean = [v for v in values if v is not None]
    if len(clean) < 2:
        return "<span style='color:#aaa'>—</span>"

    mn, mx = min(clean), max(clean)
    rng = mx - mn if mx != mn else 1

    pts: list[str] = []
    xi = 0
    for i, v in enumerate(values):
        if v is None:
            continue
        x = int(xi * (width - 4) / (len(clean) - 1)) + 2
        y = int(height - 2 - ((v - mn) / rng) * (height - 4))
        pts.append(f"{x},{y}")
        xi += 1

    path = " ".join(pts)
    last_color = "#22c55e" if clean[-1] >= clean[0] else "#ef4444"
    lx, ly = pts[-1].split(",")

    return (
        f'<svg width="{width}" height="{height}" style="vertical-align:middle" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f'<polyline points="{path}" fill="none" stroke="#94a3b8" stroke-width="1.5"/>'
        f'<circle cx="{lx}" cy="{ly}" r="3" fill="{last_color}"/>'
        f"</svg>"
    )


def write_alert_digest(
    records: list[dict],
    baseline: dict,
    alerts: list[dict],
    out_path: str,
) -> None:
    """Write counsellor-facing alert_digest.html with sparklines."""

    # Build time-series for sparklines
    dates = [r["date"] for r in records]
    wellbeing_series = [r.get("wellbeing_score") for r in records]
    social_series = [r.get("social_engagement") for r in records]
    energy_series = [r.get("energy_level") for r in records]

    wellbeing_spark = _sparkline_svg(wellbeing_series, width=160, height=36)
    social_spark = _sparkline_svg(social_series, width=160, height=36)
    energy_spark = _sparkline_svg(energy_series, width=160, height=36)

    # Person info
    detected_recs = [r for r in records if r.get("detected", True)]
    person_id = records[0].get("person_id", "unknown") if records else "unknown"
    date_range = f"{records[0]['date']} → {records[-1]['date']}" if records else "—"
    total_days = len(records)
    absent_days = sum(1 for r in records if not r.get("detected", True))

    # Alert rows
    alert_rows_html = ""
    if not alerts:
        alert_rows_html = (
            "<tr><td colspan='6' style='text-align:center;color:#64748b;padding:24px'>"
            "No anomalies detected.</td></tr>"
        )
    else:
        for a in sorted(alerts, key=lambda x: x["date"]):
            sev = a["severity"]
            badge_color = SEVERITY_BADGE.get(sev, "#94a3b8")
            text_color, bg_color = SEVERITY_COLOR.get(sev, ("#000", "#fff"))
            delta_str = (
                f"{a['delta']:+.1f}" if a.get("delta") is not None else "—"
            )
            value_str = f"{a['value']:.1f}" if a.get("value") is not None else "—"
            baseline_str = (
                f"{a['baseline_value']:.1f}"
                if a.get("baseline_value") is not None
                else "—"
            )
            alert_rows_html += f"""
            <tr style="background:{bg_color}">
              <td style="color:{text_color};font-weight:600">{a['date']}</td>
              <td>
                <span style="background:{badge_color};color:#fff;padding:2px 8px;
                  border-radius:12px;font-size:11px;font-weight:700">{sev}</span>
              </td>
              <td style="font-weight:600;color:{text_color}">{a['anomaly_type']}</td>
              <td style="color:#334155;font-size:13px">{a['description']}</td>
              <td style="text-align:center">{value_str}</td>
              <td style="text-align:center;font-weight:700;color:{'#ef4444' if '-' in delta_str else '#22c55e'}">{delta_str}</td>
            </tr>"""

    # Metric card helper
    def metric_card(label: str, spark: str, val: str, sub: str = "") -> str:
        return f"""
        <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;
          padding:16px 20px;min-width:200px;flex:1">
          <div style="font-size:12px;color:#64748b;font-weight:600;text-transform:uppercase;
            letter-spacing:.5px">{label}</div>
          <div style="margin:8px 0">{spark}</div>
          <div style="font-size:22px;font-weight:700;color:#1e293b">{val}</div>
          {f'<div style="font-size:12px;color:#64748b">{sub}</div>' if sub else ''}
        </div>"""

    last_wb = wellbeing_series[-1] if wellbeing_series and wellbeing_series[-1] is not None else "—"
    last_se = social_series[-1] if social_series and social_series[-1] is not None else "—"
    last_en = energy_series[-1] if energy_series and energy_series[-1] is not None else "—"

    # Summary counts per severity
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for a in alerts:
        counts[a.get("severity", "LOW")] = counts.get(a.get("severity", "LOW"), 0) + 1

    def summary_pill(sev: str) -> str:
        c = SEVERITY_BADGE[sev]
        return (
            f'<span style="background:{c};color:#fff;padding:4px 14px;'
            f'border-radius:20px;font-size:13px;font-weight:700;margin-right:6px">'
            f'{counts[sev]} {sev}</span>'
        )

    generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Sentio Mind – Alert Digest</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #f8fafc;
    color: #1e293b;
    padding: 32px 24px;
    line-height: 1.5;
  }}
  h1 {{ font-size: 24px; font-weight: 800; }}
  h2 {{ font-size: 16px; font-weight: 700; color: #475569; margin-bottom: 14px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{
    background: #1e293b; color: #f1f5f9; text-align: left;
    padding: 10px 12px; font-size: 12px; font-weight: 700;
    text-transform: uppercase; letter-spacing: .5px;
  }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #e2e8f0; font-size: 13px; vertical-align: top; }}
  tr:hover td {{ filter: brightness(0.97); }}
  .card-row {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 28px; }}
  .section {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 14px;
    padding: 24px; margin-bottom: 28px; }}
  .header-bar {{
    display: flex; align-items: center; justify-content: space-between;
    background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%);
    color: #fff; border-radius: 14px; padding: 24px 28px; margin-bottom: 28px;
  }}
  .logo {{ font-size: 22px; font-weight: 800; letter-spacing: -0.5px; }}
  .logo span {{ color: #38bdf8; }}
  .meta {{ font-size: 13px; color: #94a3b8; margin-top: 4px; }}
  .baseline-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 12px; }}
  .baseline-item {{ background: #f1f5f9; border-radius: 8px; padding: 12px 16px; }}
  .baseline-label {{ font-size: 11px; color: #64748b; font-weight: 600;
    text-transform: uppercase; letter-spacing: .5px; }}
  .baseline-val {{ font-size: 20px; font-weight: 700; color: #1e293b; }}
  @media (max-width: 640px) {{
    .header-bar {{ flex-direction: column; align-items: flex-start; gap: 8px; }}
  }}
</style>
</head>
<body>

<!-- Header -->
<div class="header-bar">
  <div>
    <div class="logo">Sentio<span>Mind</span></div>
    <div class="meta">Behavioral Anomaly &amp; Early Distress Detection — Counsellor Report</div>
  </div>
  <div style="text-align:right">
    <div style="font-size:13px;color:#94a3b8">Generated</div>
    <div style="font-weight:700">{generated_at}</div>
  </div>
</div>

<!-- Student summary -->
<div class="section">
  <h2>Student Overview</h2>
  <div style="display:flex;flex-wrap:wrap;gap:24px;margin-bottom:18px">
    <div><div style="font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase">Person ID</div>
         <div style="font-weight:700;font-size:15px">{person_id}</div></div>
    <div><div style="font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase">Analysis Period</div>
         <div style="font-weight:700;font-size:15px">{date_range}</div></div>
    <div><div style="font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase">Days Analysed</div>
         <div style="font-weight:700;font-size:15px">{total_days}</div></div>
    <div><div style="font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase">Absent Days</div>
         <div style="font-weight:700;font-size:15px;color:{'#dc2626' if absent_days>0 else '#22c55e'}">{absent_days}</div></div>
    <div><div style="font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase">Total Alerts</div>
         <div style="font-weight:700;font-size:15px;color:{'#dc2626' if alerts else '#22c55e'}">{len(alerts)}</div></div>
  </div>
  <div>{summary_pill('CRITICAL')}{summary_pill('HIGH')}{summary_pill('MEDIUM')}{summary_pill('LOW')}</div>
</div>

<!-- Metric sparklines -->
<div class="card-row">
  {metric_card("Wellbeing Score", wellbeing_spark, str(last_wb), f"baseline={baseline['wellbeing_mean']:.1f}")}
  {metric_card("Social Engagement", social_spark, str(last_se), f"baseline={baseline['social_mean']:.1f}")}
  {metric_card("Energy Level", energy_spark, str(last_en), f"baseline={baseline['energy_mean']:.1f}")}
</div>

<!-- Baseline -->
<div class="section">
  <h2>Personal Baseline (first {BASELINE_DAYS} days)</h2>
  <div class="baseline-grid">
    <div class="baseline-item">
      <div class="baseline-label">Wellbeing Mean</div>
      <div class="baseline-val">{baseline['wellbeing_mean']:.1f}</div>
    </div>
    <div class="baseline-item">
      <div class="baseline-label">Wellbeing Std Dev</div>
      <div class="baseline-val">{baseline['wellbeing_std']:.1f}</div>
    </div>
    <div class="baseline-item">
      <div class="baseline-label">Social Mean</div>
      <div class="baseline-val">{baseline['social_mean']:.1f}</div>
    </div>
    <div class="baseline-item">
      <div class="baseline-label">Energy Mean</div>
      <div class="baseline-val">{baseline['energy_mean']:.1f}</div>
    </div>
    <div class="baseline-item">
      <div class="baseline-label">Threshold Multiplier</div>
      <div class="baseline-val">{baseline['drop_threshold_multiplier']:.1f}×</div>
    </div>
  </div>
</div>

<!-- Alert table -->
<div class="section">
  <h2>Detected Anomalies</h2>
  <div style="overflow-x:auto">
    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Severity</th>
          <th>Anomaly Type</th>
          <th>Description</th>
          <th>Value</th>
          <th>Δ Baseline</th>
        </tr>
      </thead>
      <tbody>
        {alert_rows_html}
      </tbody>
    </table>
  </div>
</div>

<!-- Daily timeline -->
<div class="section">
  <h2>Daily Wellbeing Timeline</h2>
  <div style="overflow-x:auto">
    <table>
      <thead>
        <tr>
          <th>Date</th><th>Present</th><th>Wellbeing</th>
          <th>Social</th><th>Energy</th><th>Eye Contact</th><th>Gaze</th>
        </tr>
      </thead>
      <tbody>
        {''.join(_timeline_row(r, baseline) for r in records)}
      </tbody>
    </table>
  </div>
</div>

<div style="text-align:center;color:#94a3b8;font-size:12px;margin-top:32px">
  SentioMind Anomaly Detection v1.0 — Confidential Counsellor Report — {generated_at}
</div>
</body>
</html>"""

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"[✓] alert_digest.html written → {out_path}")


def _timeline_row(rec: dict, baseline: dict) -> str:
    """Return an HTML <tr> for one daily record."""
    present = rec.get("detected", True)
    wb = rec.get("wellbeing_score")
    se = rec.get("social_engagement")
    en = rec.get("energy_level")
    eye = rec.get("gaze", {}).get("eye_contact_ratio")
    gaze_dir = rec.get("gaze", {}).get("direction", "—")

    def fmt(v: Any) -> str:
        return f"{v:.0f}" if v is not None else "—"

    def color_val(v: float | None, thr_low: float = 45, thr_high: float = 60) -> str:
        if v is None:
            return "color:#94a3b8"
        if v < thr_low:
            return "color:#dc2626;font-weight:700"
        if v < thr_high:
            return "color:#f59e0b;font-weight:600"
        return "color:#16a34a"

    present_badge = (
        '<span style="color:#16a34a;font-weight:700">✓</span>'
        if present
        else '<span style="color:#dc2626;font-weight:700">✗ ABSENT</span>'
    )
    eye_str = f"{eye:.0%}" if eye is not None else "—"

    return f"""
    <tr>
      <td style="font-weight:600">{rec['date']}</td>
      <td>{present_badge}</td>
      <td style="{color_val(wb)}">{fmt(wb)}</td>
      <td style="{color_val(se)}">{fmt(se)}</td>
      <td style="{color_val(en)}">{fmt(en)}</td>
      <td style="{'color:#dc2626;font-weight:700' if eye == 0 else ''}">{eye_str}</td>
      <td>{gaze_dir or '—'}</td>
    </tr>"""


# ---------------------------------------------------------------------------
# Flask endpoint stub
# ---------------------------------------------------------------------------

def get_alerts_endpoint(data_dir: str = "sample_data") -> dict:
    """
    /get_alerts  –  Flask-compatible handler.
    Returns the full alert feed dict (JSON-serialisable).
    """
    records = load_daily_records(data_dir)
    _, alerts = run_detection(records)
    return {
        "schema_version": "1.0",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_alerts": len(alerts),
        "alerts": alerts,
    }


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sentio Mind – Behavioral Anomaly Detection"
    )
    parser.add_argument(
        "--data-dir",
        default="sample_data",
        help="Folder containing daily JSON files (default: sample_data)",
    )
    parser.add_argument(
        "--out-dir",
        default=".",
        help="Output directory for alert_feed.json and alert_digest.html",
    )
    args = parser.parse_args()

    print(f"[→] Loading records from: {args.data_dir}")
    records = load_daily_records(args.data_dir)
    print(f"    {len(records)} daily records loaded.")

    print("[→] Computing baseline and running anomaly detection …")
    baseline, alerts = run_detection(records)
    print(f"    Baseline: wellbeing_mean={baseline['wellbeing_mean']:.1f}, "
          f"std={baseline['wellbeing_std']:.1f}, "
          f"multiplier={baseline['drop_threshold_multiplier']:.1f}×")
    print(f"    Alerts detected: {len(alerts)}")
    for a in alerts:
        print(f"      [{a['severity']:8s}] {a['date']}  {a['anomaly_type']}")

    os.makedirs(args.out_dir, exist_ok=True)
    feed_path = os.path.join(args.out_dir, "alert_feed.json")
    html_path = os.path.join(args.out_dir, "alert_digest.html")

    write_alert_feed(alerts, feed_path)
    write_alert_digest(records, baseline, alerts, html_path)

    print("\n[✓] Done.")


if __name__ == "__main__":
    main()