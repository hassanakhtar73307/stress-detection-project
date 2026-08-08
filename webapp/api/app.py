"""
Flask API serving the trained XGBoost and Random Forest stress-detection
models, user accounts, model insights, and prediction history.

Run from the project root:
    python webapp\api\app.py
"""
import os
import re
import sys
import time

import joblib
import numpy as np
import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import auth
import database

app = Flask(__name__)
CORS(app)

database.init_db()

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PASSWORD_LETTER_RE = re.compile(r"[A-Za-z]")
PASSWORD_NUMBER_RE = re.compile(r"\d")

VALID_USER_TYPES = {
    "student",
    "employed",
    "self_employed",
    "researcher",
    "not_working",
    "other",
}
VALID_PRIMARY_GOALS = {
    "study_stress",
    "work_stress",
    "general_wellbeing",
    "research_demo",
    "other",
}
VALID_WEARABLE_DEVICES = {
    "none",
    "smartwatch",
    "chest_sensor",
    "other",
}

ADMIN_EMAILS = {
    email.strip().lower()
    for email in os.environ.get("ADMIN_EMAILS", "").split(",")
    if email.strip()
}


def is_admin_user(user):
    return bool(user and (user.get("email") or "").lower() in ADMIN_EMAILS)

# Resolve paths relative to project root regardless of launch directory.
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODEL_PATHS = {
    "xgboost": os.path.join(BASE_DIR, "models", "xgb_final.joblib"),
    "random_forest": os.path.join(BASE_DIR, "models", "rf_final.joblib"),
    "boost_forest": os.path.join(
        BASE_DIR,
        "models",
        "boost_forest_final.joblib",
    ),
}

DEFAULT_MODEL_NAME = "xgboost"

MODEL_DISPLAY_NAMES = {
    "xgboost": "XGBoost",
    "random_forest": "Random Forest",
    "boost_forest": "Boost Forest",
}

MODEL_INSIGHT_FILES = {
    "xgboost": {
        "sensor_file": "xgboost_feature_importance_by_sensor.csv",
        "feature_file": "xgboost_feature_importance.csv",
    },
    "random_forest": {
        "sensor_file": "random_forest_feature_importance_by_sensor.csv",
        "feature_file": "random_forest_feature_importance.csv",
    },
    "boost_forest": {
        "sensor_file": "boost_forest_feature_importance_by_sensor.csv",
        "feature_file": "boost_forest_feature_importance.csv",
        "note": (
            "Boost Forest global importance is an ensemble-level approximation "
            "formed from the normalized XGBoost and Random Forest global "
            "feature importances. The contribution weights are derived from "
            "the final class-specific blend and macro-averaged across the "
            "three classes. It is not a per-prediction explanation."
        ),
    },
}

FEATURES_PATH = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "features_traditional.csv",
)

print("Loading traditional models and feature schema...")

traditional_models = {
    model_name: joblib.load(model_path)
    for model_name, model_path in MODEL_PATHS.items()
}

feature_cols = [
    column
    for column in pd.read_csv(FEATURES_PATH, nrows=1).columns
    if column not in ("subject", "label")
]
print(f"  Loaded model. Expecting {len(feature_cols)} features.")

LABEL_NAMES = {0: "Baseline", 1: "Stress", 2: "Amusement"}


def normalize_model_class(model_name, raw_class):
    """Convert a model-specific class value to the shared 0-2 label index."""
    normalized_class = int(raw_class)

    # Random Forest was trained on labels 1, 2, 3, while XGBoost was trained
    # on remapped labels 0, 1, 2.
    if model_name == "random_forest":
        normalized_class -= 1

    if normalized_class not in LABEL_NAMES:
        raise ValueError(
            f"Model '{model_name}' returned unsupported class {raw_class}"
        )

    return normalized_class


def serialize_user(user):
    """Return the safe account profile without the password hash."""
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "age": user.get("age"),
        "occupation": user.get("occupation") or "",
        "user_type": user.get("user_type") or "",
        "primary_goal": user.get("primary_goal") or "",
        "wearable_device": user.get("wearable_device") or "",
        "research_notice_acknowledged": bool(user.get("research_notice_acknowledged")),
        "login_count": int(user.get("login_count") or 0),
        "last_login_at": user.get("last_login_at"),
        "created_at": user.get("created_at"),
        "updated_at": user.get("updated_at"),
        "is_admin": is_admin_user(user),
    }


