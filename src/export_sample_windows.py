"""
export_sample_windows.py
Exports a handful of real feature windows (with true labels) as JSON,
for the React dashboard to use as simulated sensor readings.
"""
import pandas as pd
import json

df = pd.read_csv("data/processed/features_traditional.csv")
feature_cols = [c for c in df.columns if c not in ("subject", "label")]

LABEL_NAMES = {1: "Baseline", 2: "Stress", 3: "Amusement"}

samples = []
for label in [1, 2, 3]:
    subset = df[df["label"] == label].sample(n=3, random_state=42)
    for _, row in subset.iterrows():
        samples.append({
            "subject": row["subject"],
            "true_label": LABEL_NAMES[int(row["label"])],
            "features": {c: row[c] for c in feature_cols}
        })

with open("webapp/dashboard/src/sample_windows.json", "w") as f:
    json.dump(samples, f, indent=2)

print(f"Exported {len(samples)} sample windows to webapp/dashboard/src/sample_windows.json")