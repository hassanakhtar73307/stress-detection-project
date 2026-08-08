"""
train_boost_forest_final.py

Trains the deployable Boost Forest model on ALL available subjects.

Method:
1. Generate leakage-safe LOSO out-of-fold probabilities for the tuned
   XGBoost and Random Forest base models.
2. Select one XGBoost-vs-Random-Forest blending weight per class using
   macro-F1 as the primary objective and accuracy as the tie-breaker.
3. Retrain both tuned base models on the full dataset.
4. Save the fitted base models + selected class weights + feature metadata
   in one joblib bundle for API deployment.

This script does NOT re-evaluate the model. Final unbiased evaluation is
already contained in models/boost_forest_v2_loso_results.csv.
"""

import itertools
import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
from xgboost import XGBClassifier


DATA_PATH = "data/processed/features_traditional.csv"
OUT_DIR = "models"

MODEL_PATH = os.path.join(OUT_DIR, "boost_forest_final.joblib")
CONFIG_PATH = os.path.join(OUT_DIR, "boost_forest_final_config.json")

os.makedirs(OUT_DIR, exist_ok=True)

RF_PARAMS = {
    "n_estimators": 300,
    "max_depth": 15,
    "random_state": 42,
    "n_jobs": -1,
}

XGB_PARAMS = {
    "n_estimators": 300,
    "max_depth": 3,
    "learning_rate": 0.1,
    "eval_metric": "mlogloss",
    "random_state": 42,
    "n_jobs": -1,
}


def make_rf():
    return RandomForestClassifier(**RF_PARAMS)


def make_xgb():
    return XGBClassifier(**XGB_PARAMS)


def normalize_rows(proba):
    row_sum = proba.sum(axis=1, keepdims=True)
    row_sum[row_sum == 0] = 1.0
    return proba / row_sum


def blend_probabilities(xgb_proba, rf_proba, alphas):
    alphas = np.asarray(alphas, dtype=float).reshape(1, 3)
    blended = (
        alphas * xgb_proba
        + (1.0 - alphas) * rf_proba
    )
    return normalize_rows(blended)


def make_loso_oof_probabilities(X, y_one, groups):
    """
    Produce OOF probabilities for every row using subject-wise LOSO.
    Each row is predicted by models trained without that row's subject.
    """
    xgb_oof = np.zeros((len(X), 3), dtype=float)
    rf_oof = np.zeros((len(X), 3), dtype=float)

    subjects = np.unique(groups)

    for fold_no, held_subject in enumerate(subjects, start=1):
        print(
            f"  OOF fold {fold_no:02d}/{len(subjects)} "
            f"- held subject: {held_subject}"
        )

        val_mask = groups == held_subject
        fit_mask = ~val_mask

        X_fit = X[fit_mask]
        y_fit_one = y_one[fit_mask]
        X_val = X[val_mask]

        rf = make_rf()
        rf.fit(X_fit, y_fit_one)
        rf_oof[val_mask] = rf.predict_proba(X_val)

        xgb = make_xgb()
        xgb.fit(X_fit, y_fit_one - 1)
        xgb_oof[val_mask] = xgb.predict_proba(X_val)

    return xgb_oof, rf_oof


def tune_class_weights(xgb_oof, rf_oof, y_true_one):
    """
    Search one XGBoost blend weight per class.

    alpha = 1.0 -> fully XGBoost for that class
    alpha = 0.0 -> fully Random Forest for that class
    """
    grid = np.linspace(0.0, 1.0, 11)

    best_alphas = (1.0, 1.0, 1.0)
    best_f1 = -1.0
    best_acc = -1.0

    for alphas in itertools.product(grid, repeat=3):
        proba = blend_probabilities(
            xgb_oof,
            rf_oof,
            alphas,
        )
        pred_one = np.argmax(proba, axis=1) + 1

        f1 = f1_score(
            y_true_one,
            pred_one,
            average="macro",
            zero_division=0,
        )
        acc = accuracy_score(y_true_one, pred_one)

        if (f1 > best_f1 + 1e-12) or (
            abs(f1 - best_f1) <= 1e-12
            and acc > best_acc
        ):
            best_alphas = tuple(float(a) for a in alphas)
            best_f1 = float(f1)
            best_acc = float(acc)

    return best_alphas, best_f1, best_acc


