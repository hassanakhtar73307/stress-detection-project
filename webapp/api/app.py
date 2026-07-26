"""
webapp/api/app.py
Flask API serving the final XGBoost stress detection model.
Run from the project root: python webapp\api\app.py
"""
import os
import re
import sys

import joblib
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import database
import auth

app = Flask(__name__)
CORS(app)

database.init_db()

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

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

@app.route("/register", methods=["POST"])
def register():
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    age = body.get("age")
    occupation = (body.get("occupation") or "").strip()

    if not name or not email or not password:
        return jsonify({"error": "name, email, and password are required"}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"error": "Invalid email format"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    if database.get_user_by_email(email):
        return jsonify({"error": "An account with this email already exists"}), 409

    try:
        age = int(age) if age not in (None, "") else None
    except (ValueError, TypeError):
        return jsonify({"error": "Age must be a number"}), 400

    password_hash = auth.hash_password(password)
    user_id = database.create_user(name, email, password_hash, age, occupation)
    token = auth.generate_token(user_id)

    return jsonify({
        "token": token,
        "user": {"id": user_id, "name": name, "email": email, "age": age, "occupation": occupation},
    }), 201

@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    user = database.get_user_by_email(email)
    if not user or not auth.verify_password(password, user["password_hash"]):
        return jsonify({"error": "Invalid email or password"}), 401

    token = auth.generate_token(user["id"])
    return jsonify({
        "token": token,
        "user": {
            "id": user["id"], "name": user["name"], "email": user["email"],
            "age": user["age"], "occupation": user["occupation"],
        },
    })

@app.route("/profile", methods=["GET"])
@auth.login_required
def get_profile():
    user = request.current_user
    return jsonify({
        "id": user["id"], "name": user["name"], "email": user["email"],
        "age": user["age"], "occupation": user["occupation"],
    })

@app.route("/profile", methods=["PUT"])
@auth.login_required
def update_profile():
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or request.current_user["name"]).strip()
    occupation = (body.get("occupation") or request.current_user["occupation"] or "").strip()
    age = body.get("age", request.current_user["age"])
    try:
        age = int(age) if age not in (None, "") else None
    except (ValueError, TypeError):
        return jsonify({"error": "Age must be a number"}), 400

    database.update_user_profile(request.user_id, name, age, occupation)
    return jsonify({
        "id": request.user_id, "name": name, "email": request.current_user["email"],
        "age": age, "occupation": occupation,
    })

@app.route("/predict", methods=["POST"])
@auth.login_required
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