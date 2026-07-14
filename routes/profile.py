from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from extensions import db
from models import EmployeeProfile, HealthRecord, MedicalReport
from utils import validate_and_normalize_profile_data

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