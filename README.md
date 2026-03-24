# 🧠 Student Distress Detection System

A rule-based anomaly detection system that analyzes daily behavioral data and generates proactive alerts for early distress detection.

This project simulates how educational institutions or wellbeing platforms can monitor student behavioral patterns and identify signs of distress before they escalate.

---

## 🚀 Overview

In many systems, behavioral data is collected but not actively used to trigger timely interventions.
This project focuses on building an **alert layer** that detects significant deviations from a student's normal behavior.

The system:

* Builds a **personal baseline** from historical data
* Detects abnormal behavioral patterns
* Generates structured alerts for further action
* Produces both **machine-readable** and **human-friendly** outputs

---

## ✨ Key Features

* 📊 Detects **7 types of behavioral anomalies**
* 🧠 Personal baseline computation (adaptive to each individual)
* ⚠️ Early distress detection using rule-based logic
* 📁 JSON alert feed for backend/API integration
* 🌐 Offline HTML dashboard for counsellor review
* 🧩 Handles missing data and absence patterns
* ⚙️ Built using **pure Python (no external dependencies)**

---

## 🛠️ Tech Stack

* Python 3.9+
* JSON processing
* Statistics (mean, standard deviation)
* HTML (offline report generation)

---

## 🧪 Simulated Data Scenario

The dataset is intentionally designed to simulate realistic behavioral transitions:

* **Day 1–3:** Stable baseline (healthy behavior)
* **Day 4:** Sudden drop in wellbeing
* **Day 5–6:** Sustained low engagement and distress
* **Day 7–8:** Absence detection (student not present)

This allows the system to validate anomaly detection across multiple edge cases.

---

## 🚨 Anomaly Types Detected

| Type                | Description                                  |
| ------------------- | -------------------------------------------- |
| SUDDEN_DROP         | Sharp drop in wellbeing compared to baseline |
| SUSTAINED_LOW       | Low wellbeing for consecutive days           |
| SOCIAL_WITHDRAWAL   | Reduced social engagement + downward gaze    |
| HYPERACTIVITY_SPIKE | Sudden increase in energy/activity levels    |
| REGRESSION          | Drop after a recovery trend                  |
| GAZE_AVOIDANCE      | No eye contact over multiple days            |
| ABSENCE_FLAG        | Student absent for consecutive days          |

---

## 📂 Project Structure

```
student-distress-detection-system/
│
├── solution.py
├── generate_sample_data.py
├── sample_data/
├── alert_feed.json
├── alert_digest.html
├── README.md
```

---

## ▶️ How to Run

### 1. Generate sample data

```bash
python generate_sample_data.py
```

### 2. Run anomaly detection

```bash
python solution.py
```

---

## 📤 Outputs

### alert_feed.json

* Machine-readable alert data
* Can be integrated into APIs or dashboards

### alert_digest.html

* Offline report for human review
* Includes summaries, trends, and anomaly highlights

---

## 🔌 Potential Applications

* Student wellbeing monitoring systems
* Workplace mental health tracking
* Behavioral analytics platforms
* Early warning systems in education tech

---

## 💡 Future Improvements

* Replace rule-based system with ML-based anomaly detection
* Real-time streaming data processing
* REST API deployment (Flask/FastAPI)
* Multi-user support and dashboards

---

## 📌 Notes

This project focuses purely on **behavioral signal analysis and alert generation**, without involving any computer vision or video processing.

---
