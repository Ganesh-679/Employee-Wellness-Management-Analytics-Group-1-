import json
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from extensions import db
from models import HealthRecord
from utils import (
    validate_and_normalize_health_data,
    calculate_health_score,
    calculate_risk_level
)

health_bp = Blueprint("health", __name__, url_prefix="/api/health-records")


def _require_user_role():
    """Only employees (role='user') manage their own health data, not admins."""
    claims = get_jwt()
    return claims.get("role") == "user"


@health_bp.route("/", methods=["POST"])
@jwt_required()
def create_health_record():
    if not _require_user_role():
        return jsonify({"message": "Only employee accounts can submit health data"}), 403

    user_id = int(get_jwt_identity())
    payload = request.get_json(silent=True) or {}

    normalized, errors, warnings = validate_and_normalize_health_data(payload)
    if errors:
        return jsonify({
        "message": "Validation failed",
        "errors": errors
    }), 400
    record_date = normalized.get("record_date")
    existing_record = HealthRecord.query.filter_by(
    user_id=user_id,
    record_date=record_date
).first()
    if existing_record:
        return jsonify({
        "message": "Health record for this date already exists."
    }), 409

    health_score = calculate_health_score(normalized)
    risk_level = calculate_risk_level(
    normalized,
    warnings
    )
    record = HealthRecord(
    user_id=user_id,

    validation_status="flagged" if warnings else "valid",

    validation_flags=json.dumps(warnings) if warnings else None,

    health_score=health_score,

    risk_level=risk_level,

    **normalized
    )
    db.session.add(record)
    db.session.commit()

    return jsonify({
        "message": "Health record saved successfully",
        "record": record.to_dict(),
    }), 201


@health_bp.route("/", methods=["GET"])
@jwt_required()
def list_health_records():
    if not _require_user_role():
        return jsonify({"message": "Only employee accounts can view their health data"}), 403

    user_id = int(get_jwt_identity())
    records = (
        HealthRecord.query.filter_by(user_id=user_id)
        .order_by(HealthRecord.record_date.desc())
        .all()
    )
    return jsonify({"records": [r.to_dict() for r in records]}), 200


@health_bp.route("/<int:record_id>", methods=["GET"])
@jwt_required()
def get_health_record(record_id):
    if not _require_user_role():
        return jsonify({"message": "Only employee accounts can view their health data"}), 403

    user_id = int(get_jwt_identity())
    record = HealthRecord.query.filter_by(id=record_id, user_id=user_id).first()
    if not record:
        return jsonify({"message": "Record not found"}), 404
    return jsonify({"record": record.to_dict()}), 200


@health_bp.route("/<int:record_id>", methods=["PUT"])
@jwt_required()
def update_health_record(record_id):
    if not _require_user_role():
        return jsonify({"message": "Only employee accounts can edit their health data"}), 403

    user_id = int(get_jwt_identity())
    record = HealthRecord.query.filter_by(id=record_id, user_id=user_id).first()
    if not record:
        return jsonify({"message": "Record not found"}), 404

    payload = request.get_json(silent=True) or {}
    normalized, errors, warnings = validate_and_normalize_health_data(payload)
    if errors:
        return jsonify({"message": "Validation failed", "errors": errors}), 400

    for field, value in normalized.items():
        setattr(record, field, value)
    record.validation_status = "flagged" if warnings else "valid"
    record.validation_flags = json.dumps(warnings) if warnings else None
    record.health_score = calculate_health_score(normalized)
    record.risk_level = calculate_risk_level(
    normalized,
    warnings
    )

    db.session.commit()
    return jsonify({"message": "Health record updated successfully", "record": record.to_dict()}), 200


@health_bp.route("/<int:record_id>", methods=["DELETE"])
@jwt_required()
def delete_health_record(record_id):
    if not _require_user_role():
        return jsonify({"message": "Only employee accounts can delete their health data"}), 403

    user_id = int(get_jwt_identity())
    record = HealthRecord.query.filter_by(id=record_id, user_id=user_id).first()
    if not record:
        return jsonify({"message": "Record not found"}), 404

    db.session.delete(record)
    db.session.commit()
    return jsonify({"message": "Health record deleted successfully"}), 200
