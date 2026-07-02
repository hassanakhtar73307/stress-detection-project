"""
train_final_models.py
Trains final RF, XGBoost, and LSTM models on ALL subjects (no LOSO holdout)
and saves them to disk for latency measurement and web app deployment.
"""
import os
import time
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.utils.class_weight import compute_class_weight
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

OUT_DIR = "models"
os.makedirs(OUT_DIR, exist_ok=True)

# ============================================================
# 1. Random Forest + XGBoost
# ============================================================
FEATURES_PATH = "data/processed/features_traditional.csv"

def load_traditional_data():
    df = pd.read_csv(FEATURES_PATH)
    feature_cols = [c for c in df.columns if c not in ("subject", "label")]
    return df, feature_cols

print("Loading traditional feature data...")
df, feature_cols = load_traditional_data()
X_feat = df[feature_cols].values
y_feat = df["label"].values
print(f"  X_feat shape: {X_feat.shape}, classes: {np.unique(y_feat)}")

print("\nTraining final Random Forest on all subjects...")
t0 = time.time()
rf = RandomForestClassifier(n_estimators=300, max_depth=15, random_state=42)
rf.fit(X_feat, y_feat)
print(f"  RF trained in {time.time() - t0:.2f}s")
joblib.dump(rf, os.path.join(OUT_DIR, "rf_final.joblib"))
print(f"  Saved {OUT_DIR}/rf_final.joblib")

print("\nTraining final XGBoost on all subjects...")
t0 = time.time()
y_feat_xgb = y_feat - 1  # matches train_traditional_models.py's remapping
xgb = XGBClassifier(
    n_estimators=300, max_depth=6, learning_rate=0.1,
    eval_metric="mlogloss", random_state=42
)
xgb.fit(X_feat, y_feat_xgb)
print(f"  XGBoost trained in {time.time() - t0:.2f}s")
joblib.dump(xgb, os.path.join(OUT_DIR, "xgb_final.joblib"))
print(f"  Saved {OUT_DIR}/xgb_final.joblib")

# ============================================================
# 2. LSTM
# ============================================================
SEQ_DATA_PATH = "data/processed/sequences_lstm.npz"
DOWNSAMPLE_FACTOR = 100

def load_sequence_data():
    data = np.load(SEQ_DATA_PATH, allow_pickle=True)
    sequences = data["sequences"][:, ::DOWNSAMPLE_FACTOR, :]
    return sequences, data["labels"], data["subjects"]

def build_model(input_shape, n_classes=3):
    model = keras.Sequential([
        layers.Input(shape=input_shape),
        layers.LSTM(32, return_sequences=True),
        layers.Dropout(0.3),
        layers.LSTM(32),
        layers.Dropout(0.3),
        layers.Dense(n_classes, activation="softmax"),
    ])
    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    return model

print("\nLoading LSTM sequence data...")
sequences, labels, subjects = load_sequence_data()
print(f"  sequences shape: {sequences.shape}")

y_seq = labels - 1
classes = np.unique(y_seq)
weights = compute_class_weight("balanced", classes=classes, y=y_seq)
class_weight = {c: w for c, w in zip(classes, weights)}
print(f"  class weights: {class_weight}")

early_stop = keras.callbacks.EarlyStopping(monitor="loss", patience=5, restore_best_weights=True)

print("\nTraining final LSTM on all subjects...")
t0 = time.time()
lstm_model = build_model(input_shape=sequences.shape[1:])
lstm_model.fit(
    sequences, y_seq,
    epochs=25,
    batch_size=32,
    callbacks=[early_stop],
    class_weight=class_weight,
    verbose=0,
)
print(f"  LSTM trained in {time.time() - t0:.2f}s")
lstm_model.save(os.path.join(OUT_DIR, "lstm_final.h5"))
print(f"  Saved {OUT_DIR}/lstm_final.h5")

print("\nAll final models trained and saved.")