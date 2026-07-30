import os
import datetime
import random
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import (
    User,
    EmployeeProfile,
    HealthRecord,
    ChatMessage,
    WellnessReminder,
    HealthCheckupSchedule
)

chatbot_bp = Blueprint("chatbot", __name__, url_prefix="/api/chatbot")


def get_current_user(user_id):
    """Fetch user record or return None."""
    return User.query.get(user_id)


def query_gemini_api(prompt, emp_name, health_score, sleep_hrs, stress_lvl):
    """Query Google Gemini API for deep conversational wellness responses.
    Tries gemini-2.0-flash first, then gemini-2.0-flash-lite as fallback."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "your_gemini_api_key_here":
        return None

    import urllib.request
    import urllib.error
    import json

    system_instruction = (
        f"You are a friendly 24/7 AI Wellness & Health Assistant coaching {emp_name}. "
        f"Employee context: Health Score {health_score}/100, Sleep Average {sleep_hrs} hrs, Stress Level {stress_lvl}. "
        f"STRICT RULE: You MUST ONLY answer questions related to health, wellness, fitness, nutrition, sleep, stress, "
        f"mental health, exercise, medical topics, employee wellbeing, or this wellness management project. "
        f"If the user asks anything unrelated (celebrities, politics, general knowledge, entertainment, etc.), "
        f"politely decline and say: 'I'm your dedicated Wellness Assistant and can only help with health & wellness topics.' "
        f"Then suggest what you CAN help with. "
        f"Provide supportive, concise guidance with bullet points and friendly emojis."
    )

    payload = {
        "contents": [{
            "parts": [{"text": f"{system_instruction}\n\nEmployee Query: {prompt}"}]
        }]
    }
    payload_bytes = json.dumps(payload).encode("utf-8")

    # Try multiple models in order of preference
    models_to_try = ["gemini-2.0-flash", "gemini-2.0-flash-lite"]

    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        try:
            req = urllib.request.Request(
                url,
                data=payload_bytes,
                headers={"Content-Type": "application/json", "x-goog-api-key": api_key}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                candidates = res_data.get("candidates", [])
                if candidates:
                    text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    if text:
                        return text.strip()
        except urllib.error.HTTPError as http_err:
            print(f"Gemini API ({model_name}) HTTP {http_err.code}: {http_err.reason}")
            continue  # Try next model
        except Exception as exc:
            print(f"Gemini API ({model_name}) warning: {exc}")
            continue  # Try next model

    return None


def process_nlp_intent(user_id, prompt):
    """Context-aware Smart NLP Chatbot Engine for Employee Wellness."""
    p_lower = prompt.lower().strip()

    # Retrieve user profile & latest health record for personalized context
    profile = EmployeeProfile.query.filter_by(user_id=user_id).first()
    latest_record = HealthRecord.query.filter_by(user_id=user_id).order_by(HealthRecord.record_date.desc()).first()

    emp_name = profile.full_name if profile and profile.full_name else "Employee"
    health_score = latest_record.health_score if latest_record else 85
    sleep_hrs = latest_record.sleep_hours if latest_record else 7.5
    stress_lvl = latest_record.stress_level if latest_record else "Low"

    # 0. Model Identity Intent
    if any(k in p_lower for k in ["which model", "what model", "which ai", "model are you", "what ai"]):
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        has_gemini = bool(api_key and api_key != "your_gemini_api_key_here")
        
        active_model = "**Google Gemini 2.0 Flash (Generative AI)** 🤖" if has_gemini else "**Smart Local Hybrid NLP Engine** 🌿"
        reply = (
            f"🧠 **AI Model Information:**\n\n"
            f"I am powered by {active_model}.\n\n"
            f"• **Active Mode**: {'Online Cloud Generative AI (gemini-2.0-flash)' if has_gemini else 'Offline Local Medical NLP Engine'}\n"
            f"• **API Status**: {'Gemini 2.0 Key Configured' if has_gemini else 'Using Local Fallback Engine'}\n"
            f"• **Capabilities**: Action scheduling, wellness reminders, goal tracking, and personalized health coaching.\n"
            f"• **Context Awareness**: Connected to your profile ({emp_name}) & Health Metrics (Health Score: {health_score}/100)."
        )
        return "model_info", reply, {}



    # 1. Schedule Health Checkup Intent
    if any(k in p_lower for k in ["schedule checkup", "book checkup", "doctor appointment", "health checkup", "schedule appointment"]):
        target_date = (datetime.date.today() + datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        
        checkup = HealthCheckupSchedule(
            user_id=user_id,
            checkup_type="Comprehensive Preventive Health Screening",
            scheduled_date=target_date,
            status="Scheduled",
            notes="Booked via AI Wellness Assistant"
        )
        db.session.add(checkup)
        db.session.commit()

        reply = (
            f"📅 **Health Checkup Scheduled Successfully!**\n\n"
            f"Hello {emp_name}, I have scheduled your **Comprehensive Preventive Health Screening** for **{target_date}**.\n"
            f"You will receive a notification reminder 24 hours prior to your appointment."
        )
        return "schedule_checkup", reply, {"checkup": checkup.to_dict()}

    # 2. Set Reminder Intent
    if any(k in p_lower for k in ["set reminder", "remind me", "water reminder", "stretch reminder", "hydration reminder"]):
        reminder_type = "hydration"
        time_str = "Every 2 hours"
        title = "💧 Drink Water & Stay Hydrated"

        if "stretch" in p_lower or "break" in p_lower:
            reminder_type = "stretch"
            time_str = "Every 60 mins"
            title = "🧘 Take a 5-Min Ergonomic Stretch Break"
        elif "sleep" in p_lower or "bed" in p_lower:
            reminder_type = "sleep"
            time_str = "Daily at 10:30 PM"
            title = "💤 Prepare for Restorative Sleep"

        reminder = WellnessReminder(
            user_id=user_id,
            title=title,
            reminder_type=reminder_type,
            time_str=time_str,
            is_active=True
        )
        db.session.add(reminder)
        db.session.commit()

        reply = (
            f"⏰ **Wellness Reminder Created!**\n\n"
            f"I have set a new **{title}** reminder ({time_str}).\n"
            f"Staying consistent with small healthy habits boosts your daily energy index!"
        )
        return "set_reminder", reply, {"reminder": reminder.to_dict()}

    # 3. Track Goals & Milestones Intent
    if any(k in p_lower for k in ["track goal", "my goals", "progress", "milestone", "score", "how am i doing"]):
        reply = (
            f"🎯 **Personal Health Goal Progress for {emp_name}:**\n\n"
            f"• **Overall Health Score:** {health_score} / 100 ({'Optimal' if health_score >= 80 else 'Moderate'})\n"
            f"• **Sleep Average:** {sleep_hrs} hrs / night (Target: 7.5 hrs)\n"
            f"• **Stress Balance:** {stress_lvl} Mental Stress\n"
            f"• **Check-in Streak:** Active Daily Tracking\n\n"
            f"💡 *Tip: Keep logging your daily metrics under 'My Wellness Check-in' to unlock +200 bonus reward points!*"
        )
        return "track_goals", reply, {}

    # 4. Motivation & Encouragement Intent
    if any(k in p_lower for k in ["motivation", "motivate me", "feeling tired", "cheer me up", "quote"]):
        motivational_quotes = [
            "🌟 'Your health is an investment, not an expense. Every healthy check-in is a step toward vibrant longevity!'",
            "⚡ 'Small daily wellness habits compound into extraordinary energy and career performance over time.'",
            "🌿 'Take a deep breath. Rest is not a reward for work; rest is a prerequisite for high performance.'",
            "🔥 'Consistency beats intensity! You are doing amazing work prioritizing your physical and mental balance.'"
        ]
        quote = random.choice(motivational_quotes)
        reply = (
            f"💪 **Personal Wellness Booster for {emp_name}:**\n\n"
            f"{quote}\n\n"
            f"Your current Health Score is **{health_score}/100**. Keep pushing forward!"
        )
        return "motivation", reply, {}

    # 5. Sleep & Fatigue Advice Intent
    if any(k in p_lower for k in ["sleep", "insomnia", "tired", "rest", "night"]):
        reply = (
            f"💤 **Evidence-Based Sleep Optimization Advice:**\n\n"
            f"Based on your profile, you average **{sleep_hrs} hours** of sleep per night.\n\n"
            f"1. **Circadian Hygiene**: Maintain a consistent bedtime within a 30-minute window.\n"
            f"2. **Blue Light Cutoff**: Discontinue screen time 45 minutes before sleep.\n"
            f"3. **Optimal Temperature**: Keep your bedroom temperature between 18°C – 20°C (65°F – 68°F).\n"
            f"4. **Caffeine Window**: Avoid caffeine consumption after 2:00 PM."
        )
        return "sleep_advice", reply, {}

    # 5. Emotional Support & Mood Empathy Intent
    if any(k in p_lower for k in ["sad", "depressed", "unhappy", "lonely", "feeling low", "feeling down", "upset", "crying", "bad day", "blue", "hopeless", "feeling bad"]):
        reply = (
            f"🫂 **I'm here for you, {emp_name}.**\n\n"
            f"I'm sorry to hear that you are feeling sad today. It is completely valid and okay to have low days.\n\n"
            f"🌿 **Gentle Self-Care Steps for Today:**\n"
            f"1. **Be Gentle with Yourself**: Prioritize rest and don't pressure yourself today.\n"
            f"2. **Mindful Pause**: Take 5 slow, deep breaths. Inhale peace, exhale tension.\n"
            f"3. **Express Feelings**: You can log a quick entry under the *Mental Health & Sentiment* tab to track your emotional wellbeing.\n"
            f"4. **Support Systems**: Reach out to a trusted colleague, friend, or check our confidential Employee Assistance Program for counseling."
        )
        return "emotional_support", reply, {}

    # 6. Stress & Anxiety Management Intent
    if any(k in p_lower for k in ["stress", "anxiety", "overwhelmed", "workload", "mental", "burnout", "panic", "worried", "exhausted"]):
        reply = (
            f"🧠 **Mental Stress & Resilience Coaching:**\n\n"
            f"Your latest logged stress level is **{stress_lvl}**.\n\n"
            f"• **Box Breathing Technique**: Inhale for 4s → Hold for 4s → Exhale for 4s → Hold for 4s. Repeat 4 times.\n"
            f"• **Micro-Breaks**: Take a 5-minute walk outside after every 90 minutes of focused work.\n"
            f"• **Employee Assistance Program**: You have access to 1-on-1 confidential counseling. Check the Mental Health tab for details."
        )
        return "stress_advice", reply, {}

    # 7. Exercise & Physical Activity Intent
    if any(k in p_lower for k in ["exercise", "workout", "gym", "fitness", "steps", "active"]):
        reply = (
            f"🏃 **Physical Activity & Ergonomics Guidance:**\n\n"
            f"Target benchmark: **150+ minutes** of moderate aerobic exercise per week.\n\n"
            f"• **Desk Ergonomics**: Keep monitor at eye level, elbows at 90°, and feet flat on the floor.\n"
            f"• **Daily Step Target**: Aim for 8,000 – 10,000 steps daily.\n"
            f"• **Strength Training**: Incorporate 2 session of resistance/bodyweight exercises weekly."
        )
        return "exercise_advice", reply, {}

    # 8. Diet & Hydration Intent
    if any(k in p_lower for k in ["diet", "food", "nutrition", "water", "hydration"]):
        reply = (
            f"🥗 **Nutritional & Hydration Protocol:**\n\n"
            f"• **Daily Hydration**: Aim for **2.5 to 3.0 Liters** of pure water daily.\n"
            f"• **Balanced Meals**: Fill 50% of your plate with complex vegetables, 25% lean protein, and 25% complex carbs.\n"
            f"• **Energy Crash Prevention**: Replace sugary afternoon snacks with almonds, Greek yogurt, or fresh fruit."
        )
        return "nutrition_advice", reply, {}

    # Try Google Gemini API query for open-ended queries
    gemini_reply = query_gemini_api(prompt, emp_name, health_score, sleep_hrs, stress_lvl)
    if gemini_reply:
        return "gemini_llm_query", gemini_reply, {}

    # Default Fallback: Wellness-only scope enforcement
    off_topic_reply = (
        f"🚫 Sorry {emp_name}, I'm your dedicated **AI Wellness & Health Assistant** and I can only help with health and wellness-related topics.\n\n"
        f"Here's what I **can** help you with:\n"
        f"• 📅 **Schedule Health Checkups** — _\"schedule a checkup\"_\n"
        f"• ⏰ **Set Wellness Reminders** — _\"remind me to drink water\"_\n"
        f"• 🎯 **Track Health Goals** — _\"set a fitness goal\"_\n"
        f"• 💡 **Sleep, Stress & Nutrition Tips** — _\"how to improve my sleep?\"_\n"
        f"• 🧠 **Mental Health Support** — _\"I feel stressed\"_\n"
        f"• 🔥 **Daily Motivation** — _\"motivate me\"_\n\n"
        f"Try asking me one of these! 😊"
    )
    return "off_topic", off_topic_reply, {}


@chatbot_bp.route("/message", methods=["POST"])
@jwt_required()
def send_message():
    """POST /api/chatbot/message: Conversational endpoint."""
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json(silent=True) or {}
        user_prompt = data.get("message", "").strip()

        if not user_prompt:
            return jsonify({"message": "Please provide a valid text prompt."}), 400

        # Save user message to persistent DB history
        user_msg = ChatMessage(user_id=user_id, sender="user", text=user_prompt)
        db.session.add(user_msg)

        # Process prompt via Smart NLP Conversational Engine
        intent, bot_reply, action_data = process_nlp_intent(user_id, user_prompt)

        # Save bot reply to persistent DB history
        bot_msg = ChatMessage(user_id=user_id, sender="bot", text=bot_reply, intent=intent)
        db.session.add(bot_msg)
        db.session.commit()

        return jsonify({
            "intent": intent,
            "reply": bot_reply,
            "actionData": action_data,
            "userMessage": user_msg.to_dict(),
            "botMessage": bot_msg.to_dict()
        }), 200
    except Exception as exc:
        db.session.rollback()
        print(f"Chatbot error: {exc}")
        return jsonify({
            "intent": "error_fallback",
            "reply": "I am here to help! Ask me about your health score, sleep, exercise, or setting reminders.",
            "actionData": {}
        }), 200


@chatbot_bp.route("/history", methods=["GET"])
@jwt_required()
def get_history():
    """GET /api/chatbot/history: Fetch chat history."""
    user_id = get_jwt_identity()
    messages = ChatMessage.query.filter_by(user_id=user_id).order_by(ChatMessage.timestamp.asc()).all()
    return jsonify({"messages": [m.to_dict() for m in messages]}), 200


@chatbot_bp.route("/clear", methods=["POST"])
@jwt_required()
def clear_history():
    """POST /api/chatbot/clear: Clear chat logs."""
    user_id = get_jwt_identity()
    ChatMessage.query.filter_by(user_id=user_id).delete()
    db.session.commit()
    return jsonify({"message": "Chat history cleared successfully."}), 200


@chatbot_bp.route("/reminders", methods=["GET", "POST"])
@jwt_required()
def manage_reminders():
    """GET/POST /api/chatbot/reminders."""
    user_id = get_jwt_identity()
    if request.method == "GET":
        reminders = WellnessReminder.query.filter_by(user_id=user_id, is_active=True).order_by(WellnessReminder.created_at.desc()).all()
        return jsonify({"reminders": [r.to_dict() for r in reminders]}), 200

    data = request.get_json() or {}
    title = data.get("title", "💧 Drink Water & Stay Hydrated")
    reminder_type = data.get("reminderType", "hydration")
    time_str = data.get("timeStr", "Every 2 hours")

    reminder = WellnessReminder(
        user_id=user_id,
        title=title,
        reminder_type=reminder_type,
        time_str=time_str,
        is_active=True
    )
    db.session.add(reminder)
    db.session.commit()

    return jsonify({"message": "Reminder created", "reminder": reminder.to_dict()}), 201


@chatbot_bp.route("/reminders/<int:reminder_id>", methods=["DELETE"])
@jwt_required()
def delete_reminder(reminder_id):
    """DELETE /api/chatbot/reminders/<id>."""
    user_id = get_jwt_identity()
    reminder = WellnessReminder.query.filter_by(id=reminder_id, user_id=user_id).first()
    if not reminder:
        return jsonify({"message": "Reminder not found"}), 404

    db.session.delete(reminder)
    db.session.commit()
    return jsonify({"message": "Reminder deleted"}), 200


@chatbot_bp.route("/checkups", methods=["GET", "POST"])
@jwt_required()
def manage_checkups():
    """GET/POST /api/chatbot/checkups."""
    user_id = int(get_jwt_identity())
    if request.method == "GET":
        checkups = HealthCheckupSchedule.query.filter_by(user_id=user_id).order_by(HealthCheckupSchedule.created_at.desc()).all()
        return jsonify({"checkups": [c.to_dict() for c in checkups]}), 200

    data = request.get_json() or {}
    checkup_type = data.get("checkupType", "Comprehensive Health Screening")
    scheduled_date = data.get("scheduledDate", (datetime.date.today() + datetime.timedelta(days=7)).strftime("%Y-%m-%d"))

    checkup = HealthCheckupSchedule(
        user_id=user_id,
        checkup_type=checkup_type,
        scheduled_date=scheduled_date,
        status="Scheduled",
        notes=data.get("notes", "Scheduled via Wellness Assistant")
    )
    db.session.add(checkup)
    db.session.commit()

    return jsonify({"message": "Checkup scheduled", "checkup": checkup.to_dict()}), 201


@chatbot_bp.route("/checkups/<int:checkup_id>", methods=["DELETE"])
@jwt_required()
def delete_checkup(checkup_id):
    """DELETE /api/chatbot/checkups/<id>: Remove a scheduled checkup."""
    user_id = int(get_jwt_identity())
    checkup = HealthCheckupSchedule.query.filter_by(id=checkup_id, user_id=user_id).first()
    if not checkup:
        return jsonify({"message": "Checkup not found"}), 404
    db.session.delete(checkup)
    db.session.commit()
    return jsonify({"message": "Checkup removed successfully"}), 200
