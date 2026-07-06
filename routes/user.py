from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from extensions import db, bcrypt, limiter
from models import User
from utils import is_valid_email, is_password_valid, failed_password_rules
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
    new_user = User(email=email, password_hash=password_hash)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "Account created successfully"}), 201


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

    expires_delta = Config.JWT_REMEMBER_ME_EXPIRES if remember_me else Config.JWT_ACCESS_TOKEN_EXPIRES
    token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": "user", "email": user.email},
        expires_delta=expires_delta,
    )

    return jsonify({"message": "Login successful", "token": token, "role": "user"}), 200
