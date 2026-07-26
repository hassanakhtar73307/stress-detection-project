"""
auth.py
Token-based authentication using itsdangerous (already installed as a Flask
dependency -- no new pip package required). Tokens are signed and expire,
similar in spirit to a JWT, verified on every protected request.
"""
from functools import wraps

from flask import request, jsonify
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import generate_password_hash, check_password_hash

import database

SECRET_KEY = "stress-detection-project-dev-secret-change-in-production"
TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24  # 24 hours

serializer = URLSafeTimedSerializer(SECRET_KEY)


def hash_password(plain_password):
    return generate_password_hash(plain_password)


def verify_password(plain_password, password_hash):
    return check_password_hash(password_hash, plain_password)


def generate_token(user_id):
    return serializer.dumps({"user_id": user_id})


def verify_token(token):
    """Returns user_id if valid, raises ValueError otherwise."""
    try:
        data = serializer.loads(token, max_age=TOKEN_MAX_AGE_SECONDS)
        return data["user_id"]
    except SignatureExpired:
        raise ValueError("Token has expired, please log in again")
    except BadSignature:
        raise ValueError("Invalid token")


def login_required(f):
    """Decorator: protects a Flask route, requiring a valid Bearer token.
    Injects the authenticated user's id as `request.user_id`."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
        token = auth_header.split("Bearer ", 1)[1]
        try:
            user_id = verify_token(token)
        except ValueError as e:
            return jsonify({"error": str(e)}), 401
        user = database.get_user_by_id(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 401
        request.user_id = user_id
        request.current_user = user
        return f(*args, **kwargs)
    return wrapper
