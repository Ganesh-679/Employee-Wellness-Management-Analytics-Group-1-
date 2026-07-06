from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from extensions import db, bcrypt, limiter
from models import Admin
from utils import is_password_valid, failed_password_rules
from config import Config

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.route("/register", methods=["POST"])
def register_admin():
    data = request.get_json(silent=True) or {}
    admin_id = (data.get("adminId") or "").strip()
    password = data.get("password") or ""

    if not admin_id or not password:
        return jsonify({"message": "Admin ID and password are required"}), 400

    if len(admin_id) < 3:
        return jsonify({"message": "Admin ID must be at least 3 characters"}), 400

    if not is_password_valid(password):
        missing = ", ".join(failed_password_rules(password))
        return jsonify({"message": f"Password must include: {missing}"}), 400

    if Admin.query.filter_by(admin_id=admin_id).first():
        return jsonify({"message": "This admin ID is already in use"}), 409

    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    new_admin = Admin(admin_id=admin_id, password_hash=password_hash)
    db.session.add(new_admin)
    db.session.commit()

    return jsonify({"message": "Admin account created successfully"}), 201


@admin_bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute")
def login_admin():
    data = request.get_json(silent=True) or {}
    admin_id = (data.get("adminId") or "").strip()
    password = data.get("password") or ""
    remember_me = bool(data.get("rememberMe"))

    if not admin_id or not password:
        return jsonify({"message": "Invalid admin ID or password"}), 401

    admin = Admin.query.filter_by(admin_id=admin_id).first()

    if not admin or not bcrypt.check_password_hash(admin.password_hash, password):
        return jsonify({"message": "Invalid admin ID or password"}), 401

    expires_delta = Config.JWT_REMEMBER_ME_EXPIRES if remember_me else Config.JWT_ACCESS_TOKEN_EXPIRES
    token = create_access_token(
        identity=str(admin.id),
        additional_claims={"role": "admin", "adminId": admin.admin_id},
        expires_delta=expires_delta,
    )

    return jsonify({"message": "Login successful", "token": token, "role": "admin"}), 200