def parse_age(value):
    if value in (None, ""):
        return None
    try:
        age = int(value)
    except (ValueError, TypeError) as exc:
        raise ValueError("Age must be a whole number") from exc
    if age < 16 or age > 120:
        raise ValueError("Age must be between 16 and 120")
    return age


def validate_password(password):
    if len(password) < 8:
        return "Password must be at least 8 characters"
    if not PASSWORD_LETTER_RE.search(password) or not PASSWORD_NUMBER_RE.search(password):
        return "Password must include at least one letter and one number"
    return None


def validate_choice(value, allowed, label, required=False):
    value = (value or "").strip()
    if required and not value:
        raise ValueError(f"{label} is required")
    if value and value not in allowed:
        raise ValueError(f"Invalid {label.lower()} selection")
    return value


@app.route("/", methods=["GET"])
def service_info():
    return jsonify(
        {
            "service": "Stress Monitor API",
            "status": "ok",
            "health_check": "/health",
            "n_features_expected": len(feature_cols),
            "database": database.database_status(),
            "default_model": DEFAULT_MODEL_NAME,
            "available_models": list(traditional_models.keys()),
        }
    )


@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "n_features_expected": len(feature_cols),
            "database": database.database_status(),
            "default_model": DEFAULT_MODEL_NAME,
            "available_models": list(traditional_models.keys()),
        }
    )


