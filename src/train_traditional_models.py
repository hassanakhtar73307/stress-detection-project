"""
train_traditional_models.py
Trains Random Forest and XGBoost under Leave-One-Subject-Out (LOSO)
cross-validation on the extracted WESAD features.
Saves per-subject results and confusion matrices.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix
)
from sklearn.preprocessing import label_binarize
import matplotlib.pyplot as plt
import seaborn as sns
import os

DATA_PATH = "data/processed/features_traditional.csv"
OUT_DIR = "models"
NOTEBOOKS_DIR = "notebooks"
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(NOTEBOOKS_DIR, exist_ok=True)

LABEL_NAMES = {1: "Baseline", 2: "Stress", 3: "Amusement"}


def load_data():
    df = pd.read_csv(DATA_PATH)
    feature_cols = [c for c in df.columns if c not in ("subject", "label")]
    return df, feature_cols


def loso_evaluate(df, feature_cols, model_fn, model_name):
    subjects = df["subject"].unique()
    results = []
    all_true = []
    all_pred = []

    for test_subject in subjects:
        train_df = df[df["subject"] != test_subject]
        test_df = df[df["subject"] == test_subject]

        X_train = train_df[feature_cols].values
        y_train = train_df["label"].values
        X_test = test_df[feature_cols].values
        y_test = test_df["label"].values

        model = model_fn()
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, average="macro", zero_division=0)
        rec = recall_score(y_test, y_pred, average="macro", zero_division=0)
        f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)

        try:
            y_proba = model.predict_proba(X_test)
            y_test_bin = label_binarize(y_test, classes=[1, 2, 3])
            if y_test_bin.shape[1] == y_proba.shape[1]:
                auc = roc_auc_score(y_test_bin, y_proba, average="macro", multi_class="ovr")
            else:
                auc = np.nan
        except Exception:
            auc = np.nan

        results.append({
            "subject": test_subject, "accuracy": acc, "precision": prec,
            "recall": rec, "f1_macro": f1, "roc_auc": auc
        })

        all_true.extend(y_test)
        all_pred.extend(y_pred)

        print(f"  [{model_name}] Test subject {test_subject}: Acc={acc:.3f}, F1={f1:.3f}")

    results_df = pd.DataFrame(results)
    cm = confusion_matrix(all_true, all_pred, labels=[1, 2, 3])

    return results_df, cm, all_true, all_pred


def plot_confusion_matrix(cm, model_name):
    plt.figure(figsize=(5, 4))
    labels = [LABEL_NAMES[i] for i in [1, 2, 3]]
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=labels, yticklabels=labels)
    plt.title(f"{model_name} — Aggregated Confusion Matrix (LOSO)")
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.tight_layout()
    path = os.path.join(NOTEBOOKS_DIR, f"confusion_matrix_{model_name.lower().replace(' ', '_')}.png")
    plt.savefig(path, dpi=150)
    print(f"Saved {path}")
    plt.close()


if __name__ == "__main__":
    df, feature_cols = load_data()
    print(f"Loaded {df.shape[0]} rows, {len(feature_cols)} features, {df['subject'].nunique()} subjects\n")

    all_summaries = {}

    print("Running Random Forest (LOSO)...")
    rf_fn = lambda: RandomForestClassifier(n_estimators=300, max_depth=15, random_state=42, n_jobs=-1)
    rf_results, rf_cm, rf_true, rf_pred = loso_evaluate(df, feature_cols, rf_fn, "Random Forest")
    rf_results.to_csv(os.path.join(OUT_DIR, "rf_loso_results.csv"), index=False)
    plot_confusion_matrix(rf_cm, "Random Forest")
    all_summaries["Random Forest"] = rf_results[["accuracy", "precision", "recall", "f1_macro"]].mean().to_dict()

    print()

    print("Running XGBoost (LOSO)...")
    def xgb_fn():
        return XGBClassifier(
            n_estimators=300, max_depth=3, learning_rate=0.1,
            objective="multi:softprob", num_class=3,
            eval_metric="mlogloss", random_state=42, n_jobs=-1
        )

    df_xgb = df.copy()
    df_xgb["label"] = df_xgb["label"] - 1
    xgb_results, xgb_cm_raw, xgb_true, xgb_pred = loso_evaluate(df_xgb, feature_cols, xgb_fn, "XGBoost")
    xgb_results.to_csv(os.path.join(OUT_DIR, "xgb_loso_results.csv"), index=False)

    xgb_cm = confusion_matrix([t + 1 for t in xgb_true], [p + 1 for p in xgb_pred], labels=[1, 2, 3])
    plot_confusion_matrix(xgb_cm, "XGBoost")
    all_summaries["XGBoost"] = xgb_results[["accuracy", "precision", "recall", "f1_macro"]].mean().to_dict()

    print("\n" + "=" * 50)
    print("SUMMARY (mean across all 15 LOSO folds)")
    print("=" * 50)
    summary_df = pd.DataFrame(all_summaries).T
    print(summary_df.round(3))
    summary_df.to_csv(os.path.join(OUT_DIR, "model_comparison_summary.csv"))
    print(f"\nSaved summary to {OUT_DIR}/model_comparison_summary.csv")