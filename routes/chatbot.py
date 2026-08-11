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
    HealthCheckupSchedule,
    MedicalReport
)

chatbot_bp = Blueprint("chatbot", __name__, url_prefix="/api/chatbot")


def get_current_user(user_id):
    """Fetch user record or return None."""
    return User.query.get(user_id)


# --- Agentic State Graph AI Coach Engine Node Pipeline ---

def memory_node(state):
    """NODE 1: Memory & Context Synthesizer Node
    Prepares active study context, chat history, and employee database vitals."""
    user_id = state["user_id"]
    
    # Fetch user profile & latest health records
    profile = EmployeeProfile.query.filter_by(user_id=user_id).first()
    latest_record = HealthRecord.query.filter_by(user_id=user_id).order_by(HealthRecord.record_date.desc()).first()
    
    state["vitals"]["emp_name"] = profile.full_name if profile and profile.full_name else "Employee"
    state["vitals"]["health_score"] = latest_record.health_score if latest_record else 85
    state["vitals"]["sleep_hrs"] = latest_record.sleep_hours if latest_record else 7.5
    state["vitals"]["stress_lvl"] = latest_record.stress_level if latest_record else "Low"

    # Load recent chat messages for conversational memory context
    history_msgs = ChatMessage.query.filter_by(user_id=user_id).order_by(ChatMessage.timestamp.desc()).limit(6).all()
    history_msgs.reverse()
    state["history"] = [{"role": m.sender, "content": m.text} for m in history_msgs]
    
    state["context_summary"] = (
        f"Employee: {state['vitals']['emp_name']} | Health Score: {state['vitals']['health_score']}/100 | "
        f"Sleep Avg: {state['vitals']['sleep_hrs']} hours | Stress Balance: {state['vitals']['stress_lvl']}"
    )
    return state


