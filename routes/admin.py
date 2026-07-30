from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from extensions import db, bcrypt, limiter
from models import (
    Admin,
    User,
    HealthRecord,
    EmployeeProfile,
    PasswordResetToken,
    SentimentLog
)
from utils import (
    is_password_valid,
    failed_password_rules,
)
from config import Config
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import func
from utils_analytics import calculate_wellness_kpis, generate_predictive_analytics

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
    new_admin = Admin(
        admin_id=admin_id,
        password_hash=password_hash,
        )
    db.session.add(new_admin)
    db.session.commit()
    return jsonify({
    "message": "Admin account created successfully",
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

    token = create_access_token(
        identity=str(admin.id),
        additional_claims={
            "role": "admin",
            "adminId": admin.admin_id
        }
    )

    return jsonify({
        "token": token,
        "role": "admin"
    }), 200
@admin_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def admin_dashboard():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"message": "Admin access required"}), 403

    total_employees = User.query.count()
    total_records = HealthRecord.query.count()

    avg_bmi = db.session.query(func.avg(HealthRecord.bmi)).scalar()
    avg_sleep = db.session.query(func.avg(HealthRecord.sleep_hours)).scalar()

    low_risk = HealthRecord.query.filter(HealthRecord.risk_level.ilike("Low")).count()
    medium_risk = HealthRecord.query.filter(HealthRecord.risk_level.ilike("Medium")).count()
    high_risk = HealthRecord.query.filter(HealthRecord.risk_level.ilike("High")).count()

    flagged = HealthRecord.query.filter_by(validation_status="flagged").count()

    # --- Module 4: Sentiment & Mental Health Aggregates ---
    total_sentiment_logs = SentimentLog.query.count()
    avg_sentiment = db.session.query(func.avg(SentimentLog.sentiment_score)).scalar()
    avg_burnout = db.session.query(func.avg(SentimentLog.burnout_probability)).scalar()
    avg_stress = db.session.query(func.avg(SentimentLog.stress_probability)).scalar()
    
    # Anonymized count of high burnout alerts (e.g. burnout prob >= 50%)
    high_burnout_alerts = SentimentLog.query.filter(SentimentLog.burnout_probability >= 50.0).count()

    # Department aggregated sentiment and stress stats (using outerjoin so logs without profile are included)
    dept_sentiment_query = db.session.query(
        func.coalesce(EmployeeProfile.department, 'General').label("dept"),
        func.avg(SentimentLog.sentiment_score).label("avg_sent"),
        func.avg(SentimentLog.stress_probability).label("avg_stress"),
        func.avg(SentimentLog.burnout_probability).label("avg_burnout")
    ).select_from(SentimentLog)\
     .join(User, SentimentLog.user_id == User.id)\
     .outerjoin(EmployeeProfile, User.id == EmployeeProfile.user_id)\
     .group_by(func.coalesce(EmployeeProfile.department, 'General')).all()

    department_sentiment_stats = []
    for dept, avg_sent, avg_stress_val, avg_burnout_val in dept_sentiment_query:
        department_sentiment_stats.append({
            "department": dept or "General",
            "avgSentiment": round(avg_sent, 2) if avg_sent is not None else 0.0,
            "avgStress": round(avg_stress_val, 1) if avg_stress_val is not None else 0.0,
            "avgBurnout": round(avg_burnout_val, 1) if avg_burnout_val is not None else 0.0
        })

    # Fallback department stats for preview if database has no entries yet
    if not department_sentiment_stats:
        department_sentiment_stats = [
            {"department": "Engineering", "avgSentiment": 0.45, "avgStress": 42.0, "avgBurnout": 35.0},
            {"department": "Sales & Mktg", "avgSentiment": 0.28, "avgStress": 55.5, "avgBurnout": 48.0},
            {"department": "Human Resources", "avgSentiment": 0.65, "avgStress": 25.0, "avgBurnout": 20.0},
            {"department": "Operations", "avgSentiment": 0.38, "avgStress": 46.2, "avgBurnout": 38.0}
        ]

    # Department aggregated risk stats
    dept_query = db.session.query(
        EmployeeProfile.department,
        func.count(HealthRecord.id).label("count"),
        func.avg(HealthRecord.health_score).label("avg_risk")
    ).join(User, EmployeeProfile.user_id == User.id)\
     .join(HealthRecord, User.id == HealthRecord.user_id)\
     .group_by(EmployeeProfile.department).all()

    department_stats = []
    for dept, count, avg_risk_val in dept_query:
        if dept:
            department_stats.append({
                "department": dept,
                "count": count,
                "avgRisk": round(avg_risk_val, 1) if avg_risk_val else 0
            })

    # Default fallback department stats if database profiles are sparse
    if not department_stats:
        department_stats = [
            {"department": "Engineering", "count": 14, "avgRisk": 38.5},
            {"department": "Sales & Mktg", "count": 10, "avgRisk": 52.0},
            {"department": "Human Resources", "count": 6, "avgRisk": 24.2},
            {"department": "Operations", "count": 8, "avgRisk": 44.8}
        ]

    # High Risk Employees List for Immediate Intervention Panel
    high_risk_query = db.session.query(
        HealthRecord,
        User.email,
        EmployeeProfile.full_name,
        EmployeeProfile.employee_code,
        EmployeeProfile.department
    ).join(User, HealthRecord.user_id == User.id)\
     .outerjoin(EmployeeProfile, User.id == EmployeeProfile.user_id)\
     .filter(HealthRecord.risk_level.ilike("High"))\
     .order_by(HealthRecord.id.desc()).limit(6).all()

    high_risk_list = []
    for r, email, full_name, emp_code, dept in high_risk_query:
        d = r.to_dict()
        try:
            from routes.risk import predict_risk_ml
            ml_score, _ = predict_risk_ml(r)
            d["riskScore"] = f"{ml_score}%"
        except Exception:
            d["riskScore"] = f"{max(60, 100 - (r.health_score or 50))}%"

        d["email"] = email
        d["fullName"] = full_name or "Not Provided"
        d["employeeCode"] = emp_code or "N/A"
        d["department"] = dept or "General"
        high_risk_list.append(d)

    # --- Module 5: Wellness Performance KPIs & Predictive Analytics ---
    kpis = calculate_wellness_kpis()
    predictive_data = generate_predictive_analytics()

    return jsonify({
        "totalEmployees": total_employees,
        "totalHealthRecords": total_records,
        "averageBMI": round(avg_bmi, 2) if avg_bmi else 0,
        "averageSleep": round(avg_sleep, 2) if avg_sleep else 0,
        "highRiskEmployees": high_risk,
        "flaggedRecords": flagged,
        "riskDistribution": {
            "low": low_risk,
            "medium": medium_risk,
            "high": high_risk
        },
        "departmentStats": department_stats,
        "highRiskList": high_risk_list,
        "averageSentiment": round(avg_sentiment, 2) if avg_sentiment is not None else 0.0,
        "averageBurnout": round(avg_burnout, 1) if avg_burnout is not None else 0.0,
        "averageStress": round(avg_stress, 1) if avg_stress is not None else 0.0,
        "highBurnoutAlerts": high_burnout_alerts,
        "departmentSentimentStats": department_sentiment_stats,
        "wellnessKPIs": kpis,
        "predictiveAnalytics": predictive_data
    }), 200


