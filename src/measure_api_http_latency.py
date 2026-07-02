"""
measure_api_http_latency.py
Measures real end-to-end HTTP latency against the LIVE Flask API,
over 100 consecutive real requests — not a direct model call.
This is what the project execution guide's Week 13 requirement asks for.
"""
import time
import json
import requests
import pandas as pd
import numpy as np

API_URL = "http://127.0.0.1:5000/predict"
N_REQUESTS = 100

df = pd.read_csv("data/processed/features_traditional.csv")
feature_cols = [c for c in df.columns if c not in ("subject", "label")]
sample_row = df[feature_cols].iloc[0].to_dict()
payload = {"features": sample_row}

# Warm-up request (exclude from timing, avoids first-request JIT/connection overhead)
requests.post(API_URL, json=payload)

times = []
errors = 0
for i in range(N_REQUESTS):
    t0 = time.perf_counter()
    try:
        r = requests.post(API_URL, json=payload, timeout=5)
        r.raise_for_status()
    except Exception as e:
        errors += 1
        continue
    times.append((time.perf_counter() - t0) * 1000)  # ms

times = np.array(times)
print(f"Completed {len(times)}/{N_REQUESTS} successful requests ({errors} errors)")
print(f"Mean:   {times.mean():.2f} ms")
print(f"Median: {np.median(times):.2f} ms")
print(f"P95:    {np.percentile(times, 95):.2f} ms")
print(f"Min:    {times.min():.2f} ms")
print(f"Max:    {times.max():.2f} ms")

pd.DataFrame({"request_number": range(1, len(times)+1), "latency_ms": times}).to_csv(
    "models/api_http_latency_results.csv", index=False
)
print("Saved models/api_http_latency_results.csv")