@app.route("/register", methods=["POST"])
def register():
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    occupation = (body.get("occupation") or "").strip()
    notice_acknowledged = body.get("research_notice_acknowledged") is True

    if not name or not email or not password:
        return jsonify({"error": "Full name, email, and password are required"}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"error": "Enter a valid email address"}), 400

    password_error = validate_password(password)
    if password_error:
        return jsonify({"error": password_error}), 400

    if database.get_user_by_email(email):
        return jsonify({"error": "An account with this email already exists"}), 409

    if not notice_acknowledged:
        return jsonify(
            {
                "error": (
                    "Please acknowledge that this is a research prototype and not medical advice"
                )
            }
        ), 400

    try:
        age = parse_age(body.get("age"))
        user_type = validate_choice(
            body.get("user_type"), VALID_USER_TYPES, "Current routine", required=True
        )
        primary_goal = validate_choice(
            body.get("primary_goal"), VALID_PRIMARY_GOALS, "Main reason", required=True
        )
        wearable_device = validate_choice(
            body.get("wearable_device"),
            VALID_WEARABLE_DEVICES,
            "Sensor or wearable access",
            required=True,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    password_hash = auth.hash_password(password)
    user_id = database.create_user(
        name=name,
        email=email,
        password_hash=password_hash,
        age=age,
        occupation=occupation,
        user_type=user_type,
        primary_goal=primary_goal,
        wearable_device=wearable_device,
        research_notice_acknowledged=True,
    )
    user = database.get_user_by_id(user_id)
    token = auth.generate_token(user_id)

    return jsonify({"token": token, "user": serialize_user(user)}), 201


@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = database.get_user_by_email(email)
    if not user or not auth.verify_password(password, user["password_hash"]):
        return jsonify({"error": "Invalid email or password"}), 401

    database.record_login(user["id"])
    user = database.get_user_by_id(user["id"])
    token = auth.generate_token(user["id"])
    return jsonify({"token": token, "user": serialize_user(user)})


@app.route("/profile", methods=["GET"])
@auth.login_required
def get_profile():
    return jsonify(serialize_user(request.current_user))


@app.route("/profile", methods=["PUT"])
@auth.login_required
def update_profile():
    body = request.get_json(silent=True) or {}
    current_user = request.current_user

    name = (body.get("name") or current_user["name"]).strip()
    occupation = (
        body.get("occupation")
        if "occupation" in body
        else current_user.get("occupation")
    )
    occupation = (occupation or "").strip()

    if not name:
        return jsonify({"error": "Full name is required"}), 400

    try:
        age = parse_age(body.get("age", current_user.get("age")))
        user_type = validate_choice(
            body.get("user_type", current_user.get("user_type")),
            VALID_USER_TYPES,
            "Current routine",
        )
        primary_goal = validate_choice(
            body.get("primary_goal", current_user.get("primary_goal")),
            VALID_PRIMARY_GOALS,
            "Main reason",
        )
        wearable_device = validate_choice(
            body.get("wearable_device", current_user.get("wearable_device")),
            VALID_WEARABLE_DEVICES,
            "Sensor or wearable access",
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    database.update_user_profile(
        user_id=request.user_id,
        name=name,
        age=age,
        occupation=occupation,
        user_type=user_type,
        primary_goal=primary_goal,
        wearable_device=wearable_device,
    )
    updated_user = database.get_user_by_id(request.user_id)
    return jsonify(serialize_user(updated_user))


@app.route("/forgot-password", methods=["POST"])
def forgot_password():
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Email is required"}), 400

    user = database.get_user_by_email(email)
    # Return the same response whether or not the account exists to avoid
    # revealing which email addresses are registered.
    if user:
        reset_token = auth.generate_reset_token(email)
        auth.send_reset_email(email, reset_token)

    return jsonify(
        {
            "message": (
                "If an account exists for that email, a reset code has been generated. "
                "During local testing, check the Flask terminal for the code."
            )
        }
    )


@app.route("/reset-password", methods=["POST"])
def reset_password():
    body = request.get_json(silent=True) or {}
    token = body.get("token") or ""
    new_password = body.get("new_password") or ""

    if not token or not new_password:
        return jsonify({"error": "Reset code and new password are required"}), 400

    password_error = validate_password(new_password)
    if password_error:
        return jsonify({"error": password_error}), 400

    try:
        email = auth.verify_reset_token(token)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    user = database.get_user_by_email(email)
    if not user:
        return jsonify({"error": "No account was found for this reset code"}), 404

    database.update_password_by_email(email, auth.hash_password(new_password))
    return jsonify({"message": "Password updated successfully. You can now sign in."})


def require_admin():
    if not is_admin_user(request.current_user):
        return jsonify({"error": "Administrator access is required"}), 403
    return None


@app.route("/admin/overview", methods=["GET"])
@auth.login_required
def admin_overview():
    denied = require_admin()
    if denied:
        return denied
    return jsonify(database.admin_overview())


@app.route("/admin/users", methods=["GET"])
@auth.login_required
def admin_users():
    denied = require_admin()
    if denied:
        return denied
    limit = request.args.get("limit", 200)
    try:
        users_list = database.list_users(limit=limit)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid limit"}), 400
    return jsonify({"users": users_list, "count": len(users_list)})


@app.route("/admin/predictions", methods=["GET"])
@auth.login_required
def admin_predictions():
    denied = require_admin()
    if denied:
        return denied
    limit = request.args.get("limit", 200)
    try:
        rows = database.list_predictions(limit=limit)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid limit"}), 400
    return jsonify({"predictions": rows, "count": len(rows)})


@app.route("/model-insights", methods=["GET"])
def model_insights():
    """Return global feature-importance data for the selected model."""
    requested_model = (
        request.args.get("model_name") or DEFAULT_MODEL_NAME
    ).strip().lower()

    if requested_model not in MODEL_INSIGHT_FILES:
        return (
            jsonify(
                {
                    "error": "Unsupported model",
                    "available_models": list(MODEL_INSIGHT_FILES.keys()),
                }
            ),
            400,
        )

    config = MODEL_INSIGHT_FILES[requested_model]

    by_sensor_path = os.path.join(
        BASE_DIR,
        "models",
        config["sensor_file"],
    )
    top_features_path = os.path.join(
        BASE_DIR,
        "models",
        config["feature_file"],
    )

    if not os.path.exists(by_sensor_path) or not os.path.exists(
        top_features_path
    ):
        return (
            jsonify(
                {
                    "available": False,
                    "model_name": requested_model,
                    "display_name": MODEL_DISPLAY_NAMES[requested_model],
                    "message": (
                        "Run src/feature_importance.py to generate "
                        "the model insight data."
                    ),
                }
            ),
            404,
        )

    by_sensor = pd.read_csv(by_sensor_path)
    top_features = pd.read_csv(top_features_path).head(10)

    required_sensor_columns = {"sensor", "importance_pct"}
    if not required_sensor_columns.issubset(by_sensor.columns):
        return (
            jsonify(
                {
                    "available": False,
                    "model_name": requested_model,
                    "error": (
                        "The sensor-importance file has an invalid schema."
                    ),
                }
            ),
            500,
        )

    return jsonify(
        {
            "available": True,
            "model_name": requested_model,
            "display_name": MODEL_DISPLAY_NAMES[requested_model],
            "by_sensor": by_sensor.to_dict(orient="records"),
            "top_features": top_features.to_dict(orient="records"),
            "note": config.get("note"),
        }
    )


@app.route("/predict", methods=["POST"])
@auth.login_required
def predict():
    body = request.get_json(silent=True)

    if body is None or "features" not in body:
        return (
            jsonify(
                {
                    "error": (
                        "Request body must be JSON with a 'features' key"
                    )
                }
            ),
            400,
        )

    features = body["features"]

    requested_model = (
        body.get("model_name") or DEFAULT_MODEL_NAME
    ).strip().lower()

    if requested_model not in traditional_models:
        return (
            jsonify(
                {
                    "error": "Unsupported model",
                    "available_models": list(traditional_models.keys()),
                }
            ),
            400,
        )

    selected_model = traditional_models[requested_model]

    if isinstance(features, dict):
        missing = [
            column
            for column in feature_cols
            if column not in features
        ]

        if missing:
            suffix = "..." if len(missing) > 5 else ""
            return (
                jsonify(
                    {
                        "error": (
                            f"Missing features: {missing[:5]}{suffix}"
                        )
                    }
                ),
                400,
            )

        x = np.array(
            [[features[column] for column in feature_cols]]
        )

    elif isinstance(features, list):
        if len(features) != len(feature_cols):
            return (
                jsonify(
                    {
                        "error": (
                            f"Expected {len(feature_cols)} features, "
                            f"got {len(features)}"
                        )
                    }
                ),
                400,
            )

        x = np.array([features])

    else:
        return (
            jsonify(
                {
                    "error": (
                        "'features' must be a list or a dictionary"
                    )
                }
            ),
            400,
        )

    prediction_start = time.perf_counter()

    if requested_model == "boost_forest":
        rf_model = selected_model["rf_model"]
        xgb_model = selected_model["xgb_model"]
        xgb_weights = np.asarray(
            selected_model["xgb_class_weights"],
            dtype=float,
        ).reshape(1, 3)

        rf_probabilities = rf_model.predict_proba(x)
        xgb_probabilities = xgb_model.predict_proba(x)

        blended_probabilities = (
            xgb_weights * xgb_probabilities
            + (1.0 - xgb_weights) * rf_probabilities
        )

        probability_sum = blended_probabilities.sum(
            axis=1,
            keepdims=True,
        )
        probability_sum[probability_sum == 0] = 1.0
        blended_probabilities = (
            blended_probabilities / probability_sum
        )

        raw_probabilities = blended_probabilities[0]
        pred_class = int(np.argmax(raw_probabilities))
        raw_classes = np.arange(3)

    else:
        raw_pred_class = selected_model.predict(x)[0]
        pred_class = normalize_model_class(
            requested_model,
            raw_pred_class,
        )

        raw_probabilities = selected_model.predict_proba(x)[0]
        raw_classes = getattr(
            selected_model,
            "classes_",
            np.arange(len(raw_probabilities)),
        )

    processing_time_ms = round(
        (time.perf_counter() - prediction_start) * 1000,
        3,
    )

    probabilities = {
        label_name: 0.0
        for label_name in LABEL_NAMES.values()
    }

    if requested_model == "boost_forest":
        for class_index, probability in enumerate(
            raw_probabilities
        ):
            probabilities[LABEL_NAMES[class_index]] = round(
                float(probability),
                4,
            )
    else:
        for raw_class, probability in zip(
            raw_classes,
            raw_probabilities,
        ):
            normalized_class = normalize_model_class(
                requested_model,
                raw_class,
            )
            probabilities[LABEL_NAMES[normalized_class]] = round(
                float(probability),
                4,
            )

    predicted_label = LABEL_NAMES[pred_class]
    confidence = round(float(max(raw_probabilities)), 4)

    benchmark_mode = body.get("benchmark_mode") is True

    if benchmark_mode:
        denied = require_admin()
        if denied:
            return denied

    prediction_id = None

    if not benchmark_mode:
        prediction_id = database.create_prediction(
            user_id=request.user_id,
            model_name=requested_model,
            comparison_id=(body.get("comparison_id") or "")[:80] or None,
            processing_time_ms=processing_time_ms,
            sample_id=(body.get("sample_id") or "")[:80] or None,
            source_participant_id=(
                body.get("participant_id") or ""
            )[:30] or None,
            expected_label=(
                body.get("expected_label") or ""
            )[:40] or None,
            predicted_label=predicted_label,
            confidence=confidence,
            probabilities=probabilities,
        )

    return jsonify(
        {
            "prediction_id": prediction_id,
	    "benchmark_mode": benchmark_mode,
            "model_name": requested_model,
            "model_display_name": MODEL_DISPLAY_NAMES[requested_model],
            "predicted_class": pred_class,
            "predicted_label": predicted_label,
            "confidence": confidence,
            "probabilities": probabilities,
            "processing_time_ms": processing_time_ms,
        }
    )
if __name__ == "__main__":
    app.run(debug=True, port=5000)