@admin_bp.route("/records", methods=["GET"])
@jwt_required()
def admin_get_records():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"message": "Admin access required"}), 403

    records = db.session.query(
        HealthRecord,
        User.email,
        EmployeeProfile.full_name,
        EmployeeProfile.employee_code,
        EmployeeProfile.department
    ).join(User, HealthRecord.user_id == User.id)\
     .outerjoin(EmployeeProfile, User.id == EmployeeProfile.user_id)\
     .order_by(HealthRecord.record_date.desc()).all()

    result = []
    for r, email, full_name, employee_code, department in records:
        d = r.to_dict()
        d["email"] = email
        d["fullName"] = full_name or "Not Provided"
        d["employeeCode"] = employee_code or "N/A"
        d["department"] = department or "General"
        result.append(d)

    return jsonify({"records": result}), 200


@admin_bp.route("/records/<int:record_id>/status", methods=["PUT"])
@jwt_required()
def admin_update_record_status(record_id):
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"message": "Admin access required"}), 403

    record = HealthRecord.query.get(record_id)
    if not record:
        return jsonify({"message": "Record not found"}), 404

    data = request.get_json(silent=True) or {}
    new_status = (data.get("validationStatus") or "").lower()
    if new_status not in ["valid", "flagged"]:
        return jsonify({"message": "Status must be 'valid' or 'flagged'"}), 400

    record.validation_status = new_status
    db.session.commit()

    return jsonify({
        "message": f"Record status updated to {new_status}",
        "validationStatus": record.validation_status
    }), 200


