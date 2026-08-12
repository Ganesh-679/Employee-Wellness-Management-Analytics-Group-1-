import os
import uuid
from flask import Blueprint, request, jsonify, send_from_directory, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from extensions import db
from models import EmployeeProfile, HealthRecord, MedicalReport
from utils import validate_and_normalize_profile_data

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

profile_bp = Blueprint("profile", __name__, url_prefix="/api/profile")


def _require_user_role():
    claims = get_jwt()
    return claims.get("role") == "user"


@profile_bp.route("", methods=["GET"])
@jwt_required()
def get_profile():
    if not _require_user_role():
        return jsonify({"message": "Only employee accounts have a profile here"}), 403

    user_id = int(get_jwt_identity())
    profile = EmployeeProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        # No profile yet is a normal state (new employee) — return empty shape.
        return jsonify({"profile": None}), 200
    return jsonify({"profile": profile.to_dict()}), 200


@profile_bp.route("", methods=["PUT"])
@jwt_required()
def upsert_profile():
    if not _require_user_role():
        return jsonify({"message": "Only employee accounts have a profile here"}), 403

    user_id = int(get_jwt_identity())
    payload = request.get_json(silent=True) or {}

    normalized, errors = validate_and_normalize_profile_data(payload)
    if errors:
        return jsonify({"message": "Validation failed", "errors": errors}), 400

    profile = EmployeeProfile.query.filter_by(user_id=user_id).first()
    if profile:
        for field, value in normalized.items():
            setattr(profile, field, value)
    else:
        profile = EmployeeProfile(user_id=user_id, **normalized)
        db.session.add(profile)

    db.session.commit()
    return jsonify({"message": "Profile saved successfully", "profile": profile.to_dict()}), 200


def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@profile_bp.route("/picture", methods=["POST"])
@jwt_required()
def upload_profile_picture():
    if not _require_user_role():
        return jsonify({"message": "Only employee accounts can upload pictures"}), 403

    user_id = int(get_jwt_identity())

    if "file" not in request.files:
        return jsonify({"message": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "" or not _allowed_file(file.filename):
        return jsonify({"message": "Invalid file type. Use PNG, JPG, JPEG, GIF, or WebP."}), 400

    # Save to uploads/avatars/
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "avatars")
    os.makedirs(upload_dir, exist_ok=True)

    ext = file.filename.rsplit(".", 1)[1].lower()
    unique_name = f"{user_id}_{uuid.uuid4().hex[:8]}.{ext}"
    file.save(os.path.join(upload_dir, unique_name))

    # Update profile record
    profile = EmployeeProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = EmployeeProfile(user_id=user_id, profile_picture=unique_name)
        db.session.add(profile)
    else:
        # Delete old file if exists
        if profile.profile_picture:
            old_path = os.path.join(upload_dir, profile.profile_picture)
            if os.path.exists(old_path):
                os.remove(old_path)
        profile.profile_picture = unique_name

    db.session.commit()
    return jsonify({"message": "Profile picture updated", "profilePicture": unique_name}), 200


@profile_bp.route("/picture/<filename>", methods=["GET"])
def serve_profile_picture(filename):
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "avatars")
    return send_from_directory(upload_dir, filename)

@profile_bp.route("/complete", methods=["GET"])
@jwt_required()
def get_complete_employee_profile():

    if not _require_user_role():
        return jsonify({
            "message": "Only employee accounts can access this endpoint"
        }), 403

    user_id = int(get_jwt_identity())

    profile = EmployeeProfile.query.filter_by(
        user_id=user_id
    ).first()

    latest_health = (
        HealthRecord.query
        .filter_by(user_id=user_id)
        .order_by(HealthRecord.record_date.desc())
        .first()
    )

    reports = (
        MedicalReport.query
        .filter_by(user_id=user_id)
        .order_by(MedicalReport.uploaded_at.desc())
        .all()
    )

    return jsonify({

        "profile":
            profile.to_dict() if profile else None,

        "latestHealth":
            latest_health.to_dict() if latest_health else None,

        "medicalReports":
            [r.to_dict() for r in reports]

    }), 200