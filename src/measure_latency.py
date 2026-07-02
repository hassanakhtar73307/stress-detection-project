"""
measure_latency.py
Loads the three final trained models and measures inference latency
over 100 consecutive predictions each, on a single sample — mirrors
the real-time single-request pattern the Flask API will use later.
"""
import time
import joblib
import numpy as np
import pandas as pd
from tensorflow import keras

N_RUNS = 100

# --- Load one sample input for each model type ---
df = pd.read_csv("data/processed/features_traditional.csv")
feature_cols = [c for c in df.columns if c not in ("subject", "label")]
X_sample_feat = df[feature_cols].values[[0]]  # single row, shape (1, n_features)

seq_data = np.load("data/processed/sequences_lstm.npz", allow_pickle=True)
X_sample_seq = seq_data["sequences"][:, ::100, :][[0]]  # single window, downsampled

def measure(predict_fn, X, n_runs=N_RUNS):
    # warm-up run (JIT/graph build overhead shouldn't count)
    predict_fn(X)
    times = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        predict_fn(X)
        times.append((time.perf_counter() - t0) * 1000)  # ms
    times = np.array(times)
    return {
        "mean_ms": times.mean(),
        "median_ms": np.median(times),
        "p95_ms": np.percentile(times, 95),
        "min_ms": times.min(),
        "max_ms": times.max(),
    }

results = {}

print("Measuring Random Forest latency...")
rf = joblib.load("models/rf_final.joblib")
results["Random Forest"] = measure(lambda X: rf.predict(X), X_sample_feat)

print("Measuring XGBoost latency...")
xgb = joblib.load("models/xgb_final.joblib")
results["XGBoost"] = measure(lambda X: xgb.predict(X), X_sample_feat)

print("Measuring LSTM latency...")
lstm = keras.models.load_model("models/lstm_final.h5")
results["LSTM"] = measure(lambda X: lstm.predict(X, verbose=0), X_sample_seq)

print("\n" + "=" * 60)
print(f"INFERENCE LATENCY (single-sample prediction, n={N_RUNS} runs)")
print("=" * 60)
results_df = pd.DataFrame(results).T
print(results_df.round(3))

results_df.to_csv("models/latency_results.csv")
print("\nSaved models/latency_results.csv")