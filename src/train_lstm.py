"""
train_lstm.py
Trains an LSTM under Leave-One-Subject-Out (LOSO) cross-validation
on the WESAD sequence data (raw, normalised, windowed chest signals).
Saves per-subject results and a comparison against RF/XGBoost.
"""

import os
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.utils.class_weight import compute_class_weight

DATA_PATH = "data/processed/sequences_lstm.npz"
OUT_DIR = "models"
NOTEBOOKS_DIR = "notebooks"
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(NOTEBOOKS_DIR, exist_ok=True)

LABEL_NAMES = {1: "Baseline", 2: "Stress", 3: "Amusement"}

DOWNSAMPLE_FACTOR = 100  # take every 100th sample: 42000 -> 420 timesteps


def load_data():
    data = np.load(DATA_PATH, allow_pickle=True)
    sequences = data["sequences"][:, ::DOWNSAMPLE_FACTOR, :]
    return sequences, data["labels"], data["subjects"]


def build_model(input_shape, n_classes=3):
    model = keras.Sequential([
        layers.Input(shape=input_shape),
        layers.LSTM(32, return_sequences=True),
        layers.Dropout(0.3),
        layers.LSTM(16),
        layers.Dropout(0.3),
        layers.Dense(16, activation="relu"),
        layers.Dense(n_classes, activation="softmax"),
    ])
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def loso_evaluate(sequences, labels, subjects):
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

        model = build_model(input_shape=X_train.shape[1:])

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

        results.append({
            "subject": test_subject, "accuracy": acc, "precision": prec,
            "recall": rec, "f1_macro": f1
        })

        all_true.extend([inv_label_map[y] for y in y_test])
        all_pred.extend([inv_label_map[y] for y in y_pred])

        print(f"  [LSTM] Test subject {test_subject}: Acc={acc:.3f}, F1={f1:.3f}")
        print(f"    unique predicted classes: {np.unique(y_pred)}")

        keras.backend.clear_session()

    results_df = pd.DataFrame(results)
    cm = confusion_matrix(all_true, all_pred, labels=[1, 2, 3])

    return results_df, cm


def plot_confusion_matrix(cm, model_name="LSTM"):
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
    print("Loading sequence data...")
    sequences, labels, subjects = load_data()
    print(f"Loaded {sequences.shape[0]} windows, shape per window: {sequences.shape[1:]}, {len(np.unique(subjects))} subjects\n")

    print("Running LSTM (LOSO) — this will take a while (15 folds)...\n")
    lstm_results, lstm_cm = loso_evaluate(sequences, labels, subjects)

    lstm_results.to_csv(os.path.join(OUT_DIR, "lstm_loso_results.csv"), index=False)
    plot_confusion_matrix(lstm_cm, "LSTM")

    print("\n" + "=" * 50)
    print("LSTM SUMMARY (mean across all 15 LOSO folds)")
    print("=" * 50)
    summary = lstm_results[["accuracy", "precision", "recall", "f1_macro"]].mean()
    print(summary.round(3))

    comparison_path = os.path.join(OUT_DIR, "model_comparison_summary.csv")
    if os.path.exists(comparison_path):
        existing = pd.read_csv(comparison_path, index_col=0)
        existing.loc["LSTM"] = summary
        existing.to_csv(comparison_path)
        print(f"\nUpdated comparison table saved to {comparison_path}")
        print(existing.round(3))
    else:
        pd.DataFrame({"LSTM": summary}).T.to_csv(comparison_path)
        print(f"\nSaved comparison table to {comparison_path}")