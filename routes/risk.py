from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
import os
import pickle
import subprocess
import sys
import threading
import numpy as np

from models import HealthRecord

# Absolute paths anchored to the project root — these used to be bare
# relative filenames ("wellness_model.pkl"), which only worked if Flask
# happened to be launched with the project root as the current working
# directory. Anchoring them here makes model loading work no matter where
# the app is started from.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODEL_PATH = os.path.join(PROJECT_ROOT, "wellness_model.pkl")
SCALER_PATH = os.path.join(PROJECT_ROOT, "scaler.pkl")
TRAIN_SCRIPT_PATH = os.path.join(PROJECT_ROOT, "train_model.py")

_model = None
_scaler = None
_model_lock = threading.Lock()

STRESS_MAP = {"Low": 0, "Medium": 1, "High": 2}


class ModelUnavailableError(Exception):
    """Raised when the risk model can't be loaded or trained, so the route
    handler can turn it into a clean JSON error instead of a bare 500."""
    pass


def warmup_model():
    """Background eager pre-loader for risk model and scaler."""
    global _model, _scaler
    if _model is not None and _scaler is not None:
        return
    with _model_lock:
        if _model is not None and _scaler is not None:
            return
        if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
            try:
                with open(MODEL_PATH, "rb") as f:
                    _model = pickle.load(f)
                with open(SCALER_PATH, "rb") as f:
                    _scaler = pickle.load(f)
                print("Risk ML Model & Scaler eagerly loaded into RAM!")
            except Exception as exc:
                print(f"Warning: Could not pre-load model: {exc}")

# Trigger eager pre-loading in background thread upon import
threading.Thread(target=warmup_model, daemon=True).start()


def get_model_and_scaler():
    global _model, _scaler
    # Fast path: already loaded into RAM
    if _model is not None and _scaler is not None:
        return _model, _scaler

    with _model_lock:
        if _model is not None and _scaler is not None:
            return _model, _scaler

        if not os.path.exists(MODEL_PATH) or not os.path.exists(SCALER_PATH):
            print("Model files missing. Training model dynamically...")
            try:
                subprocess.run(
                    [sys.executable, TRAIN_SCRIPT_PATH],
                    check=True,
                    cwd=PROJECT_ROOT,
                )
            except (subprocess.CalledProcessError, FileNotFoundError) as exc:
                raise ModelUnavailableError(
                    f"Could not train the risk model automatically: {exc}"
                ) from exc

        try:
            with open(MODEL_PATH, "rb") as f:
                _model = pickle.load(f)
            with open(SCALER_PATH, "rb") as f:
                _scaler = pickle.load(f)
        except Exception as exc:
            raise ModelUnavailableError(f"Could not load the risk model: {exc}") from exc
    return _model, _scaler

def predict_risk_ml(record):
    try:
        model, scaler = get_model_and_scaler()
    except Exception:
        # Instant fallback to rule-based risk prediction if ML model is unavailable
        return calculate_risk(record)

    stress_encoded = STRESS_MAP.get(record.stress_level, 0)

    bmi = record.bmi if record.bmi is not None else 22.0
    sleep = record.sleep_hours if record.sleep_hours is not None else 8.0
    exercise = record.exercise_minutes_per_week if record.exercise_minutes_per_week is not None else 150
    bp_sys = record.bp_systolic if record.bp_systolic is not None else 120
    bp_dia = record.bp_diastolic if record.bp_diastolic is not None else 80

    # A plain numpy array is much cheaper to build per-request than a
    # pandas DataFrame (no index/dtype-inference machinery), and both
    # scaler.transform() and model.predict() accept it directly.
    features = np.array([[bmi, sleep, exercise, bp_sys, bp_dia, stress_encoded]])

    features_scaled = scaler.transform(features)

    pred_class = model.predict(features_scaled)[0]
    pred_probs = model.predict_proba(features_scaled)[0]

    classes = model.classes_
    prob_dict = dict(zip(classes, pred_probs))

    high_prob = prob_dict.get("High", 0.0)
    med_prob = prob_dict.get("Medium", 0.0)
    low_prob = prob_dict.get("Low", 0.0)

    score = int(high_prob * 100 + med_prob * 50 + low_prob * 10)
    score = min(max(score, 0), 100)

    return score, pred_class

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
        .order_by(HealthRecord.updated_at.desc(), HealthRecord.record_date.desc())
        .first()
    )

    if not record:
        return jsonify({
            "message": "No health data found."
        }), 404

    try:
        score, level = predict_risk_ml(record)
    except ModelUnavailableError as exc:
        return jsonify({"message": str(exc)}), 503

    response = jsonify({
        "riskScore": score,
        "riskLevel": level,
        "prediction": {
            "stressRisk":
                "High" if record.stress_level == "High" else ("Medium" if record.stress_level == "Medium" else "Low"),
            "obesityRisk":
                "High" if record.bmi >= 30 else ("Medium" if record.bmi >= 25 else "Low"),
            "hypertensionRisk":
                "High"
                if (
                    (record.bp_systolic is not None and record.bp_systolic >= 140)
                    or
                    (record.bp_diastolic is not None and record.bp_diastolic >= 90)
                )
                else (
                    "Medium"
                    if (
                        (record.bp_systolic is not None and record.bp_systolic >= 130)
                        or
                        (record.bp_diastolic is not None and record.bp_diastolic >= 85)
                    )
                    else "Low"
                )
        },
        "features": {
            "bmi": record.bmi,
            "sleepHours": record.sleep_hours,
            "exerciseMinutes": record.exercise_minutes_per_week,
            "bpSystolic": record.bp_systolic,
            "bpDiastolic": record.bp_diastolic,
            "stressLevel": record.stress_level
        }
    })

    response.headers["Cache-Control"] = "no-store"
    return response, 200