def router_node(state):
    """NODE 2: Router & Intent Classification Node
    Uses Gemini Generative Model to classify user intent, or falls back to rules."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    has_gemini = bool(api_key and api_key != "your_gemini_api_key_here")
    
    if has_gemini:
        system_instruction = (
            "You are the Intent & Context Router for an AI Wellness Coach.\n"
            "Analyze the user's message and classify the intent into exactly one of these categories:\n"
            "- VIEW_HEALTH_RECORD: User wants to see their health record data, vitals, logs, weight/height metrics, or bp/heart rate.\n"
            "- VIEW_MEDICAL_REPORTS: User wants to see, list, fetch, or access their uploaded medical reports, PDFs, checkup summaries, or doctor lab results.\n"
            "- SCHEDULE_ACTION: User asks to book/schedule a checkup, or set a reminder (water, stretch, sleep).\n"
            "- TRACK_GOALS: User asks about their goals, progress, milestones, or how they are doing.\n"
            "- WELLNESS_ADVICE: User asks for tips or coaching on diet, nutrition, sleep hygiene, stress, exercise, or ergonomics.\n"
            "- EMPATHY_SUPPORT: User expresses feeling down, sad, lonely, depressed, stressed, or burnt out.\n"
            "- GENERAL_CONVERSATION: Small talk, greetings, model details, or warm chat.\n"
            "- OFF_TOPIC: Unrelated general questions (celebrities, politics, sports, general knowledge).\n\n"
            "Return ONLY a JSON object with this format:\n"
            "{\"intent\": \"CATEGORY_NAME\", \"topic\": \"Short Topic Summary\"}"
        )
        payload = {
            "contents": [{
                "parts": [{"text": f"{system_instruction}\n\nUser message: \"{state['message']}\"\nHistory: {json.dumps(state['history'])}"}]
            }]
        }
        try:
            payload_bytes = json.dumps(payload).encode("utf-8")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
            req = urllib.request.Request(
                url,
                data=payload_bytes,
                headers={"Content-Type": "application/json", "x-goog-api-key": api_key}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                cleaned = raw_text.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(cleaned)
                state["intent"] = parsed.get("intent", "GENERAL_CONVERSATION")
                state["current_topic"] = parsed.get("topic", "General Well-being")
                return state
        except Exception as e:
            print(f"Gemini Router warning: {e}")

    # Local Socratic Keyword Fallback
    p_lower = state["message"].lower()
    if any(k in p_lower for k in ["medical report", "my report", "uploaded report", "my reports", "my pdf", "blood test report", "doctor report", "reports"]):
        state["intent"] = "VIEW_MEDICAL_REPORTS"
        state["current_topic"] = "Medical Report"
    elif any(k in p_lower for k in ["health record", "health data", "my record", "my data", "blood pressure", "heart rate", "bp log", "vitals", "systolic", "diastolic", "my bp", "my height", "my weight", "bmi", "past bmi", "body mass index", "my sleep", "water intake", "my log", "my logs", "check-in"]):
        state["intent"] = "VIEW_HEALTH_RECORD"
        state["current_topic"] = "Health Record"
    elif any(k in p_lower for k in ["schedule checkup", "book checkup", "doctor appointment", "health checkup", "schedule appointment"]):
        state["intent"] = "SCHEDULE_ACTION"
        state["current_topic"] = "Preventive Checkup"
    elif any(k in p_lower for k in ["set reminder", "remind me", "water reminder", "stretch reminder", "hydration reminder"]):
        state["intent"] = "SCHEDULE_ACTION"
        state["current_topic"] = "Wellness Reminder"
    elif any(k in p_lower for k in ["track goal", "my goals", "progress", "milestone", "score", "how am i doing"]):
        state["intent"] = "TRACK_GOALS"
        state["current_topic"] = "Goal Performance"
    elif any(k in p_lower for k in ["diet", "food", "nutrition", "calories", "calorie", "body fat", "meal"]):
        state["intent"] = "WELLNESS_ADVICE"
        state["current_topic"] = "Nutrition"
    elif any(k in p_lower for k in ["sleep", "insomnia", "tired", "rest", "night"]):
        state["intent"] = "WELLNESS_ADVICE"
        state["current_topic"] = "Sleep Hygiene"
    elif any(k in p_lower for k in ["stress", "anxiety", "overwhelmed", "workload", "burnout", "exhausted"]):
        state["intent"] = "WELLNESS_ADVICE"
        state["current_topic"] = "Stress Coaching"
    elif any(k in p_lower for k in ["exercise", "workout", "gym", "fitness", "steps", "active", "stretch", "ergonomics"]):
        state["intent"] = "WELLNESS_ADVICE"
        state["current_topic"] = "Physical Fitness & Ergonomics"
    elif any(k in p_lower for k in ["sad", "depressed", "unhappy", "lonely", "feeling low", "feeling down", "bad day", "upset"]):
        state["intent"] = "EMPATHY_SUPPORT"
        state["current_topic"] = "Emotional Wellness"
    elif any(k in p_lower for k in ["hello", "hi", "hey", "who are you", "what are you", "model"]):
        state["intent"] = "GENERAL_CONVERSATION"
        state["current_topic"] = "General Conversation"
    else:
        state["intent"] = "WELLNESS_ADVICE"
        state["current_topic"] = "General Health Inquiry"
    return state


def resolve_contextual_navigation(message, history):
    p_lower = message.lower()
    # Check if the query is a relative navigation request
    relative_keywords = ["that page", "go there", "take me there", "open it", "navigate to it", "show it", "navigate me there", "view it"]
    if any(rk in p_lower for rk in relative_keywords) or p_lower.strip() in ["navigate", "open", "show", "go"]:
        # Scan history from latest to oldest
        for msg in reversed(history):
            text = msg["content"].lower()
            if any(k in text for k in ["stress", "mental", "sentiment", "anxiety", "depressed", "mood", "cortisol"]):
                return "sentimentView", "Mental Health & Sentiment"
            if any(k in text for k in ["bmi", "weight", "height", "blood pressure", "heart rate", "bp", "vital"]):
                return "healthDataView", "Health Data"
            if any(k in text for k in ["report", "pdf"]):
                return "reportsView", "Medical Reports"
            if any(k in text for k in ["risk", "prediction", "cardiovascular", "diabetes"]):
                return "riskView", "Wellness Risk Prediction"
            if any(k in text for k in ["recommendation", "advice", "tips", "routine"]):
                return "recommendationsView", "Wellness Recommendations"
            if any(k in text for k in ["tracker", "checklist", "water", "stretch", "sleep reminder", "remind"]):
                return "trackerView", "Daily Tracker"
            if any(k in text for k in ["leaderboard", "rank", "score"]):
                return "leaderboardView", "Leaderboard"
    return None, None


def action_tool_node(state):
    """NODE 3: Action Tool Node
    Executes database operations and maps navigation/view commands to UI trigger hooks."""
    intent = state["intent"]
    p_lower = state["message"].lower()
    user_id = state["user_id"]
    history = state.get("history", [])
    
    # 1. Contextual Navigation Resolution
    nav_view, nav_label = resolve_contextual_navigation(state["message"], history)
    if nav_view:
        state["action"] = "navigate"
        state["action_data"] = {"navigate": nav_view}
        state["intent"] = "NAVIGATION_CONFIRMATION"
        state["current_topic"] = nav_label
        return state

    # 2. Page/View Navigation Triggers
    if any(k in p_lower for k in ["navigate to", "open page", "go to page", "show page", "view page", "show my", "show me", "canyou show", "canyou show my", "where is", "open tab"]):
        if "health record" in p_lower or "health data" in p_lower or "vital" in p_lower or "bmi" in p_lower:
            state["action"] = "navigate"
            state["action_data"] = {"navigate": "healthDataView"}
            return state
        elif "risk" in p_lower or "prediction" in p_lower:
            state["action"] = "navigate"
            state["action_data"] = {"navigate": "riskView"}
            return state
        elif "report" in p_lower or "medical" in p_lower:
            state["action"] = "navigate"
            state["action_data"] = {"navigate": "reportsView"}
            return state
        elif "recommendation" in p_lower or "advice" in p_lower:
            state["action"] = "navigate"
            state["action_data"] = {"navigate": "recommendationsView"}
            return state
        elif "sentiment" in p_lower or "mental" in p_lower or "mood" in p_lower or "stress" in p_lower:
            state["action"] = "navigate"
            state["action_data"] = {"navigate": "sentimentView"}
            return state
        elif "analytics" in p_lower or "chart" in p_lower or "graph" in p_lower:
            state["action"] = "navigate"
            state["action_data"] = {"navigate": "employeeAnalyticsView"}
            return state
        elif "tracker" in p_lower or "checklist" in p_lower:
            state["action"] = "navigate"
            state["action_data"] = {"navigate": "trackerView"}
            return state
        elif "leaderboard" in p_lower or "rank" in p_lower or "score" in p_lower:
            state["action"] = "navigate"
            state["action_data"] = {"navigate": "leaderboardView"}
            return state

    if intent == "VIEW_HEALTH_RECORD":
        state["action"] = "navigate"
        state["action_data"] = {"navigate": "healthDataView"}
    elif intent == "VIEW_MEDICAL_REPORTS":
        state["action"] = "navigate"
        state["action_data"] = {"navigate": "reportsView"}
    elif intent == "SCHEDULE_ACTION":
        if any(k in p_lower for k in ["checkup", "appointment"]):
            target_date = (datetime.date.today() + datetime.timedelta(days=7)).strftime("%Y-%m-%d")
            checkup = HealthCheckupSchedule(
                user_id=user_id,
                checkup_type="Comprehensive Preventive Health Screening",
                scheduled_date=target_date,
                status="Scheduled",
                notes="Booked via AI Socratic Wellness Coach"
            )
            db.session.add(checkup)
            db.session.commit()
            state["action_data"] = {"checkup": checkup.to_dict()}
            state["action"] = "scheduled_checkup"
        elif any(k in p_lower for k in ["reminder", "remind"]):
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
            state["action_data"] = {"reminder": reminder.to_dict()}
            state["action"] = "set_reminder"
            
    return state


def specialist_node(state):
    """NODE 4: Specialist Node (Deep Socratic Reasoning Engine)
    Generates tailored, conversational, step-by-step coaching feedback."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    has_gemini = bool(api_key and api_key != "your_gemini_api_key_here")
    
    emp_name = state["vitals"]["emp_name"]
    health_score = state["vitals"]["health_score"]
    sleep_hrs = state["vitals"]["sleep_hrs"]
    stress_lvl = state["vitals"]["stress_lvl"]
    user_id = state["user_id"]
    
    latest_record = HealthRecord.query.filter_by(user_id=user_id).order_by(HealthRecord.record_date.desc()).first()
    reports = MedicalReport.query.filter_by(user_id=user_id).order_by(MedicalReport.uploaded_at.desc()).all()
    
    if has_gemini:
        # Load complete context from DB to inject into Gemini prompt
        db_context = "No health logs found."
        if latest_record:
            bp_systolic = latest_record.bp_systolic if latest_record.bp_systolic else "Not logged"
            bp_diastolic = latest_record.bp_diastolic if latest_record.bp_diastolic else "Not logged"
            resting_hr = latest_record.resting_heart_rate if latest_record.resting_heart_rate else "Not logged"
            water_liters = latest_record.water_intake_liters if latest_record.water_intake_liters else "Not logged"
            db_context = (
                f"Employee's latest database HealthRecord details:\n"
                f"- Log Date: {latest_record.record_date}\n"
                f"- Height: {latest_record.height_cm} cm | Weight: {latest_record.weight_kg} kg\n"
                f"- BMI: {latest_record.bmi:.1f} ({latest_record.bmi_category})\n"
                f"- Blood Pressure: {bp_systolic}/{bp_diastolic} mmHg\n"
                f"- Resting Heart Rate: {resting_hr} bpm\n"
                f"- Sleep Hours: {latest_record.sleep_hours} hrs/night\n"
                f"- Water Intake: {water_liters} Liters/day\n"
                f"- Stress Level: {latest_record.stress_level}\n"
                f"- Exercise Frequency: {latest_record.exercise_frequency} ({latest_record.exercise_minutes_per_week} mins/week)\n"
                f"- Attendance status: {latest_record.attendance_status}"
            )
        
        reports_context = "No uploaded medical reports found."
        if reports:
            reports_context = "Uploaded medical reports list:\n" + "\n".join([f"- Name: {r.report_name}, Type: {r.report_type}, Uploaded: {r.uploaded_at}" for r in reports])
            
        system_instruction = (
            f"You are a friendly, highly professional 24/7 AI Socratic Wellness Coach coaching {emp_name}.\n"
            f"Employee context: Health Score {health_score}/100, Sleep Average {sleep_hrs} hrs, Stress Level {stress_lvl}.\n"
            f"Classified Intent: {state['intent']}. Classified Topic: {state['current_topic']}.\n"
            f"{db_context}\n"
            f"{reports_context}\n\n"
            f"ROLE STYLE: You use a Socratic coaching style. Do not just spit out long lists of answers. "
            f"Instead, guide {emp_name} step-by-step. Ask brief, open-ended questions about their habits, sleep patterns, "
            f"stress triggers, or exercise routines to help them discover their own path to better health.\n"
            f"Provide short, supportive, concise guidance with 1-2 bullet points and friendly emojis, then ask an engaging follow-up question.\n"
            f"STRICT RULE: You MUST ONLY answer questions related to health, wellness, fitness, nutrition, sleep, stress, "
            f"mental health, exercise, medical topics, employee wellbeing, or this wellness management project. "
            f"If the user asks anything unrelated, politely decline and steer them back to wellness."
        )
        payload = {
            "contents": [{
                "parts": [{"text": f"{system_instruction}\n\nEmployee Query: {state['message']}"}]
            }]
        }
        try:
            payload_bytes = json.dumps(payload).encode("utf-8")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
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
                        state["reply"] = text.strip()
                        return state
        except Exception as exc:
            print(f"Gemini Specialist warning: {exc}")

    # Fallback Socratic Response Generator (Local Rules)
    intent = state["intent"]
    topic = state["current_topic"]
    
    if intent == "NAVIGATION_CONFIRMATION":
        state["reply"] = (
            f"🚀 **Opening the {topic} section for you!**\n\n"
            f"I have automatically switched the dashboard view to the **{topic}** page as requested.\n\n"
            f"💬 *Would you like me to walk you through any details or trends on this page?*"
        )
    elif intent == "VIEW_HEALTH_RECORD":
        all_records = HealthRecord.query.filter_by(user_id=user_id).order_by(HealthRecord.record_date.desc()).all()
        if all_records:
            latest = all_records[0]
            bp_text = f"{latest.bp_systolic}/{latest.bp_diastolic} mmHg" if latest.bp_systolic else "Not logged"
            hr_text = f"{latest.resting_heart_rate} bpm" if latest.resting_heart_rate else "Not logged"
            water_text = f"{latest.water_intake_liters} L" if latest.water_intake_liters else "Not logged"
            
            reply = (
                f"📊 **Your Latest Wellness & Health Record Details:**\n\n"
                f"• **Log Date**: {latest.record_date.strftime('%B %d, %Y')}\n"
                f"• **Physical Vitals**:\n"
                f"  - Height: **{latest.height_cm} cm** | Weight: **{latest.weight_kg} kg**\n"
                f"  - BMI: **{latest.bmi:.1f}** ({latest.bmi_category})\n"
                f"  - Blood Pressure: **{bp_text}**\n"
                f"  - Resting Heart Rate: **{hr_text}**\n"
                f"• **Lifestyle Indicators**:\n"
                f"  - Sleep Average: **{latest.sleep_hours} hours/night**\n"
                f"  - Water Intake: **{water_text}**\n"
                f"  - Stress Balance: **{latest.stress_level}**\n"
                f"  - Activity Level: **{latest.exercise_frequency}** ({latest.exercise_minutes_per_week} mins/week)\n"
            )
            
            if len(all_records) > 1:
                trends = []
                for r in all_records[1:5]:
                    trends.append(f"- *{r.record_date.strftime('%b %d, %Y')}*: BMI **{r.bmi:.1f}** | BP **{r.bp_systolic}/{r.bp_diastolic}** | Sleep **{r.sleep_hours} hrs**")
                trend_text = "\n".join(trends)
                reply += f"\n📈 **Past Records & BMI Trends:**\n{trend_text}\n"
                
            reply += (
                f"\nI have also automatically opened the **Health Data** page for you. "
                f"💬 *Looking at your BMI and vital logs, what changes or wellness goals do you want to explore next?*"
            )
            state["reply"] = reply
        else:
            state["reply"] = (
                f"📊 **Health Record Lookup:**\n\n"
                f"Hello {emp_name}, I searched your database files but couldn't find any health records logged yet.\n\n"
                f"I have loaded the **Health Data** tab so you can input your first wellness metrics check-in. "
                f"💬 *Would you like help calculating your baseline BMI or logging your daily sleep hours?*"
            )
    elif intent == "VIEW_MEDICAL_REPORTS":
        if reports:
            report_list_md = "\n".join([f"• 📄 **{r.report_name}** ({r.report_type}) - *Uploaded on {r.uploaded_at.strftime('%B %d, %Y')}*" for r in reports])
            state["reply"] = (
                f"📋 **Here are your uploaded Medical Reports:**\n\n"
                f"{report_list_md}\n\n"
                f"I have also automatically opened the **Medical Reports** section so you can upload new health files or review these PDFs. "
                f"💬 *Would you like me to explain any clinical values or medical checkup terms?*"
            )
        else:
            state["reply"] = (
                f"📋 **Medical Reports Lookup:**\n\n"
                f"Hello {emp_name}, I searched your record files but couldn't find any uploaded medical reports in the database.\n\n"
                f"I have opened the **Medical Reports** tab for you so you can upload your first PDF. "
                f"💬 *Would you like to walk through how to upload a report?*"
            )
    elif intent == "SCHEDULE_ACTION":
        if state["action"] == "scheduled_checkup":
            state["reply"] = (
                f"📅 **Health Checkup Scheduled Successfully!**\n\n"
                f"Hello {emp_name}, I have scheduled your **Comprehensive Preventive Health Screening** for next week.\n\n"
                f"💬 *Preventive care is a great baseline. What specific metrics or checks are you hoping to review with the doctor?*"
            )
        else:
            state["reply"] = (
                f"⏰ **Wellness Reminder Created!**\n\n"
                f"I have successfully activated your wellness reminder.\n\n"
                f"💬 *Consistency with small habits makes a massive difference over time. How do you plan to keep yourself accountable to this new reminder?*"
            )
    elif intent == "TRACK_GOALS":
        state["reply"] = (
            f"🎯 **Personal Health Goal Progress for {emp_name}:**\n\n"
            f"• **Overall Health Score:** {health_score} / 100 ({'Optimal' if health_score >= 80 else 'Moderate'})\n"
            f"• **Sleep Average:** {sleep_hrs} hrs / night (Target: 7.5 hrs)\n"
            f"• **Stress Balance:** {stress_lvl} Mental Stress\n\n"
            f"💬 *Looking at these metrics, which area—sleep, stress, or overall score—do you feel we should tackle together first?*"
        )
    elif intent == "EMPATHY_SUPPORT":
        state["reply"] = (
            f"🫂 **I'm here for you, {emp_name}.**\n\n"
            f"I'm sorry to hear that you are feeling down or overwhelmed today. It is completely normal to have low-energy days.\n\n"
            f"• **Micro-Reset**: Taking 5 slow box-breaths can help anchor your nervous system.\n\n"
            f"💬 *When you're feeling this way, do you find it more helpful to rest quietly, or would you like to walk through a quick, 2-minute breathing exercise together?*"
        )
    elif intent == "WELLNESS_ADVICE":
        p_lower = state["message"].lower()
        
        # 1. Stress medications / aids (check typo meds/madicine/medecine/drug)
        if ("stress" in topic.lower() or "stress" in p_lower) and any(w in p_lower for w in ["medicine", "medication", "drug", "pill", "tablet", "prescribe", "madicine", "medecine", "meds", "treatment", "cure"]):
            state["reply"] = (
                f"💊 **Stress Medications & Aids:**\n"
                f"• **Natural/OTC**: Ashwagandha, L-Theanine, Chamomile, or Magnesium Glycinate.\n"
                f"• **Prescription**: Beta-blockers or SSRIs (consult a medical physician first).\n\n"
                f"💬 *Would you like me to schedule a preventive health checkup to discuss prescriptions?*"
            )
            
        # 2. Sleep medications / aids
        elif ("sleep" in topic.lower() or "sleep" in p_lower) and any(w in p_lower for w in ["medicine", "medication", "drug", "pill", "tablet", "prescribe", "madicine", "medecine", "meds", "treatment", "cure", "insomnia"]):
            state["reply"] = (
                f"💤 **Sleep Medications & Aids:**\n"
                f"• **Natural/OTC**: Melatonin, Valerian Root, Chamomile tea, or Magnesium.\n"
                f"• **Prescription**: Z-drugs or Orexin antagonists (consult a physician first).\n\n"
                f"💬 *Would you like me to set a sleep hygiene reminder?*"
            )
            
        # 3. Nutrition, diet, food (check typo diet/dit/food/nutrition)
        elif "nutrition" in topic.lower() or "diet" in topic.lower() or any(w in p_lower for w in ["diet", "food", "nutrition", "meal", "breakfast", "eat", "protein", "dit"]):
            state["reply"] = (
                f"🥗 **Nutrition & Diet Guidelines:**\n"
                f"• **Recommended Foods**: Fatty fish (Omega-3), leafy greens, oats, berries, nuts, and clean proteins.\n"
                f"• **Avoid**: Processed sugars, simple carbohydrates, and late-night caffeine.\n\n"
                f"💬 *Would you like me to navigate to the Wellness Recommendations tab?*"
            )
            
        # 4. Exercise & Fitness (gym/workout/exercise)
        elif "fitness" in topic.lower() or "exercise" in topic.lower() or any(w in p_lower for w in ["gym", "workout", "routine", "exercise", "plan", "fitness", "active", "stretching"]):
            state["reply"] = (
                f"🏃 **Exercise & Fitness Plan:**\n"
                f"• **Cardio**: 20-30 mins of walking, cycling, or jogging 3x a week.\n"
                f"• **Strength**: Simple bodyweight movements (planks, squats, push-ups).\n\n"
                f"💬 *Would you like me to set a reminder for a quick workout break?*"
            )
            
        # 5. General Stress
        elif "stress" in topic.lower() or "stress" in p_lower:
            state["reply"] = (
                f"🧠 **Stress Management:**\n"
                f"• **Breathing**: Try 5 slow box-breaths to reset your nervous system.\n"
                f"• **Ergonomic**: Take a short 5-minute desk stretch break.\n\n"
                f"💬 *Do you prefer a physical stretch or a mental breathing pause?*"
            )
            
        # 6. Default Fallback
        else:
            state["reply"] = (
                f"🏃 **Wellness Advice:**\n"
                f"• **Daily Vitals**: Your current Health Score is **{health_score}/100**.\n"
                f"• **Actionable**: Log your sleep, keep active, and minimize stress levels.\n\n"
                f"💬 *What health metric are you focusing on today?*"
            )
    elif intent == "GENERAL_CONVERSATION":
        state["reply"] = (
            f"🤖 **Hello {emp_name}!**\n\n"
            f"I am your dedicated **AI Socratic Wellness Coach**. I am designed to help you build positive daily habits, track metrics, schedule preventive appointments, and manage stress.\n\n"
            f"💬 *What wellness goals or concerns are on your mind today?*"
        )
    else:
        state["reply"] = (
            f"🚫 Hello {emp_name}, I am your **AI Socratic Wellness Coach**.\n\n"
            f"To get the most out of our session, I focus on health, fitness, and stress goals.\n\n"
            f"💬 *Which area—sleep, stress, activity, or scheduling a health checkup—would you like to explore today?*"
        )
    return state


def output_formatter_node(state):
    """NODE 5: Output Formatter Node
    Synthesizes and packages the final formatted conversational payload."""
    if "?" not in state["reply"]:
        state["reply"] += "\n\n💬 *What do you think is the best next step for you to try?*"
    return state


def process_nlp_intent(user_id, prompt):
    """Context-aware Smart NLP Chatbot Engine for Employee Wellness (State Graph Workflow)."""
    # Initialize State Graph Context
    state = {
        "user_id": user_id,
        "message": prompt,
        "history": [],
        "intent": "GENERAL_CONVERSATION",
        "current_topic": "General Well-being",
        "context_summary": "",
        "action": None,
        "action_data": {},
        "reply": "",
        "vitals": {
            "emp_name": "Employee",
            "health_score": 85,
            "sleep_hrs": 7.5,
            "stress_lvl": "Low"
        }
    }

    # Pipeline Executions
    state = memory_node(state)
    state = router_node(state)
    state = action_tool_node(state)
    state = specialist_node(state)
    state = output_formatter_node(state)

    return state["intent"], state["reply"], state["action_data"]


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
