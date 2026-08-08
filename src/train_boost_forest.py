"""
train_boost_forest.py

Boost Forest:
A leakage-safe stacked ensemble combining the tuned Random Forest and XGBoost
models already used in this project.

Evaluation:
- Outer Leave-One-Subject-Out (LOSO): evaluates Boost Forest on one unseen subject.
- Inner LOSO on the remaining subjects: creates out-of-fold RF/XGB probabilities
  used to train the Logistic Regression meta-classifier.
- The outer test subject is NEVER used to train the base models or meta-classifier.

Outputs:
- models/boost_forest_loso_results.csv
- models/boost_forest_subject_comparison.csv
- notebooks/confusion_matrix_boost_forest.png
"""

import os
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
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

LABELS = [1, 2, 3]
ZERO_LABELS = [0, 1, 2]

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

def make_meta_classifier():
    return LogisticRegression(max_iter=2000, random_state=42)

def build_meta_features(xgb_proba, rf_proba):
    xgb_conf = np.max(xgb_proba, axis=1).reshape(-1, 1)
    rf_conf = np.max(rf_proba, axis=1).reshape(-1, 1)

    xgb_pred = np.argmax(xgb_proba, axis=1)
    rf_pred = np.argmax(rf_proba, axis=1)

    confidence_difference = xgb_conf - rf_conf
    agreement = (xgb_pred == rf_pred).astype(float).reshape(-1, 1)

    return np.hstack([
        xgb_proba,
        rf_proba,
        xgb_conf,
        rf_conf,
        confidence_difference,
        agreement,
    ])

def safe_auc(y_true_zero, proba):
    try:
        y_bin = label_binarize(y_true_zero, classes=ZERO_LABELS)
        return roc_auc_score(
            y_bin,
            proba,
            average="macro",
            multi_class="ovr",
        )
    except ValueError:
        return np.nan

def metric_row(y_true, y_pred, proba):
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(
            y_true, y_pred, average="macro", zero_division=0
        ),
        "recall": recall_score(
            y_true, y_pred, average="macro", zero_division=0
        ),
        "f1_macro": f1_score(
            y_true, y_pred, average="macro", zero_division=0
        ),
        "roc_auc": safe_auc(y_true - 1, proba),
    }

def create_inner_oof_meta_training(X_train, y_train, groups_train):
    unique_inner_subjects = np.unique(groups_train)

    meta_X = np.zeros((len(X_train), 10), dtype=float)
    meta_y = y_train - 1

    for inner_subject in unique_inner_subjects:
        inner_val_mask = groups_train == inner_subject
        inner_fit_mask = ~inner_val_mask

        X_inner_fit = X_train[inner_fit_mask]
        y_inner_fit = y_train[inner_fit_mask]
        X_inner_val = X_train[inner_val_mask]

        rf = make_rf()
        rf.fit(X_inner_fit, y_inner_fit)
        rf_proba = rf.predict_proba(X_inner_val)

        xgb = make_xgb()
        xgb.fit(X_inner_fit, y_inner_fit - 1)
        xgb_proba = xgb.predict_proba(X_inner_val)

        meta_X[inner_val_mask] = build_meta_features(
            xgb_proba=xgb_proba,
            rf_proba=rf_proba,
        )

    return meta_X, meta_y

