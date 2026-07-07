from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from extensions import db, bcrypt, limiter
from models import Admin
from utils import (
    is_password_valid,
    failed_password_rules,
    generate_totp_secret,
    generate_qr_code,
    verify_totp
)
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
    secret = generate_totp_secret()
    new_admin = Admin(
        admin_id=admin_id,
        password_hash=password_hash,
        totp_secret=secret,
        two_factor_enabled=True
        )
    db.session.add(new_admin)
    db.session.commit()
    qr_code = generate_qr_code(secret, admin_id)
    return jsonify({
    "message": "Admin account created successfully",
    "qr_code": qr_code,
    "secret": secret
}), 201


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

    return jsonify({
    "requires2FA": True,
    "adminId": admin.admin_id
}), 200
@admin_bp.route("/verify-2fa", methods=["POST"])
def verify_admin_2fa():

    data = request.get_json()

    admin_id = data.get("adminId")
    code = data.get("totpCode")

    admin = Admin.query.filter_by(admin_id=admin_id).first()

    if not admin:
        return jsonify({"message":"Admin not found"}),404

    if not verify_totp(admin.totp_secret, code):
        return jsonify({"message":"Invalid verification code"}),401

    token = create_access_token(
        identity=str(admin.id),
        additional_claims={
            "role":"admin",
            "adminId":admin.admin_id
        }
    )

    return jsonify({
        "token":token,
        "role":"admin"
    }),200