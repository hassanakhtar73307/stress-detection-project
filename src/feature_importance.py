"""
feature_importance.py
Analyses which of the 45 features the deployed XGBoost model relies on most,
and aggregates importance by sensor channel (ECG, EDA, EMG, Resp, Temp).

This directly supports the dissertation discussion of *why* XGBoost
outperforms the other models, rather than just reporting that it does.

Run from the project root:
    python src\\feature_importance.py

No new pip installs required (uses xgboost + matplotlib, both already installed).
"""
import os
import joblib
import pandas as pd
import matplotlib.pyplot as plt

MODEL_PATH = os.path.join("models", "xgb_final.joblib")
FEATURES_PATH = os.path.join("data", "processed", "features_traditional.csv")
OUT_DIR = "models"

SENSOR_PREFIXES = ["ECG", "EDA", "EMG", "Resp", "Temp"]


def get_sensor(feature_name):
    for prefix in SENSOR_PREFIXES:
        if feature_name.startswith(prefix):
            return prefix
    return "Other"


def main():
    print("Loading model and feature schema...")
    model = joblib.load(MODEL_PATH)
    feature_cols = [c for c in pd.read_csv(FEATURES_PATH, nrows=1).columns if c not in ("subject", "label")]

    # XGBoost's built-in gain-based importance: how much each feature
    # improves the model's splits on average, weighted by how often it's used.
    booster = model.get_booster()
    raw_scores = booster.get_score(importance_type="gain")

    # XGBoost names features f0, f1, ... internally unless trained with a
    # DataFrame that had column names; handle both cases.
    importances = []
    for i, name in enumerate(feature_cols):
        key = name if name in raw_scores else f"f{i}"
        importances.append(raw_scores.get(key, 0.0))

    imp_df = pd.DataFrame({"feature": feature_cols, "importance": importances})
    imp_df["sensor"] = imp_df["feature"].apply(get_sensor)
    imp_df = imp_df.sort_values("importance", ascending=False).reset_index(drop=True)

    imp_df.to_csv(os.path.join(OUT_DIR, "feature_importance.csv"), index=False)
    print(f"Saved full ranking to {OUT_DIR}/feature_importance.csv\n")

    print("Top 10 individual features:")
    print(imp_df.head(10).to_string(index=False))

    # Aggregate by sensor channel -- this is the key "why" evidence:
    # which physiological signal is XGBoost actually relying on?
    by_sensor = imp_df.groupby("sensor")["importance"].sum().sort_values(ascending=False)
    by_sensor_pct = (by_sensor / by_sensor.sum() * 100).round(1)
    print("\nImportance aggregated by sensor channel:")
    print(by_sensor_pct.to_string())
    by_sensor_pct.to_csv(os.path.join(OUT_DIR, "feature_importance_by_sensor.csv"))

    # Plot 1: top 15 individual features
    plt.figure(figsize=(8, 6))
    top15 = imp_df.head(15).iloc[::-1]
    plt.barh(top15["feature"], top15["importance"], color="#4ec9a8")
    plt.xlabel("Gain-based importance")
    plt.title("XGBoost: Top 15 most important features")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "feature_importance_top15.png"), dpi=150)
    print(f"\nSaved chart to {OUT_DIR}/feature_importance_top15.png")
    plt.close()

    # Plot 2: importance by sensor channel
    plt.figure(figsize=(6, 5))
    plt.bar(by_sensor_pct.index, by_sensor_pct.values, color="#4ec9a8")
    plt.ylabel("Share of total importance (%)")
    plt.title("XGBoost: importance by sensor channel")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "feature_importance_by_sensor.png"), dpi=150)
    print(f"Saved chart to {OUT_DIR}/feature_importance_by_sensor.png")
    plt.close()


if __name__ == "__main__":
    main()
