from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from extensions import db, bcrypt, limiter
from models import User, Admin, PasswordResetToken
from utils import is_password_valid, failed_password_rules, generate_otp, send_otp_email

password_reset_bp = Blueprint("password_reset", __name__, url_prefix="/api")

VALID_ROLES = {"user", "admin"}


def _find_account(identifier, role):
    if role == "user":
        return User.query.filter_by(email=identifier).first()
    if role == "admin":
        return Admin.query.filter_by(admin_id=identifier).first()
    return None


@password_reset_bp.route("/forgot-password", methods=["POST"])
@limiter.limit("5 per minute")
def forgot_password():
    data = request.get_json(silent=True) or {}
    identifier = (data.get("identifier") or "").strip()
    role = data.get("role")

    if not identifier or role not in VALID_ROLES:
        return jsonify({"message": "Identifier and a valid role are required"}), 400

    account = _find_account(identifier.lower() if role == "user" else identifier, role)

    # NOTE: the frontend (see forgot-password.html) is built to show the
    # user a "no account found" error here, matching the project brief in
    # API_ENDPOINTS.md. In a public production app you'd normally return
    # 200 unconditionally to avoid leaking which emails/IDs are registered
    # — if you want that later, just remove the 404 branch below.
    if not account:
        return jsonify({"message": "No account found with that identifier"}), 404

    otp_code = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=current_app.config["OTP_EXPIRY_MINUTES"])

    reset_token = PasswordResetToken(
        identifier=identifier.lower() if role == "user" else identifier,
        role=role,
        otp_code=otp_code,
        expires_at=expires_at,
    )
    db.session.add(reset_token)
    db.session.commit()

    # Only "user" accounts have a real email address to send to.
    # Admin IDs aren't necessarily emails, so this assumes admins have a
    # separate way to receive the code (e.g. a linked email on file) —
    # flag this to your team if admins need OTP delivery some other way.
    if role == "user":
        send_otp_email(identifier, otp_code, current_app.config)
    else:
        print(f"[DEV] OTP for admin '{identifier}': {otp_code}")

    return jsonify({"message": "Verification code sent"}), 200


@password_reset_bp.route("/reset-password", methods=["POST"])
@limiter.limit("10 per minute")
def reset_password():
    data = request.get_json(silent=True) or {}
    identifier = (data.get("identifier") or "").strip()
    role = data.get("role")
    otp = (data.get("otp") or "").strip()
    new_password = data.get("newPassword") or ""

    if not identifier or role not in VALID_ROLES or not otp or not new_password:
        return jsonify({"message": "Invalid or expired verification code"}), 400

    normalized_identifier = identifier.lower() if role == "user" else identifier

    token_row = (
        PasswordResetToken.query.filter_by(
            identifier=normalized_identifier, role=role, otp_code=otp, used=False
        )
        .order_by(PasswordResetToken.created_at.desc())
        .first()
    )

    if not token_row or token_row.expires_at < datetime.utcnow():
        return jsonify({"message": "Invalid or expired verification code"}), 400

    if not is_password_valid(new_password):
        missing = ", ".join(failed_password_rules(new_password))
        return jsonify({"message": f"Password must include: {missing}"}), 400

    account = _find_account(normalized_identifier, role)
    if not account:
        return jsonify({"message": "Invalid or expired verification code"}), 400

    account.password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
    token_row.used = True
    db.session.commit()

    return jsonify({"message": "Password reset successfully"}), 200
