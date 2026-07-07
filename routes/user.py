from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from extensions import db, bcrypt, limiter
from models import User
from utils import (
    is_valid_email,
    is_password_valid,
    failed_password_rules,
    generate_totp_secret,
    generate_qr_code,
    verify_totp,
)
from config import Config


user_bp = Blueprint("user", __name__, url_prefix="/api/user")


@user_bp.route("/register", methods=["POST"])
def register_user():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    if not is_valid_email(email):
        return jsonify({"message": "Please enter a valid email address"}), 400

    # Re-validate password rules server-side even though the frontend
    # already checks them (never trust client-side validation alone).
    if not is_password_valid(password):
        missing = ", ".join(failed_password_rules(password))
        return jsonify({"message": f"Password must include: {missing}"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"message": "An account with this email already exists"}), 409
    
    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    # Generate Google Authenticator secret
    secret = generate_totp_secret()
    new_user = User(
        email=email,
        password_hash=password_hash,
        totp_secret=secret,
        two_factor_enabled=True,
        )
    db.session.add(new_user)
    db.session.commit()
    # Generate QR Code
    qr_code = generate_qr_code(secret, email)
    return jsonify({
        "message": "Account created successfully",
        "qr_code": qr_code,
        "secret": secret
        }), 201
@user_bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute")
def login_user():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    remember_me = bool(data.get("rememberMe"))

    if not email or not password:
        return jsonify({"message": "Invalid email or password"}), 401

    user = User.query.filter_by(email=email).first()

    # Same generic message whether the account doesn't exist or the
    # password is wrong, so attackers can't tell which emails are registered.
    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({"message": "Invalid email or password"}), 401
    return jsonify(
    {
        "requires2FA": True,
        "email": user.email
    }
), 200
@user_bp.route("/verify-2fa", methods=["POST"])
def verify_2fa():

    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    totp_code = (data.get("totpCode") or "").strip()

    if not email or not totp_code:
        return jsonify({
            "message": "Email and verification code are required."
        }), 400

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({
            "message": "User not found."
        }), 404

    if not verify_totp(user.totp_secret, totp_code):
        return jsonify({
            "message": "Invalid Google Authenticator code."
        }), 401

    token = create_access_token(
        identity=str(user.id),
        additional_claims={
            "role": "user",
            "email": user.email
        }
    )

    return jsonify({
        "message": "Verification successful",
        "token": token,
        "role": "user"
    }), 200