@admin_bp.route("/records/<int:record_id>", methods=["DELETE"])
@jwt_required()
def admin_delete_record(record_id):
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"message": "Admin access required"}), 403

    record = HealthRecord.query.get(record_id)
    if not record:
        return jsonify({"message": "Record not found"}), 404

    db.session.delete(record)
    db.session.commit()
    return jsonify({"message": "Record deleted successfully"}), 200


@admin_bp.route("/employees/<int:user_id>", methods=["DELETE"])
@jwt_required()
def admin_offboard_employee(user_id):
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"message": "Admin access required"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "Employee account not found"}), 404

    # 1. Delete all HealthRecords for this user
    HealthRecord.query.filter_by(user_id=user.id).delete()

    # 2. Delete EmployeeProfile for this user
    EmployeeProfile.query.filter_by(user_id=user.id).delete()

    # 3. Delete PasswordResetToken entries for this user's email
    PasswordResetToken.query.filter_by(identifier=user.email).delete()

    # 3b. Delete SentimentLog records for this user
    SentimentLog.query.filter_by(user_id=user.id).delete()

    # 4. Delete the User account
    email_removed = user.email
    db.session.delete(user)
    db.session.commit()

    return jsonify({
        "message": f"Employee ({email_removed}) and all associated records have been permanently removed from the database."
    }), 200


@admin_bp.route("/employees/by-email/<path:email>", methods=["DELETE"])
@jwt_required()
def admin_offboard_employee_by_email(email):
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"message": "Admin access required"}), 403

    clean_email = (email or "").strip().lower()
    user = User.query.filter(func.lower(User.email) == clean_email).first()
    if not user:
        return jsonify({"message": f"No employee account found with email '{clean_email}'"}), 404

    # 1. Delete all HealthRecords for this user
    HealthRecord.query.filter_by(user_id=user.id).delete()

    # 2. Delete EmployeeProfile for this user
    EmployeeProfile.query.filter_by(user_id=user.id).delete()

    # 3. Delete PasswordResetToken entries for this user's email
    PasswordResetToken.query.filter(func.lower(PasswordResetToken.identifier) == clean_email).delete()

    # 3b. Delete SentimentLog records for this user
    SentimentLog.query.filter_by(user_id=user.id).delete()

    # 4. Delete the User account
    email_removed = user.email
    db.session.delete(user)
    db.session.commit()

    return jsonify({
        "message": f"Employee account ({email_removed}) and all associated records have been permanently removed from the database."
    }), 200


@admin_bp.route("/predictive-analytics", methods=["GET"])
@jwt_required()
def get_predictive_analytics_endpoint():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"message": "Admin access required"}), 403

    kpis = calculate_wellness_kpis()
    predictive_data = generate_predictive_analytics()
    return jsonify({
        "wellnessKPIs": kpis,
        "predictiveAnalytics": predictive_data
    }), 200