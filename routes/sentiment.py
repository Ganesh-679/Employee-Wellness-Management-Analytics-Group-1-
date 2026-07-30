import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from extensions import db
from models import SentimentLog
from utils import analyze_mental_health_nlp

sentiment_bp = Blueprint("sentiment", __name__, url_prefix="/api/sentiment")


@sentiment_bp.route("/analyze", methods=["POST"])
@jwt_required()
def analyze_and_log_sentiment():
    claims = get_jwt()
    if claims.get("role") != "user":
        return jsonify({"message": "Only employee accounts can submit mental health check-ins"}), 403

    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    text_content = (data.get("textContent") or "").strip()

    if not text_content:
        return jsonify({"message": "Journal or reflection text is required"}), 400

    # Ensure a minimum of 5 words for NLP extraction
    words = text_content.split()
    if len(words) < 5:
        return jsonify({"message": "Please write at least 5 words so the AI can run a reliable sentiment analysis."}), 400

    # Run NLP Analysis Engine
    analysis = analyze_mental_health_nlp(text_content)

    new_log = SentimentLog(
        user_id=user_id,
        text_content=text_content,
        sentiment_score=analysis["sentiment_score"],
        sentiment_label=analysis["sentiment_label"],
        stress_probability=analysis["stress_probability"],
        anxiety_probability=analysis["anxiety_probability"],
        burnout_probability=analysis["burnout_probability"],
        detected_emotions=json.dumps(analysis["detected_emotions"])
    )

    db.session.add(new_log)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Sentiment analysis logged successfully",
        "log": new_log.to_dict()
    }), 201


@sentiment_bp.route("/history", methods=["GET"])
@jwt_required()
def get_sentiment_history():
    claims = get_jwt()
    if claims.get("role") != "user":
        return jsonify({"message": "Only employee accounts can retrieve sentiment history"}), 403

    user_id = int(get_jwt_identity())
    logs = SentimentLog.query.filter_by(user_id=user_id).order_by(SentimentLog.logged_at.desc()).all()

    return jsonify({
        "logs": [log.to_dict() for log in logs]
    }), 200


@sentiment_bp.route("/dashboard-summary", methods=["GET"])
@jwt_required()
def get_sentiment_dashboard_summary():
    claims = get_jwt()
    if claims.get("role") != "user":
        return jsonify({"message": "Only employee accounts can retrieve dashboard summaries"}), 403

    user_id = int(get_jwt_identity())
    logs = SentimentLog.query.filter_by(user_id=user_id).order_by(SentimentLog.logged_at.desc()).all()

    if not logs:
        return jsonify({
            "status": "no_data",
            "message": "No mental health reflections submitted yet."
        }), 200

    latest_log = logs[0].to_dict()
    
    # Calculate averages
    avg_sentiment = sum(log.sentiment_score for log in logs) / len(logs)
    avg_stress = sum(log.stress_probability for log in logs) / len(logs)
    avg_anxiety = sum(log.anxiety_probability for log in logs) / len(logs)
    avg_burnout = sum(log.burnout_probability for log in logs) / len(logs)

    # Determine average sentiment label
    if avg_sentiment >= 0.15:
        avg_label = "Positive"
    elif avg_sentiment <= -0.15:
        avg_label = "Negative"
    else:
        avg_label = "Neutral"

    return jsonify({
        "status": "success",
        "totalLogs": len(logs),
        "latest": latest_log,
        "averages": {
            "sentimentScore": round(avg_sentiment, 2),
            "sentimentLabel": avg_label,
            "stressProbability": round(avg_stress, 1),
            "anxietyProbability": round(avg_anxiety, 1),
            "burnoutProbability": round(avg_burnout, 1)
        }
    }), 200
