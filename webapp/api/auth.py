"""
auth.py
Token-based authentication using itsdangerous (already installed as a Flask
dependency -- no new pip package required). Tokens are signed and expire,
similar in spirit to a JWT, verified on every protected request.
"""
import os
import smtplib
from email.mime.text import MIMEText
from functools import wraps

from flask import request, jsonify
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import generate_password_hash, check_password_hash

import database

SECRET_KEY = os.environ.get("SECRET_KEY", "stress-detection-project-dev-secret-change-in-production")
TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24  # 24 hours
RESET_TOKEN_MAX_AGE_SECONDS = 60 * 30  # 30 minutes, shorter-lived than login tokens

serializer = URLSafeTimedSerializer(SECRET_KEY)
reset_serializer = URLSafeTimedSerializer(SECRET_KEY, salt="password-reset")

# Optional real SMTP config -- if these env vars are not set, reset links are
# printed to the Flask console instead of emailed. This is a deliberate,
# documented simplification for a development/dissertation prototype that
# has no production mail server.
SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")
FROM_EMAIL = os.environ.get("FROM_EMAIL", SMTP_USER or "noreply@stress-monitor.local")


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


def generate_reset_token(email):
    return reset_serializer.dumps({"email": email})


def verify_reset_token(token):
    """Returns email if valid, raises ValueError otherwise."""
    try:
        data = reset_serializer.loads(token, max_age=RESET_TOKEN_MAX_AGE_SECONDS)
        return data["email"]
    except SignatureExpired:
        raise ValueError("This reset link has expired, please request a new one")
    except BadSignature:
        raise ValueError("Invalid or tampered reset link")


def send_email(to_email, subject, body):
    """Sends a real email if SMTP is configured; otherwise prints the message
    to the Flask console. Returns True if actually emailed, False if it fell
    back to console output."""
    if SMTP_HOST and SMTP_USER and SMTP_PASS:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = FROM_EMAIL
        msg["To"] = to_email
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
            print(f"[auth] Email sent to {to_email}: {subject}")
            return True
        except Exception as e:
            print(f"[auth] Failed to send email ({e}); falling back to console output")

    print("\n" + "=" * 60)
    print(f"EMAIL (no SMTP configured or send failed -- shown here instead)")
    print(f"To: {to_email}")
    print(f"Subject: {subject}")
    print(body)
    print("=" * 60 + "\n")
    return False


def send_reset_email(to_email, reset_token):
    body = (
        f"A password reset was requested for {to_email}.\n\n"
        f"Your reset code is:\n\n{reset_token}\n\n"
        f"This code expires in 30 minutes. If you did not request this, ignore this email."
    )
    return send_email(to_email, "Stress Monitor -- Password Reset", body)


def send_welcome_email(to_email, name):
    body = (
        f"Hi {name},\n\n"
        f"Your Stress Monitor account has been created successfully with this email address.\n\n"
        f"You can now log in and start using the dashboard."
    )
    return send_email(to_email, "Welcome to Stress Monitor", body)


def send_login_notification_email(to_email, name):
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    body = (
        f"Hi {name},\n\n"
        f"A new login to your Stress Monitor account was detected at {timestamp}.\n\n"
        f"If this wasn't you, consider resetting your password."
    )
    return send_email(to_email, "Stress Monitor -- New login", body)


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
