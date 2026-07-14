from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from models import HealthRecord

risk_bp = Blueprint(
    "risk",
    __name__,
    url_prefix="/api/risk"
)


def calculate_risk(record):

    score = 0

    # BMI
    if record.bmi >= 30:
        score += 25
    elif record.bmi >= 25:
        score += 15

    # Sleep
    if record.sleep_hours < 5:
        score += 20
    elif record.sleep_hours < 7:
        score += 10

    # Exercise
    if record.exercise_minutes_per_week < 150:
        score += 10

    # Stress
    if record.stress_level == "High":
        score += 20
    elif record.stress_level == "Medium":
        score += 10

    # Blood Pressure
    if record.bp_systolic and record.bp_diastolic:

        if record.bp_systolic >= 140 or record.bp_diastolic >= 90:
            score += 20

        elif record.bp_systolic >= 130 or record.bp_diastolic >= 85:
            score += 10

    if score >= 60:
        level = "High"

    elif score >= 30:
        level = "Medium"

    else:
        level = "Low"

    return score, level


@risk_bp.route("", methods=["GET"])
@jwt_required()
def predict_risk():

    claims = get_jwt()

    if claims.get("role") != "user":
        return jsonify({
            "message": "Employee access only."
        }), 403

    user_id = int(get_jwt_identity())

    record = (
        HealthRecord.query
        .filter_by(user_id=user_id)
        .order_by(HealthRecord.record_date.desc())
        .first()
    )

    if not record:
        return jsonify({
            "message": "No health data found."
        }), 404

    score, level = calculate_risk(record)

    return jsonify({

        "riskScore": score,

        "riskLevel": level,

        "prediction": {

            "stressRisk":
                level,

            "obesityRisk":
                "High" if record.bmi >= 30 else "Low",

            "hypertensionRisk":
                "High"
                if (
                    record.bp_systolic >= 140
                    or
                    record.bp_diastolic >= 90
                )
                else "Low"

        }

    }), 200