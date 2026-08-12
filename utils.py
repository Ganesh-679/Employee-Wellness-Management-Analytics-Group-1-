import re
import random
import smtplib
from datetime import date, datetime
from email.mime.text import MIMEText

EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def is_valid_email(email):
    return bool(email) and bool(EMAIL_REGEX.match(email.strip()))


def get_password_checks(password):
    """Mirrors js/validation.js -> getPasswordChecks() exactly, so the
    backend enforces the identical rules the frontend already shows the
    user via the live checklist."""
    password = password or ""
    return {
        "length": len(password) >= 8,
        "lowercase": bool(re.search(r"[a-z]", password)),
        "uppercase": bool(re.search(r"[A-Z]", password)),
        "number": bool(re.search(r"[0-9]", password)),
        "special": bool(re.search(r"[^A-Za-z0-9]", password)),
    }


def is_password_valid(password):
    return all(get_password_checks(password).values())


def failed_password_rules(password):
    """Returns a list of human-readable rule names that failed, useful for
    a precise 400 error message."""
    checks = get_password_checks(password)
    labels = {
        "length": "at least 8 characters",
        "lowercase": "one lowercase letter",
        "uppercase": "one uppercase letter",
        "number": "one number",
        "special": "one special character",
    }
    return [labels[rule] for rule, passed in checks.items() if not passed]


def generate_otp():
    """6-digit numeric OTP, e.g. '482913'."""
    return f"{random.randint(0, 999999):06d}"


def send_otp_email(to_address, otp_code, app_config):
    """
    Sends the OTP by email if MAIL_SERVER is configured. Otherwise, just
    logs it to the console so you can test the forgot-password flow
    locally without setting up a real mail server.

    Wire up real SMTP creds (e.g. Gmail app password, SendGrid, etc.) in
    your environment variables (see config.py) once the team is ready.
    """
    if not app_config.get("MAIL_SERVER"):
        print(f"[DEV] OTP for {to_address}: {otp_code} (no MAIL_SERVER configured, not emailed)")
        return

    message = MIMEText(f"Your Wellness Management verification code is: {otp_code}\n"
                        f"It expires in {app_config.get('OTP_EXPIRY_MINUTES', 10)} minutes.")
    message["Subject"] = "Your verification code"
    message["From"] = app_config.get("MAIL_SENDER")
    message["To"] = to_address

    with smtplib.SMTP(app_config["MAIL_SERVER"], app_config["MAIL_PORT"]) as server:
        server.starttls()
        server.login(app_config["MAIL_USERNAME"], app_config["MAIL_PASSWORD"])
        server.sendmail(app_config.get("MAIL_SENDER"), [to_address], message.as_string())
# =========================================================================
# Module 1: Employee Health Data Management
# -------------------------------------------------------------------------
# "AI techniques used: data preprocessing, data integration, AI-based data
# validation" — implemented here as:
#   - preprocessing: coercing/rounding raw input into clean numeric types
#   - integration: combining BMI + exercise + sleep + attendance + checkup
#     into one normalized record shape (see routes/health.py)
#   - AI-based (rule-based) data validation: an expert-system style rule
#     engine below that both rejects impossible data and flags
#     biologically-plausible-but-concerning values for review.
# =========================================================================

VALID_EXERCISE_FREQUENCIES = {"Sedentary", "Light", "Moderate", "Active"}
VALID_ATTENDANCE_STATUSES = {"Present", "Absent", "Leave", "WFH"}
VALID_CHECKUP_RESULTS = {"Normal", "NeedsAttention", "Critical"}
VALID_STRESS_LEVELS = {"Low", "Medium", "High"}
VALID_SMOKING_STATUSES = {"Never", "Former", "Current"}
VALID_ALCOHOL_LEVELS = {"None", "Occasional", "Regular"}


def calculate_bmi(height_cm, weight_kg):
    """Returns BMI rounded to 1 decimal. Raises ValueError on non-physical input."""
    if height_cm <= 0 or weight_kg <= 0:
        raise ValueError("Height and weight must be positive numbers")
    height_m = height_cm / 100
    return round(weight_kg / (height_m ** 2), 1)


def bmi_category(bmi):
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal"
    if bmi < 30:
        return "Overweight"
    return "Obese"


