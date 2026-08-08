"""
train_lstm_tuned.py
Retrains the LSTM under LOSO cross-validation, using the tuned
hyperparameters found by tune_lstm.py (128 units, dropout 0.2) instead of
the original untuned architecture (32/16 units, dropout 0.3).

Saves results separately (lstm_loso_results_tuned.csv) so the original
untuned results are preserved for an honest before/after comparison in
the dissertation, rather than being silently overwritten.

Run from the project root:
    python src\\train_lstm_tuned.py
"""
import os
import json
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.utils.class_weight import compute_class_weight

DATA_PATH = "data/processed/sequences_lstm.npz"
TUNING_RESULTS_PATH = "models/lstm_tuning_results.json"
OUT_DIR = "models"
NOTEBOOKS_DIR = "notebooks"
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(NOTEBOOKS_DIR, exist_ok=True)

LABEL_NAMES = {1: "Baseline", 2: "Stress", 3: "Amusement"}
DOWNSAMPLE_FACTOR = 100


def load_data():
    data = np.load(DATA_PATH, allow_pickle=True)
    sequences = data["sequences"][:, ::DOWNSAMPLE_FACTOR, :]
    return sequences, data["labels"], data["subjects"]


def load_tuned_config():
    with open(TUNING_RESULTS_PATH) as f:
        cfg = json.load(f)
    print(f"Using tuned config from {TUNING_RESULTS_PATH}: {cfg}")
    return cfg


def build_tuned_model(input_shape, tuned_cfg, n_classes=3):
    units = tuned_cfg.get("units", 128)
    dropout = tuned_cfg.get("dropout", 0.2)
    n_layers = tuned_cfg.get("n_layers", 2)

    model = keras.Sequential()
    model.add(layers.Input(shape=input_shape))
    for i in range(n_layers):
        return_seq = i < n_layers - 1
        model.add(layers.LSTM(units, return_sequences=return_seq))
        model.add(layers.Dropout(dropout))
    model.add(layers.Dense(16, activation="relu"))
    model.add(layers.Dense(n_classes, activation="softmax"))

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def loso_evaluate(sequences, labels, subjects, tuned_cfg):
    unique_subjects = np.unique(subjects)
    results = []
    all_true = []
    all_pred = []

    label_map = {1: 0, 2: 1, 3: 2}
    inv_label_map = {0: 1, 1: 2, 2: 3}
    y_mapped = np.array([label_map[l] for l in labels])

    for test_subject in unique_subjects:
        train_mask = subjects != test_subject
        test_mask = subjects == test_subject

        X_train, y_train = sequences[train_mask], y_mapped[train_mask]
        X_test, y_test = sequences[test_mask], y_mapped[test_mask]

        model = build_tuned_model(input_shape=X_train.shape[1:], tuned_cfg=tuned_cfg)

        early_stop = keras.callbacks.EarlyStopping(
            monitor="loss", patience=5, restore_best_weights=True
        )

        classes = np.unique(y_train)
        weights = compute_class_weight("balanced", classes=classes, y=y_train)
        class_weight = {c: w for c, w in zip(classes, weights)}

        model.fit(
            X_train, y_train,
            epochs=25,
            batch_size=32,
            callbacks=[early_stop],
            class_weight=class_weight,
            verbose=0,
        )

        y_proba = model.predict(X_test, verbose=0)
        y_pred = np.argmax(y_proba, axis=1)

        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, average="macro", zero_division=0)
        rec = recall_score(y_test, y_pred, average="macro", zero_division=0)
        f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)

        try:
            auc = roc_auc_score(
                y_test,
                y_proba,
                average="macro",
                multi_class="ovr",
                labels=[0, 1, 2],
            )
        except ValueError:
            auc = np.nan

        results.append({
            "subject": test_subject,
            "accuracy": acc,
            "precision": prec,
            "recall": rec,
            "f1_macro": f1,
            "roc_auc": auc,
        })

        all_true.extend([inv_label_map[y] for y in y_test])
        all_pred.extend([inv_label_map[y] for y in y_pred])

        print(f"  [LSTM-tuned] Test subject {test_subject}: Acc={acc:.3f}, F1={f1:.3f}")

        keras.backend.clear_session()

    results_df = pd.DataFrame(results)
    cm = confusion_matrix(all_true, all_pred, labels=[1, 2, 3])
    return results_df, cm


def plot_confusion_matrix(cm, model_name="LSTM_tuned"):
    plt.figure(figsize=(5, 4))
    labels = [LABEL_NAMES[i] for i in [1, 2, 3]]
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=labels, yticklabels=labels)
    plt.title(f"{model_name} — Aggregated Confusion Matrix (LOSO)")
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.tight_layout()
    path = os.path.join(NOTEBOOKS_DIR, f"confusion_matrix_{model_name.lower()}.png")
    plt.savefig(path, dpi=150)
    print(f"Saved {path}")
    plt.close()


if __name__ == "__main__":
    tuned_cfg = load_tuned_config()

    print("\nLoading sequence data...")
    sequences, labels, subjects = load_data()
    print(f"Loaded {sequences.shape[0]} windows, {len(np.unique(subjects))} subjects\n")

    print("Running TUNED LSTM (LOSO) — this will take a while (15 folds)...\n")
    lstm_results, lstm_cm = loso_evaluate(sequences, labels, subjects, tuned_cfg)

    lstm_results.to_csv(os.path.join(OUT_DIR, "lstm_loso_results_tuned.csv"), index=False)
    plot_confusion_matrix(lstm_cm, "LSTM_tuned")

    print("\n" + "=" * 50)
    print("TUNED LSTM SUMMARY (mean across all 15 LOSO folds)")
    print("=" * 50)
    summary = lstm_results[["accuracy", "precision", "recall", "f1_macro"]].mean()
    print(summary.round(3))

    # Compare directly against the original untuned LSTM results, if present
    original_path = os.path.join(OUT_DIR, "lstm_loso_results.csv")
    if os.path.exists(original_path):
        original = pd.read_csv(original_path)
        original_summary = original[["accuracy", "precision", "recall", "f1_macro"]].mean()
        comparison = pd.DataFrame({"LSTM_original": original_summary, "LSTM_tuned": summary})
        comparison["improvement"] = comparison["LSTM_tuned"] - comparison["LSTM_original"]
        print("\nComparison: original (untuned) vs tuned LSTM")
        print(comparison.round(3))
        comparison.to_csv(os.path.join(OUT_DIR, "lstm_tuned_vs_original_comparison.csv"))
        print(f"\nSaved comparison to {OUT_DIR}/lstm_tuned_vs_original_comparison.csv")
    else:
        print("\n(No original lstm_loso_results.csv found to compare against.)")
