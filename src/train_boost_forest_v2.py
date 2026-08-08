"""
train_boost_forest_v2.py

Boost Forest v2:
A leakage-safe class-wise weighted ensemble of tuned XGBoost + Random Forest.

For class c:
    P_boost(c) = alpha_c * P_xgb(c) + (1 - alpha_c) * P_rf(c)

The three class weights are selected ONLY from inner LOSO out-of-fold
predictions. The outer LOSO subject remains unseen until final evaluation.
"""

import os
import warnings
import itertools

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)
from sklearn.preprocessing import label_binarize
from xgboost import XGBClassifier


DATA_PATH = "data/processed/features_traditional.csv"
OUT_DIR = "models"
NOTEBOOK_DIR = "notebooks"

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(NOTEBOOK_DIR, exist_ok=True)

LABELS_ONE = [1, 2, 3]
LABELS_ZERO = [0, 1, 2]

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


def normalize_rows(p):
    row_sum = p.sum(axis=1, keepdims=True)
    row_sum[row_sum == 0] = 1.0
    return p / row_sum


def blend_probabilities(xgb_proba, rf_proba, alphas):
    a = np.asarray(alphas, dtype=float).reshape(1, 3)
    blended = a * xgb_proba + (1.0 - a) * rf_proba
    return normalize_rows(blended)


def safe_auc(y_true_zero, proba):
    try:
        y_bin = label_binarize(y_true_zero, classes=LABELS_ZERO)
        return roc_auc_score(
            y_bin,
            proba,
            average="macro",
            multi_class="ovr",
        )
    except ValueError:
        return np.nan


def metric_row(y_true_one, y_pred_one, proba):
    return {
        "accuracy": accuracy_score(y_true_one, y_pred_one),
        "precision": precision_score(
            y_true_one, y_pred_one, average="macro", zero_division=0
        ),
        "recall": recall_score(
            y_true_one, y_pred_one, average="macro", zero_division=0
        ),
        "f1_macro": f1_score(
            y_true_one, y_pred_one, average="macro", zero_division=0
        ),
        "roc_auc": safe_auc(y_true_one - 1, proba),
    }


def inner_oof_probabilities(X_train, y_train_one, groups_train):
    n = len(X_train)
    xgb_oof = np.zeros((n, 3), dtype=float)
    rf_oof = np.zeros((n, 3), dtype=float)

    for inner_subject in np.unique(groups_train):
        val_mask = groups_train == inner_subject
        fit_mask = ~val_mask

        X_fit = X_train[fit_mask]
        y_fit_one = y_train_one[fit_mask]
        X_val = X_train[val_mask]

        rf = make_rf()
        rf.fit(X_fit, y_fit_one)
        rf_oof[val_mask] = rf.predict_proba(X_val)

        xgb = make_xgb()
        xgb.fit(X_fit, y_fit_one - 1)
        xgb_oof[val_mask] = xgb.predict_proba(X_val)

    return xgb_oof, rf_oof, y_train_one


def tune_class_weights(xgb_oof, rf_oof, y_true_one):
    grid = np.linspace(0.0, 1.0, 11)

    best_alphas = (1.0, 1.0, 1.0)
    best_f1 = -1.0
    best_acc = -1.0

    for alphas in itertools.product(grid, repeat=3):
        proba = blend_probabilities(xgb_oof, rf_oof, alphas)
        pred_one = np.argmax(proba, axis=1) + 1

        f1 = f1_score(
            y_true_one,
            pred_one,
            average="macro",
            zero_division=0,
        )
        acc = accuracy_score(y_true_one, pred_one)

        if (f1 > best_f1 + 1e-12) or (
            abs(f1 - best_f1) <= 1e-12 and acc > best_acc
        ):
            best_f1 = f1
            best_acc = acc
            best_alphas = tuple(float(x) for x in alphas)

    return best_alphas, best_f1, best_acc


