"""
Generate global feature-importance results for the deployed
XGBoost and Random Forest models.

Run from the project root:

    python src\\feature_importance.py
"""

import os

import joblib
import matplotlib.pyplot as plt
import pandas as pd


FEATURES_PATH = os.path.join(
    "data",
    "processed",
    "features_traditional.csv",
)

OUT_DIR = "models"

MODEL_CONFIG = {
    "xgboost": {
        "path": os.path.join(OUT_DIR, "xgb_final.joblib"),
        "display_name": "XGBoost",
        "axis_label": "Gain-based importance",
    },
    "random_forest": {
        "path": os.path.join(OUT_DIR, "rf_final.joblib"),
        "display_name": "Random Forest",
        "axis_label": "Impurity-based importance",
    },
}

SENSOR_PREFIXES = ["ECG", "EDA", "EMG", "Resp", "Temp"]


def get_sensor(feature_name):
    for prefix in SENSOR_PREFIXES:
        if feature_name.startswith(prefix):
            return prefix

    return "Other"


def get_model_importances(model_name, model, feature_cols):
    """Return one importance value for every engineered feature."""

    if model_name == "xgboost":
        booster = model.get_booster()
        raw_scores = booster.get_score(importance_type="gain")

        return [
            raw_scores.get(
                feature_name
                if feature_name in raw_scores
                else f"f{index}",
                0.0,
            )
            for index, feature_name in enumerate(feature_cols)
        ]

    if model_name == "random_forest":
        return model.feature_importances_.tolist()

    raise ValueError(f"Unsupported model: {model_name}")


def save_model_results(model_name, config, feature_cols):
    display_name = config["display_name"]

    print(f"\nLoading {display_name}...")
    model = joblib.load(config["path"])

    importances = get_model_importances(
        model_name,
        model,
        feature_cols,
    )

    if len(importances) != len(feature_cols):
        raise ValueError(
            f"{display_name} returned {len(importances)} importance values, "
            f"but {len(feature_cols)} features were expected."
        )

    importance_df = pd.DataFrame(
        {
            "feature": feature_cols,
            "importance": importances,
        }
    )

    importance_df["sensor"] = importance_df["feature"].apply(
        get_sensor
    )

    importance_df = importance_df.sort_values(
        "importance",
        ascending=False,
    ).reset_index(drop=True)

    feature_output = os.path.join(
        OUT_DIR,
        f"{model_name}_feature_importance.csv",
    )

    importance_df.to_csv(feature_output, index=False)

    by_sensor = (
        importance_df.groupby("sensor")["importance"]
        .sum()
        .sort_values(ascending=False)
    )

    total_importance = by_sensor.sum()

    if total_importance == 0:
        raise ValueError(
            f"{display_name} returned zero total feature importance."
        )

    by_sensor_pct = (
        by_sensor
        .div(total_importance)
        .mul(100)
        .round(1)
        .rename("importance_pct")
        .reset_index()
    )

    sensor_output = os.path.join(
        OUT_DIR,
        f"{model_name}_feature_importance_by_sensor.csv",
    )

    by_sensor_pct.to_csv(sensor_output, index=False)

    # Preserve the old XGBoost filenames while the API is being updated.
    if model_name == "xgboost":
        importance_df.to_csv(
            os.path.join(OUT_DIR, "feature_importance.csv"),
            index=False,
        )

        by_sensor_pct.to_csv(
            os.path.join(
                OUT_DIR,
                "feature_importance_by_sensor.csv",
            ),
            index=False,
        )

    print(f"Saved: {feature_output}")
    print(f"Saved: {sensor_output}")

    print(f"\n{display_name} top 10 features:")
    print(
        importance_df.head(10).to_string(index=False)
    )

    print(f"\n{display_name} importance by sensor:")
    print(by_sensor_pct.to_string(index=False))

    top_15 = importance_df.head(15).iloc[::-1]

    plt.figure(figsize=(9, 6))
    plt.barh(
        top_15["feature"],
        top_15["importance"],
    )
    plt.xlabel(config["axis_label"])
    plt.title(
        f"{display_name}: Top 15 most important features"
    )
    plt.tight_layout()
    plt.savefig(
        os.path.join(
            OUT_DIR,
            f"{model_name}_feature_importance_top15.png",
        ),
        dpi=150,
    )
    plt.close()

    plt.figure(figsize=(7, 5))
    plt.bar(
        by_sensor_pct["sensor"],
        by_sensor_pct["importance_pct"],
    )
    plt.ylabel("Share of total importance (%)")
    plt.title(
        f"{display_name}: Global importance by sensor group"
    )
    plt.tight_layout()
    plt.savefig(
        os.path.join(
            OUT_DIR,
            f"{model_name}_feature_importance_by_sensor.png",
        ),
        dpi=150,
    )
    plt.close()


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    feature_cols = [
        column
        for column in pd.read_csv(
            FEATURES_PATH,
            nrows=1,
        ).columns
        if column not in ("subject", "label")
    ]

    print(f"Feature count: {len(feature_cols)}")

    for model_name, config in MODEL_CONFIG.items():
        save_model_results(
            model_name,
            config,
            feature_cols,
        )

    print(
        "\nFinished generating XGBoost and "
        "Random Forest importance results."
    )


if __name__ == "__main__":
    main()