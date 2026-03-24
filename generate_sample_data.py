import json, os, random
from datetime import date, timedelta

random.seed(42)
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "sample_data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

days_data = [
    # day 1 – baseline healthy
    {
        "date": "2025-01-13",
        "person_id": "student_001",
        "detected": True,
        "wellbeing_score": 72,
        "social_engagement": 68,
        "energy_level": 60,
        "focus_score": 65,
        "gaze": {"eye_contact_ratio": 0.71, "direction": "forward"},
        "emotions": {"happy": 0.55, "neutral": 0.30, "sad": 0.10, "anxious": 0.05},
        "movement": {"activity_level": 58, "restlessness": 20},
    },
    # day 2 – baseline healthy
    {
        "date": "2025-01-14",
        "person_id": "student_001",
        "detected": True,
        "wellbeing_score": 75,
        "social_engagement": 72,
        "energy_level": 63,
        "focus_score": 70,
        "gaze": {"eye_contact_ratio": 0.68, "direction": "forward"},
        "emotions": {"happy": 0.60, "neutral": 0.25, "sad": 0.08, "anxious": 0.07},
        "movement": {"activity_level": 60, "restlessness": 18},
    },
    # day 3 – baseline healthy (slight dip)
    {
        "date": "2025-01-15",
        "person_id": "student_001",
        "detected": True,
        "wellbeing_score": 70,
        "social_engagement": 65,
        "energy_level": 58,
        "focus_score": 62,
        "gaze": {"eye_contact_ratio": 0.65, "direction": "forward"},
        "emotions": {"happy": 0.50, "neutral": 0.32, "sad": 0.12, "anxious": 0.06},
        "movement": {"activity_level": 55, "restlessness": 22},
    },
    # day 4 – SUDDEN_DROP: wellbeing drops ~30 points
    {
        "date": "2025-01-16",
        "person_id": "student_001",
        "detected": True,
        "wellbeing_score": 42,
        "social_engagement": 38,
        "energy_level": 35,
        "focus_score": 30,
        "gaze": {"eye_contact_ratio": 0.00, "direction": "downward"},
        "emotions": {"happy": 0.10, "neutral": 0.20, "sad": 0.50, "anxious": 0.20},
        "movement": {"activity_level": 30, "restlessness": 40},
    },
    # day 5 – SUSTAINED_LOW + SOCIAL_WITHDRAWAL + GAZE_AVOIDANCE
    {
        "date": "2025-01-17",
        "person_id": "student_001",
        "detected": True,
        "wellbeing_score": 38,
        "social_engagement": 28,   # dropped 40 pts vs baseline
        "energy_level": 30,
        "focus_score": 28,
        "gaze": {"eye_contact_ratio": 0.00, "direction": "downward"},
        "emotions": {"happy": 0.05, "neutral": 0.18, "sad": 0.55, "anxious": 0.22},
        "movement": {"activity_level": 25, "restlessness": 45},
    },
    # day 6 – still SUSTAINED_LOW + GAZE_AVOIDANCE
    {
        "date": "2025-01-18",
        "person_id": "student_001",
        "detected": True,
        "wellbeing_score": 40,
        "social_engagement": 30,
        "energy_level": 28,
        "focus_score": 32,
        "gaze": {"eye_contact_ratio": 0.00, "direction": "downward"},
        "emotions": {"happy": 0.08, "neutral": 0.20, "sad": 0.52, "anxious": 0.20},
        "movement": {"activity_level": 28, "restlessness": 42},
    },
    # day 7 – ABSENCE_FLAG simulation: not detected
    {
        "date": "2025-01-19",
        "person_id": "student_001",
        "detected": False,
        "wellbeing_score": None,
        "social_engagement": None,
        "energy_level": None,
        "focus_score": None,
        "gaze": {"eye_contact_ratio": None, "direction": None},
        "emotions": {},
        "movement": {"activity_level": None, "restlessness": None},
    },
    # day 8 – still absent
    {
        "date": "2025-01-20",
        "person_id": "student_001",
        "detected": False,
        "wellbeing_score": None,
        "social_engagement": None,
        "energy_level": None,
        "focus_score": None,
        "gaze": {"eye_contact_ratio": None, "direction": None},
        "emotions": {},
        "movement": {"activity_level": None, "restlessness": None},
    },
]

for record in days_data:
    fname = f"{record['date']}.json"
    fpath = os.path.join(OUTPUT_DIR, fname)
    with open(fpath, "w") as f:
        json.dump(record, f, indent=2)
    print(f"Written: {fpath}")

print("Sample data generation complete.")