def run_boost_forest_loso(df, feature_cols):
    subjects = np.unique(df["subject"].values)

    results = []
    diagnostics = []

    all_true = []
    all_pred = []

    for fold_no, test_subject in enumerate(subjects, start=1):
        print(f"\n[{fold_no:02d}/{len(subjects)}] Outer test subject: {test_subject}")

        test_mask = df["subject"].values == test_subject
        train_mask = ~test_mask

        train_df = df.loc[train_mask]
        test_df = df.loc[test_mask]

        X_train = train_df[feature_cols].values
        y_train = train_df["label"].values
        groups_train = train_df["subject"].values

        X_test = test_df[feature_cols].values
        y_test = test_df["label"].values

        print("  Building inner-LOSO meta-training predictions...")
        meta_X_train, meta_y_train = create_inner_oof_meta_training(
            X_train, y_train, groups_train
        )

        meta_model = make_meta_classifier()
        meta_model.fit(meta_X_train, meta_y_train)

        rf = make_rf()
        rf.fit(X_train, y_train)

        xgb = make_xgb()
        xgb.fit(X_train, y_train - 1)

        rf_proba = rf.predict_proba(X_test)
        xgb_proba = xgb.predict_proba(X_test)

        rf_pred = rf.predict(X_test)
        xgb_pred = np.argmax(xgb_proba, axis=1) + 1

        meta_X_test = build_meta_features(
            xgb_proba=xgb_proba,
            rf_proba=rf_proba,
        )

        boost_proba = meta_model.predict_proba(meta_X_test)
        boost_pred = np.argmax(boost_proba, axis=1) + 1

        boost_metrics = metric_row(y_test, boost_pred, boost_proba)

        rf_f1 = f1_score(y_test, rf_pred, average="macro", zero_division=0)
        xgb_f1 = f1_score(y_test, xgb_pred, average="macro", zero_division=0)

        rf_acc = accuracy_score(y_test, rf_pred)
        xgb_acc = accuracy_score(y_test, xgb_pred)

        agreement_rate = np.mean(rf_pred == xgb_pred)

        results.append({
            "subject": test_subject,
            **boost_metrics,
        })

        diagnostics.append({
            "subject": test_subject,
            "boost_forest_accuracy": boost_metrics["accuracy"],
            "xgboost_accuracy": xgb_acc,
            "random_forest_accuracy": rf_acc,
            "boost_forest_f1": boost_metrics["f1_macro"],
            "xgboost_f1": xgb_f1,
            "random_forest_f1": rf_f1,
            "base_model_agreement_rate": agreement_rate,
        })

        all_true.extend(y_test.tolist())
        all_pred.extend(boost_pred.tolist())

        print(
            f"  Boost Forest: "
            f"Acc={boost_metrics['accuracy']:.3f}, "
            f"F1={boost_metrics['f1_macro']:.3f}, "
            f"AUC={boost_metrics['roc_auc']:.3f}"
        )
        print(
            f"  Base models : "
            f"XGB Acc={xgb_acc:.3f}, RF Acc={rf_acc:.3f}, "
            f"agreement={agreement_rate:.3f}"
        )

    results_df = pd.DataFrame(results)
    diagnostics_df = pd.DataFrame(diagnostics)

    cm = confusion_matrix(all_true, all_pred, labels=LABELS)

    return results_df, diagnostics_df, cm

def save_confusion_matrix(cm):
    plt.figure(figsize=(6, 5))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=["Baseline", "Stress", "Amusement"],
        yticklabels=["Baseline", "Stress", "Amusement"],
    )
    plt.title("Boost Forest — Aggregated Confusion Matrix (LOSO)")
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.tight_layout()

    output_path = os.path.join(
        NOTEBOOK_DIR,
        "confusion_matrix_boost_forest.png",
    )
    plt.savefig(output_path, dpi=200)
    plt.close()
    print(f"\nSaved {output_path}")

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

    print("\nStarting Boost Forest nested LOSO evaluation...")
    print("Outer LOSO = final unbiased evaluation")
    print("Inner LOSO = leakage-safe meta-classifier training")

    results_df, diagnostics_df, cm = run_boost_forest_loso(
        df,
        feature_cols,
    )

    results_path = os.path.join(
        OUT_DIR,
        "boost_forest_loso_results.csv",
    )
    diagnostics_path = os.path.join(
        OUT_DIR,
        "boost_forest_subject_comparison.csv",
    )

    results_df.to_csv(results_path, index=False)
    diagnostics_df.to_csv(diagnostics_path, index=False)

    save_confusion_matrix(cm)

    print("\n" + "=" * 60)
    print("BOOST FOREST LOSO SUMMARY")
    print("=" * 60)

    metric_cols = [
        "accuracy",
        "precision",
        "recall",
        "f1_macro",
        "roc_auc",
    ]

    print(results_df[metric_cols].mean().round(4))

    print("\nSaved:")
    print(f"  {results_path}")
    print(f"  {diagnostics_path}")

if __name__ == "__main__":
    main()