def run_nested_loso(df, feature_cols):
    subjects = np.unique(df["subject"].values)

    results = []
    weights_rows = []
    comparisons = []

    all_true = []
    all_pred = []

    for fold_no, test_subject in enumerate(subjects, start=1):
        print(f"\n[{fold_no:02d}/{len(subjects)}] Outer test subject: {test_subject}")

        test_mask = df["subject"].values == test_subject
        train_mask = ~test_mask

        train_df = df.loc[train_mask]
        test_df = df.loc[test_mask]

        X_train = train_df[feature_cols].values
        y_train_one = train_df["label"].values
        groups_train = train_df["subject"].values

        X_test = test_df[feature_cols].values
        y_test_one = test_df["label"].values

        print("  Building leakage-safe inner-LOSO probabilities...")
        xgb_oof, rf_oof, y_oof_one = inner_oof_probabilities(
            X_train,
            y_train_one,
            groups_train,
        )

        alphas, inner_f1, inner_acc = tune_class_weights(
            xgb_oof,
            rf_oof,
            y_oof_one,
        )

        print(
            "  Selected XGB class weights: "
            f"Baseline={alphas[0]:.1f}, "
            f"Stress={alphas[1]:.1f}, "
            f"Amusement={alphas[2]:.1f}"
        )
        print(
            f"  Inner OOF selection: F1={inner_f1:.3f}, Acc={inner_acc:.3f}"
        )

        rf = make_rf()
        rf.fit(X_train, y_train_one)

        xgb = make_xgb()
        xgb.fit(X_train, y_train_one - 1)

        rf_proba = rf.predict_proba(X_test)
        xgb_proba = xgb.predict_proba(X_test)

        rf_pred_one = rf.predict(X_test)
        xgb_pred_one = np.argmax(xgb_proba, axis=1) + 1

        boost_proba = blend_probabilities(
            xgb_proba,
            rf_proba,
            alphas,
        )
        boost_pred_one = np.argmax(boost_proba, axis=1) + 1

        boost_metrics = metric_row(
            y_test_one,
            boost_pred_one,
            boost_proba,
        )

        xgb_acc = accuracy_score(y_test_one, xgb_pred_one)
        rf_acc = accuracy_score(y_test_one, rf_pred_one)

        xgb_f1 = f1_score(
            y_test_one,
            xgb_pred_one,
            average="macro",
            zero_division=0,
        )
        rf_f1 = f1_score(
            y_test_one,
            rf_pred_one,
            average="macro",
            zero_division=0,
        )

        agreement = np.mean(xgb_pred_one == rf_pred_one)

        results.append({
            "subject": test_subject,
            **boost_metrics,
        })

        weights_rows.append({
            "subject": test_subject,
            "alpha_baseline_xgb": alphas[0],
            "alpha_stress_xgb": alphas[1],
            "alpha_amusement_xgb": alphas[2],
            "inner_oof_f1_macro": inner_f1,
            "inner_oof_accuracy": inner_acc,
        })

        comparisons.append({
            "subject": test_subject,
            "boost_forest_v2_accuracy": boost_metrics["accuracy"],
            "xgboost_accuracy": xgb_acc,
            "random_forest_accuracy": rf_acc,
            "boost_forest_v2_f1": boost_metrics["f1_macro"],
            "xgboost_f1": xgb_f1,
            "random_forest_f1": rf_f1,
            "base_model_agreement_rate": agreement,
        })

        all_true.extend(y_test_one.tolist())
        all_pred.extend(boost_pred_one.tolist())

        print(
            f"  Boost Forest v2: "
            f"Acc={boost_metrics['accuracy']:.3f}, "
            f"F1={boost_metrics['f1_macro']:.3f}, "
            f"AUC={boost_metrics['roc_auc']:.3f}"
        )
        print(
            f"  Base models    : "
            f"XGB Acc={xgb_acc:.3f}, "
            f"RF Acc={rf_acc:.3f}, "
            f"agreement={agreement:.3f}"
        )

    cm = confusion_matrix(all_true, all_pred, labels=LABELS_ONE)

    return (
        pd.DataFrame(results),
        pd.DataFrame(weights_rows),
        pd.DataFrame(comparisons),
        cm,
    )


def save_confusion_matrix(cm):
    fig, ax = plt.subplots(figsize=(6, 5))
    image = ax.imshow(cm)

    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center")

    labels = ["Baseline", "Stress", "Amusement"]
    ax.set_xticks(range(3), labels)
    ax.set_yticks(range(3), labels)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title("Boost Forest v2 — Aggregated Confusion Matrix (LOSO)")
    fig.colorbar(image, ax=ax)
    fig.tight_layout()

    path = os.path.join(
        NOTEBOOK_DIR,
        "confusion_matrix_boost_forest_v2.png",
    )
    fig.savefig(path, dpi=200)
    plt.close(fig)

    print(f"\nSaved {path}")


def main():
    warnings.filterwarnings("ignore", category=UserWarning)

    print("Loading traditional feature data...")
    df = pd.read_csv(DATA_PATH)

    feature_cols = [
        c for c in df.columns
        if c not in ("subject", "label")
    ]

    print(
        f"Loaded {len(df)} rows, "
        f"{len(feature_cols)} features, "
        f"{df['subject'].nunique()} subjects"
    )

    print("\nStarting Boost Forest v2 nested LOSO evaluation...")
    print("Outer LOSO = unbiased evaluation")
    print("Inner LOSO = class-wise blend-weight selection")

    results_df, weights_df, comparison_df, cm = run_nested_loso(
        df,
        feature_cols,
    )

    results_path = os.path.join(
        OUT_DIR,
        "boost_forest_v2_loso_results.csv",
    )
    weights_path = os.path.join(
        OUT_DIR,
        "boost_forest_v2_weights.csv",
    )
    comparison_path = os.path.join(
        OUT_DIR,
        "boost_forest_v2_subject_comparison.csv",
    )

    results_df.to_csv(results_path, index=False)
    weights_df.to_csv(weights_path, index=False)
    comparison_df.to_csv(comparison_path, index=False)

    save_confusion_matrix(cm)

    metric_cols = [
        "accuracy",
        "precision",
        "recall",
        "f1_macro",
        "roc_auc",
    ]

    print("\n" + "=" * 64)
    print("BOOST FOREST v2 LOSO SUMMARY")
    print("=" * 64)
    print(results_df[metric_cols].mean().round(4))

    print("\nMean selected XGBoost class weights:")
    print(
        weights_df[
            [
                "alpha_baseline_xgb",
                "alpha_stress_xgb",
                "alpha_amusement_xgb",
            ]
        ].mean().round(3)
    )

    print("\nSaved:")
    print(f"  {results_path}")
    print(f"  {weights_path}")
    print(f"  {comparison_path}")


if __name__ == "__main__":
    main()