def main():
    print("Loading traditional feature data...")
    df = pd.read_csv(DATA_PATH)

    feature_cols = [
        c for c in df.columns
        if c not in ("subject", "label")
    ]

    X = df[feature_cols].values
    y_one = df["label"].values
    groups = df["subject"].values

    print(
        f"Loaded {len(df)} rows, "
        f"{len(feature_cols)} features, "
        f"{df['subject'].nunique()} subjects"
    )

    print("\nGenerating LOSO OOF probabilities for final blend selection...")
    xgb_oof, rf_oof = make_loso_oof_probabilities(
        X,
        y_one,
        groups,
    )

    print("\nSelecting final class-wise Boost Forest weights...")
    alphas, oof_f1, oof_acc = tune_class_weights(
        xgb_oof,
        rf_oof,
        y_one,
    )

    print(
        "Selected XGBoost shares: "
        f"Baseline={alphas[0]:.1f}, "
        f"Stress={alphas[1]:.1f}, "
        f"Amusement={alphas[2]:.1f}"
    )
    print(
        f"OOF selection score: "
        f"F1-macro={oof_f1:.4f}, "
        f"Accuracy={oof_acc:.4f}"
    )

    print("\nTraining final Random Forest on all subjects...")
    rf_final = make_rf()
    rf_final.fit(X, y_one)

    print("Training final XGBoost on all subjects...")
    xgb_final = make_xgb()
    xgb_final.fit(X, y_one - 1)

    bundle = {
        "model_name": "Boost Forest",
        "model_version": "v2",
        "ensemble_type": "class_wise_probability_blend",
        "rf_model": rf_final,
        "xgb_model": xgb_final,
        "xgb_class_weights": np.asarray(alphas, dtype=float),
        "feature_cols": feature_cols,
        "labels": [1, 2, 3],
        "class_names": ["Baseline", "Stress", "Amusement"],
        "rf_params": RF_PARAMS,
        "xgb_params": XGB_PARAMS,
    }

    joblib.dump(bundle, MODEL_PATH)

    config = {
        "model_name": "Boost Forest",
        "version": "v2",
        "ensemble_type": "class_wise_probability_blend",
        "xgb_class_weights": {
            "baseline": alphas[0],
            "stress": alphas[1],
            "amusement": alphas[2],
        },
        "random_forest_class_weights": {
            "baseline": 1.0 - alphas[0],
            "stress": 1.0 - alphas[1],
            "amusement": 1.0 - alphas[2],
        },
        "oof_weight_selection_f1_macro": oof_f1,
        "oof_weight_selection_accuracy": oof_acc,
        "n_features": len(feature_cols),
        "n_subjects": int(df["subject"].nunique()),
        "n_rows": int(len(df)),
        "class_names": ["Baseline", "Stress", "Amusement"],
        "rf_params": RF_PARAMS,
        "xgb_params": XGB_PARAMS,
    }

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    print("\nFinal Boost Forest model saved:")
    print(f"  {MODEL_PATH}")
    print(f"  {CONFIG_PATH}")

    print("\nVerifying saved model bundle...")
    loaded = joblib.load(MODEL_PATH)

    required_keys = {
        "rf_model",
        "xgb_model",
        "xgb_class_weights",
        "feature_cols",
    }
    missing = required_keys.difference(loaded.keys())

    if missing:
        raise RuntimeError(
            f"Saved bundle verification failed. Missing: {sorted(missing)}"
        )

    sample = X[:5]
    rf_proba = loaded["rf_model"].predict_proba(sample)
    xgb_proba = loaded["xgb_model"].predict_proba(sample)
    boost_proba = blend_probabilities(
        xgb_proba,
        rf_proba,
        loaded["xgb_class_weights"],
    )
    boost_pred = np.argmax(boost_proba, axis=1) + 1

    print("Verification successful.")
    print(f"  Sample predictions: {boost_pred.tolist()}")
    print(
        "  Probability row sums: "
        f"{np.round(boost_proba.sum(axis=1), 6).tolist()}"
    )


if __name__ == "__main__":
    main()
