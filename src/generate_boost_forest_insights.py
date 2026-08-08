"""
generate_boost_forest_insights.py

Creates global Boost Forest feature/sensor insight files by combining
the already-generated XGBoost and Random Forest global importances.

Method:
- Normalize each base model's feature importances to 100%.
- Read the final Boost Forest class-specific XGBoost weights.
- Use the macro-average XGBoost share across the 3 classes as the
  global ensemble contribution weight.
- Combine normalized XGBoost and RF feature importances.
- Re-normalize the combined feature importances to 100%.
- Aggregate by sensor.

This is a transparent global ensemble approximation. It is NOT a
per-prediction explanation.
"""

import json
from pathlib import Path

import pandas as pd

MODELS = Path("models")

XGB_FEATURES = MODELS / "xgboost_feature_importance.csv"
RF_FEATURES = MODELS / "random_forest_feature_importance.csv"
BOOST_CONFIG = MODELS / "boost_forest_final_config.json"

OUT_FEATURES = MODELS / "boost_forest_feature_importance.csv"
OUT_SENSORS = MODELS / "boost_forest_feature_importance_by_sensor.csv"


def normalize_pct(series):
    values = pd.to_numeric(series, errors="coerce").fillna(0.0)
    total = float(values.sum())
    if total <= 0:
        raise ValueError("Feature importance values must sum to more than zero.")
    return values / total * 100.0


def main():
    for path in (XGB_FEATURES, RF_FEATURES, BOOST_CONFIG):
        if not path.exists():
            raise FileNotFoundError(path)

    xgb = pd.read_csv(XGB_FEATURES)
    rf = pd.read_csv(RF_FEATURES)

    required = {"feature", "importance", "sensor"}
    if not required.issubset(xgb.columns):
        raise ValueError(f"{XGB_FEATURES} has an invalid schema.")
    if not required.issubset(rf.columns):
        raise ValueError(f"{RF_FEATURES} has an invalid schema.")

    with BOOST_CONFIG.open("r", encoding="utf-8") as handle:
        config = json.load(handle)

    class_weights = config["xgb_class_weights"]
    xgb_weights = [
        float(class_weights["baseline"]),
        float(class_weights["stress"]),
        float(class_weights["amusement"]),
    ]

    # Macro-average across the 3 classes:
    # final weights 1.0, 0.0, 0.8 -> global XGB share 0.6, RF share 0.4.
    xgb_share = sum(xgb_weights) / len(xgb_weights)
    rf_share = 1.0 - xgb_share

    xgb = xgb[["feature", "sensor", "importance"]].copy()
    rf = rf[["feature", "sensor", "importance"]].copy()

    xgb["xgb_importance_pct"] = normalize_pct(xgb["importance"])
    rf["rf_importance_pct"] = normalize_pct(rf["importance"])

    merged = xgb[
        ["feature", "sensor", "xgb_importance_pct"]
    ].merge(
        rf[["feature", "sensor", "rf_importance_pct"]],
        on=["feature", "sensor"],
        how="outer",
    )

    merged["xgb_importance_pct"] = (
        merged["xgb_importance_pct"].fillna(0.0)
    )
    merged["rf_importance_pct"] = (
        merged["rf_importance_pct"].fillna(0.0)
    )

    merged["importance"] = (
        xgb_share * merged["xgb_importance_pct"]
        + rf_share * merged["rf_importance_pct"]
    )

    merged["importance"] = normalize_pct(merged["importance"])

    merged = merged.sort_values(
        "importance",
        ascending=False,
    ).reset_index(drop=True)

    feature_output = merged[
        [
            "feature",
            "importance",
            "sensor",
            "xgb_importance_pct",
            "rf_importance_pct",
        ]
    ].copy()

    feature_output.to_csv(OUT_FEATURES, index=False)

    sensor_output = (
        feature_output.groupby("sensor", as_index=False)["importance"]
        .sum()
        .rename(columns={"importance": "importance_pct"})
        .sort_values("importance_pct", ascending=False)
        .reset_index(drop=True)
    )

    sensor_output["importance_pct"] = (
        sensor_output["importance_pct"]
        / sensor_output["importance_pct"].sum()
        * 100.0
    )

    sensor_output.to_csv(OUT_SENSORS, index=False)

    print("Boost Forest insight files generated.")
    print(
        f"Global blend used: "
        f"XGBoost={xgb_share:.1%}, Random Forest={rf_share:.1%}"
    )
    print(f"Saved: {OUT_FEATURES}")
    print(f"Saved: {OUT_SENSORS}")

    print("\nTop 10 combined features:")
    print(
        feature_output[
            ["feature", "sensor", "importance"]
        ].head(10).to_string(index=False)
    )

    print("\nCombined sensor importance:")
    print(sensor_output.to_string(index=False))


if __name__ == "__main__":
    main()