def _parse_date(value, field_name, errors):
    """Preprocessing helper: coerces an incoming 'YYYY-MM-DD' string into a
    date object, recording an error instead of raising if it's malformed."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        errors.append(f"{field_name} must be a valid date in YYYY-MM-DD format")
        return None


def validate_and_normalize_health_data(payload):
    """Rule-based validation + preprocessing for one health record submission.

    Returns (normalized: dict | None, errors: list[str], warnings: list[str]).
    - `errors` non-empty  -> reject the submission (400), data is impossible/unusable.
    - `warnings` non-empty -> accept, but flag the record for admin review
      (validation_status = 'flagged'), since the value is a plausible but
      unusual health signal (e.g. very low sleep, very high BMI).
    """
    errors = []
    warnings = []

    # ---- Preprocessing: coerce numeric fields safely ----
    try:
        height_cm = float(payload.get("heightCm"))
    except (TypeError, ValueError):
        height_cm = None
        errors.append("heightCm must be a number")

    try:
        weight_kg = float(payload.get("weightKg"))
    except (TypeError, ValueError):
        weight_kg = None
        errors.append("weightKg must be a number")

    try:
        sleep_hours = float(payload.get("sleepHours"))
    except (TypeError, ValueError):
        sleep_hours = None
        errors.append("sleepHours must be a number")

    try:
        exercise_minutes = int(payload.get("exerciseMinutesPerWeek", 0) or 0)
    except (TypeError, ValueError):
        exercise_minutes = None
        errors.append("exerciseMinutesPerWeek must be a whole number")

    # ---- Optional vitals/lifestyle fields (feed Module 2 risk prediction) ----
    def _optional_number(key, cast, label):
        raw = payload.get(key)
        if raw in (None, ""):
            return None
        try:
            return cast(raw)
        except (TypeError, ValueError):
            errors.append(f"{label} must be a number")
            return None

    water_intake_liters = _optional_number("waterIntakeLiters", float, "waterIntakeLiters")
    bp_systolic = _optional_number("bpSystolic", int, "bpSystolic")
    bp_diastolic = _optional_number("bpDiastolic", int, "bpDiastolic")
    resting_heart_rate = _optional_number("restingHeartRate", int, "restingHeartRate")

    stress_level = (payload.get("stressLevel") or "").strip() or None
    smoking_status = (payload.get("smokingStatus") or "").strip() or None
    alcohol_consumption = (payload.get("alcoholConsumption") or "").strip() or None

    exercise_frequency = (payload.get("exerciseFrequency") or "").strip()
    attendance_status = (payload.get("attendanceStatus") or "").strip()
    checkup_result = (payload.get("checkupResult") or "").strip() or None

    record_date = _parse_date(payload.get("recordDate"), "recordDate", errors)
    checkup_date = _parse_date(payload.get("checkupDate"), "checkupDate", errors) \
        if payload.get("checkupDate") else None

    # ---- Rule-based validation: hard errors (impossible/unusable data) ----
    if height_cm is not None and not (50 <= height_cm <= 250):
        errors.append("heightCm must be between 50 and 250 cm")
    if weight_kg is not None and not (20 <= weight_kg <= 300):
        errors.append("weightKg must be between 20 and 300 kg")
    if sleep_hours is not None and not (0 <= sleep_hours <= 24):
        errors.append("sleepHours must be between 0 and 24")
    if exercise_minutes is not None and not (0 <= exercise_minutes <= 2000):
        errors.append("exerciseMinutesPerWeek must be between 0 and 2000")
    if exercise_frequency and exercise_frequency not in VALID_EXERCISE_FREQUENCIES:
        errors.append(f"exerciseFrequency must be one of {sorted(VALID_EXERCISE_FREQUENCIES)}")
    elif not exercise_frequency:
        errors.append("exerciseFrequency is required")
    if attendance_status and attendance_status not in VALID_ATTENDANCE_STATUSES:
        errors.append(f"attendanceStatus must be one of {sorted(VALID_ATTENDANCE_STATUSES)}")
    elif not attendance_status:
        errors.append("attendanceStatus is required")
    if checkup_result and checkup_result not in VALID_CHECKUP_RESULTS:
        errors.append(f"checkupResult must be one of {sorted(VALID_CHECKUP_RESULTS)}")
    if water_intake_liters is not None and not (0 <= water_intake_liters <= 15):
        errors.append("waterIntakeLiters must be between 0 and 15")
    if bp_systolic is not None and not (60 <= bp_systolic <= 260):
        errors.append("bpSystolic must be between 60 and 260 mmHg")
    if bp_diastolic is not None and not (30 <= bp_diastolic <= 160):
        errors.append("bpDiastolic must be between 30 and 160 mmHg")
    if bp_systolic is not None and bp_diastolic is not None and bp_systolic <= bp_diastolic:
        errors.append("bpSystolic must be greater than bpDiastolic")
    if resting_heart_rate is not None and not (30 <= resting_heart_rate <= 220):
        errors.append("restingHeartRate must be between 30 and 220 bpm")
    if stress_level and stress_level not in VALID_STRESS_LEVELS:
        errors.append(f"stressLevel must be one of {sorted(VALID_STRESS_LEVELS)}")
    if smoking_status and smoking_status not in VALID_SMOKING_STATUSES:
        errors.append(f"smokingStatus must be one of {sorted(VALID_SMOKING_STATUSES)}")
    if alcohol_consumption and alcohol_consumption not in VALID_ALCOHOL_LEVELS:
        errors.append(f"alcoholConsumption must be one of {sorted(VALID_ALCOHOL_LEVELS)}")
    if record_date and record_date > date.today():
        errors.append("recordDate cannot be in the future")
    if checkup_date and checkup_date > date.today():
        errors.append("checkupDate cannot be in the future")
    if not record_date and "recordDate" not in [e.split()[0] for e in errors]:
        errors.append("recordDate is required")

    if errors:
        return None, errors, warnings

    # ---- BMI (data integration point: height + weight -> one derived metric) ----
    bmi = calculate_bmi(height_cm, weight_kg)
    category = bmi_category(bmi)

    # ---- Rule-based validation: soft warnings (plausible but concerning) ----
    if bmi < 15 or bmi > 45:
        warnings.append(f"BMI of {bmi} is an extreme value — please double-check height/weight")
    if sleep_hours < 4:
        warnings.append(f"Sleep of {sleep_hours}h/night is very low")
    elif sleep_hours > 11:
        warnings.append(f"Sleep of {sleep_hours}h/night is unusually high")
    if category == "Obese" and exercise_frequency == "Sedentary":
        warnings.append("Obese BMI combined with sedentary activity — flagged for wellness follow-up")
    if checkup_result == "Critical":
        warnings.append("Check-up marked Critical — flagged for admin attention")
    if bp_systolic is not None and bp_diastolic is not None:
        if bp_systolic >= 140 or bp_diastolic >= 90:
            warnings.append(f"Blood pressure {bp_systolic}/{bp_diastolic} mmHg suggests hypertension — flagged for review")
        elif bp_systolic < 90 or bp_diastolic < 60:
            warnings.append(f"Blood pressure {bp_systolic}/{bp_diastolic} mmHg is unusually low")
    if resting_heart_rate is not None and (resting_heart_rate > 100 or resting_heart_rate < 45):
        warnings.append(f"Resting heart rate of {resting_heart_rate} bpm is outside the typical range")
    if water_intake_liters is not None and water_intake_liters < 1:
        warnings.append(f"Water intake of {water_intake_liters}L/day is low — possible dehydration risk")
    if stress_level == "High":
        warnings.append("Self-reported stress level is High — flagged for wellness follow-up")

    normalized = {
        "record_date": record_date,
        "height_cm": round(height_cm, 1),
        "weight_kg": round(weight_kg, 1),
        "bmi": bmi,
        "bmi_category": category,
        "exercise_frequency": exercise_frequency,
        "exercise_minutes_per_week": exercise_minutes,
        "sleep_hours": round(sleep_hours, 1),
        "water_intake_liters": round(water_intake_liters, 1) if water_intake_liters is not None else None,
        "bp_systolic": bp_systolic,
        "bp_diastolic": bp_diastolic,
        "resting_heart_rate": resting_heart_rate,
        "stress_level": stress_level,
        "smoking_status": smoking_status,
        "alcohol_consumption": alcohol_consumption,
        "attendance_status": attendance_status,
        "checkup_date": checkup_date,
        "checkup_result": checkup_result,
        "checkup_notes": (payload.get("checkupNotes") or "").strip() or None,
        "assessment_notes": (payload.get("assessmentNotes") or "").strip() or None,
    }
    return normalized, errors, warnings


# =========================================================================
# Personal Information (part of Module 1 — employee profile fields)
# =========================================================================

def validate_and_normalize_profile_data(payload):
    """Light validation for the personal-information form. Everything here
    is optional except full_name, since employees may fill this in
    gradually."""
    errors = []

    full_name = (payload.get("fullName") or "").strip()
    if not full_name:
        errors.append("fullName is required")
    elif len(full_name) > 120:
        errors.append("fullName is too long")

    phone = (payload.get("phone") or "").strip()
    if phone and not re.match(r"^[0-9+\-\s()]{6,20}$", phone):
        errors.append("phone must be a valid phone number")

    date_of_joining = None
    raw_doj = payload.get("dateOfJoining")
    if raw_doj:
        try:
            date_of_joining = datetime.strptime(raw_doj, "%Y-%m-%d").date()
            if date_of_joining > date.today():
                errors.append("dateOfJoining cannot be in the future")
        except ValueError:
            errors.append("dateOfJoining must be a valid date in YYYY-MM-DD format")

    if errors:
        return None, errors

    normalized = {
        "full_name": full_name,
        "employee_code": (payload.get("employeeCode") or "").strip() or None,
        "designation": (payload.get("designation") or "").strip() or None,
        "department": (payload.get("department") or "").strip() or None,
        "date_of_joining": date_of_joining,
        "phone": phone or None,
        "work_location": (payload.get("workLocation") or "").strip() or None,
    }

    # Allow clearing the profile picture via PUT
    if "profilePicture" in payload:
        normalized["profile_picture"] = payload["profilePicture"]

    return normalized, errors
def calculate_health_score(data):
    score = 100

    bmi = data.get("bmi", 0)

    if bmi < 18.5 or bmi >= 30:
        score -= 20
    elif bmi >= 25:
        score -= 10

    sleep = data.get("sleep_hours", 0)

    if sleep < 5:
        score -= 20
    elif sleep < 7:
        score -= 10

    exercise = data.get("exercise_minutes_per_week", 0)

    if exercise < 150:
        score -= 10

    stress = data.get("stress_level")

    if stress == "High":
        score -= 20
    elif stress == "Medium":
        score -= 10

    bp_sys = data.get("bp_systolic")
    bp_dia = data.get("bp_diastolic")

    if bp_sys and bp_dia:
        if bp_sys >= 140 or bp_dia >= 90:
            score -= 20
        elif bp_sys >= 130 or bp_dia >= 85:
            score -= 10

    return max(score, 0)


def calculate_risk_level(data, warnings):

    score = calculate_health_score(data)

    if score >= 80:
        return "Low"

    elif score >= 50:
        return "Medium"

    return "High"


def analyze_mental_health_nlp(text):
    """
    Analyzes written text for sentiment, stress, anxiety, and burnout risk.
    Uses an explainable lexicon-based NLP algorithm with negation handling.
    """
    text = text or ""
    clean_text = re.sub(r"[^\w\s]", "", text.lower())
    words = clean_text.split()
    word_count = len(words)

    # Lexicon categories
    positives = {
        'happy', 'calm', 'good', 'great', 'excellent', 'motivated', 'energetic', 
        'relaxed', 'peaceful', 'productive', 'excited', 'balanced', 'well', 'healthy', 
        'positive', 'cheerful', 'joy', 'wonderful', 'amazing', 'love', 'content', 
        'satisfied', 'refreshed', 'peace', 'optimistic', 'hopeful', 'grateful', 'proud'
    }
    
    negatives = {
        'sad', 'depressed', 'anxious', 'stressed', 'tired', 'burnout', 'exhausted', 
        'angry', 'frustrated', 'bad', 'terrible', 'worst', 'pressure', 'deadline', 
        'overwhelmed', 'hate', 'unhappy', 'lonely', 'worry', 'hopeless', 'helpless', 
        'fear', 'scared', 'panic', 'tension', 'stressful', 'drained', 'fatigue', 
        'annoyed', 'disappointed', 'fail', 'failure', 'difficult', 'pain', 'struggle', 
        'struggling', 'cry', 'crying'
    }

    negations = {'not', 'no', 'never', 'dont', 'doesnt', 'wasnt', 'cant', 'cannot', 'without'}

    stress_keywords = {
        'stress', 'stressed', 'stressful', 'pressure', 'deadline', 'deadlines', 
        'overloaded', 'overwhelming', 'busy', 'rush', 'rushed', 'demanding', 'demands'
    }
    
    anxiety_keywords = {
        'anxious', 'anxiety', 'worried', 'worry', 'nervous', 'scared', 'panic', 
        'fear', 'tense', 'tension', 'uneasy', 'paranoid'
    }
    
    burnout_keywords = {
        'burnout', 'exhausted', 'drained', 'fatigued', 'tired', 'worn', 'empty', 
        'helpless', 'hopeless', 'overwhelmed', 'give', 'quitting', 'quit'
    }

    pos_count = 0
    neg_count = 0
    stress_hits = 0
    anxiety_hits = 0
    burnout_hits = 0

    for idx, word in enumerate(words):
        # Check if preceded by a negation word within 3 indices
        is_negated = False
        for offset in (1, 2, 3):
            if idx - offset >= 0 and words[idx - offset] in negations:
                is_negated = True
                break

        # Count sentiment categories
        if word in positives:
            if is_negated:
                neg_count += 1
            else:
                pos_count += 1
        elif word in negatives:
            if is_negated:
                pos_count += 1
            else:
                neg_count += 1

        # Count risk dimensions
        if word in stress_keywords:
            if not is_negated:
                stress_hits += 1
        if word in anxiety_keywords:
            if not is_negated:
                anxiety_hits += 1
        if word in burnout_keywords:
            if not is_negated:
                burnout_hits += 1

    # Normalize counts based on length (standardizing density per 15 words)
    scale_factor = max(1.0, word_count / 15.0)
    
    stress_prob = min(100.0, round((stress_hits / scale_factor) * 45.0, 1))
    anxiety_prob = min(100.0, round((anxiety_hits / scale_factor) * 45.0, 1))
    burnout_prob = min(100.0, round((burnout_hits / scale_factor) * 45.0, 1))

    # Base values if sentiment is highly negative
    sentiment_score = 0.0
    total_sentiment_words = pos_count + neg_count
    if total_sentiment_words > 0:
        sentiment_score = round((pos_count - neg_count) / total_sentiment_words, 2)
    else:
        # Default neutral or slight adjustments based on direct hits
        if stress_hits or anxiety_hits or burnout_hits:
            sentiment_score = -0.2
        else:
            sentiment_score = 0.0

    # Ensure negative sentiment bumps probabilities slightly
    if sentiment_score < -0.2:
        stress_prob = min(100.0, stress_prob + 15)
        anxiety_prob = min(100.0, anxiety_prob + 15)
        burnout_prob = min(100.0, burnout_prob + 15)

    # Determine labels
    if sentiment_score >= 0.15:
        sentiment_label = "Positive"
    elif sentiment_score <= -0.15:
        sentiment_label = "Negative"
    else:
        sentiment_label = "Neutral"

    # Determine specific emotion tags
    emotions = []
    if burnout_prob >= 40:
        emotions.append("Burned Out")
    if stress_prob >= 40:
        emotions.append("Stressed")
    if anxiety_prob >= 40:
        emotions.append("Anxious")
        
    if sentiment_score > 0.3:
        if "relaxed" in words or "calm" in words:
            emotions.append("Calm & Relaxed")
        else:
            emotions.append("Happy & Motivated")
    elif sentiment_score < -0.3 and not emotions:
        emotions.append("Overwhelmed")

    if not emotions:
        emotions.append("Neutral")

    return {
        "sentiment_score": sentiment_score,
        "sentiment_label": sentiment_label,
        "stress_probability": round(stress_prob, 1),
        "anxiety_probability": round(anxiety_prob, 1),
        "burnout_probability": round(burnout_prob, 1),
        "detected_emotions": emotions
    }