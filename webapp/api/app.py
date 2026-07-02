"""
webapp/api/app.py
Flask API serving the final XGBoost stress detection model.
Run from the project root: python webapp\api\app.py
"""
import os
import joblib
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Resolve paths relative to project root regardless of where this is launched from
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODEL_PATH = os.path.join(BASE_DIR, "models", "xgb_final.joblib")
FEATURES_PATH = os.path.join(BASE_DIR, "data", "processed", "features_traditional.csv")

print("Loading model and feature schema...")
model = joblib.load(MODEL_PATH)
feature_cols = [c for c in pd.read_csv(FEATURES_PATH, nrows=1).columns if c not in ("subject", "label")]
print(f"  Loaded model. Expecting {len(feature_cols)} features.")

LABEL_NAMES = {0: "Baseline", 1: "Stress", 2: "Amusement"}  # 0-indexed, matches xgb training

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "n_features_expected": len(feature_cols)})

@app.route("/predict", methods=["POST"])
def predict():
    body = request.get_json(silent=True)
    if body is None or "features" not in body:
        return jsonify({"error": "Request body must be JSON with a 'features' key"}), 400

    features = body["features"]

    # Accept either a dict {feature_name: value} or an ordered list of 45 floats
    if isinstance(features, dict):
        missing = [c for c in feature_cols if c not in features]
        if missing:
            return jsonify({"error": f"Missing features: {missing[:5]}{'...' if len(missing) > 5 else ''}"}), 400
        x = np.array([[features[c] for c in feature_cols]])
    elif isinstance(features, list):
        if len(features) != len(feature_cols):
            return jsonify({"error": f"Expected {len(feature_cols)} features, got {len(features)}"}), 400
        x = np.array([features])
    else:
        return jsonify({"error": "'features' must be a list or a dict"}), 400

    pred_class = int(model.predict(x)[0])
    proba = model.predict_proba(x)[0].tolist()

    return jsonify({
        "predicted_class": pred_class,
        "predicted_label": LABEL_NAMES[pred_class],
        "confidence": round(max(proba), 4),
        "probabilities": {LABEL_NAMES[i]: round(p, 4) for i, p in enumerate(proba)}
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)