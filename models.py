import json
from datetime import datetime
from extensions import db


class User(db.Model):
    """An employee account. Matches the frontend's 'user' role."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Admin(db.Model):
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PasswordResetToken(db.Model):
    """One row per requested OTP. `identifier` is an email (role='user')
    or an adminId (role='admin')."""
    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String(120), nullable=False, index=True)
    role = db.Column(db.String(10), nullable=False)  # "user" or "admin"
    otp_code = db.Column(db.String(10), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class EmployeeProfile(db.Model):
    """Personal information an employee fills in about their role at the
    company (not their health data). One-to-one with User."""
    __tablename__ = "employee_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False, index=True)

    full_name = db.Column(db.String(120), nullable=True)
    employee_code = db.Column(db.String(40), nullable=True)  # company employee ID, if they have one
    designation = db.Column(db.String(80), nullable=True)    # e.g. "Software Engineer"
    department = db.Column(db.String(80), nullable=True)     # e.g. "Engineering", "HR"
    date_of_joining = db.Column(db.Date, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    work_location = db.Column(db.String(80), nullable=True)  # e.g. "Bengaluru", "Remote"
    profile_picture = db.Column(db.String(255), nullable=True)  # filename of uploaded avatar

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "fullName": self.full_name,
            "employeeCode": self.employee_code,
            "designation": self.designation,
            "department": self.department,
            "dateOfJoining": self.date_of_joining.isoformat() if self.date_of_joining else None,
            "phone": self.phone,
            "workLocation": self.work_location,
            "profilePicture": self.profile_picture,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class HealthRecord(db.Model):
    """Module 1: Employee Health Data Management.

    One row = one employee's wellness check-in / data snapshot. An
    employee can have many records over time (e.g. one per month), so
    trends can later feed the analytics modules.
    """
    __tablename__ = "health_records"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    record_date = db.Column(db.Date, nullable=False)  # date this snapshot is for

    # --- BMI inputs / derived values ---
    height_cm = db.Column(db.Float, nullable=False)
    weight_kg = db.Column(db.Float, nullable=False)
    bmi = db.Column(db.Float, nullable=False)              # server-computed, never trust client
    bmi_category = db.Column(db.String(20), nullable=False)  # Underweight/Normal/Overweight/Obese

    # --- Exercise habits ---
    exercise_frequency = db.Column(db.String(20), nullable=False)  # Sedentary/Light/Moderate/Active
    exercise_minutes_per_week = db.Column(db.Integer, nullable=False, default=0)

    # --- Sleep patterns ---
    sleep_hours = db.Column(db.Float, nullable=False)  # average hours/night

    # --- Vitals / lifestyle signals (feed Module 2: Wellness Risk Prediction) ---
    water_intake_liters = db.Column(db.Float, nullable=True)      # liters/day
    bp_systolic = db.Column(db.Integer, nullable=True)            # mmHg
    bp_diastolic = db.Column(db.Integer, nullable=True)           # mmHg
    resting_heart_rate = db.Column(db.Integer, nullable=True)     # bpm
    stress_level = db.Column(db.String(10), nullable=True)        # Low/Medium/High
    smoking_status = db.Column(db.String(10), nullable=True)      # Never/Former/Current
    alcohol_consumption = db.Column(db.String(15), nullable=True)  # None/Occasional/Regular

    # --- Attendance ---
    attendance_status = db.Column(db.String(20), nullable=False)  # Present/Absent/Leave/WFH

    # --- Medical check-up report (structured fields only, per scope) ---
    checkup_date = db.Column(db.Date, nullable=True)
    checkup_result = db.Column(db.String(20), nullable=True)  # Normal/NeedsAttention/Critical
    checkup_notes = db.Column(db.Text, nullable=True)

    # --- Health self-assessment ---
    assessment_notes = db.Column(db.Text, nullable=True)

    # --- AI-based (rule-based) data validation outcome ---
    validation_status = db.Column(db.String(10), nullable=False, default="valid")  # valid/flagged
    validation_flags = db.Column(db.Text, nullable=True)  # JSON-encoded list of warning strings
    health_score = db.Column(db.Integer, nullable=False, default=100)
    risk_level = db.Column(db.String(20), nullable=False, default="Low")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "recordDate": self.record_date.isoformat() if self.record_date else None,
            "heightCm": self.height_cm,
            "weightKg": self.weight_kg,
            "bmi": self.bmi,
            "bmiCategory": self.bmi_category,
            "exerciseFrequency": self.exercise_frequency,
            "exerciseMinutesPerWeek": self.exercise_minutes_per_week,
            "sleepHours": self.sleep_hours,
            "waterIntakeLiters": self.water_intake_liters,
            "bpSystolic": self.bp_systolic,
            "bpDiastolic": self.bp_diastolic,
            "restingHeartRate": self.resting_heart_rate,
            "stressLevel": self.stress_level,
            "smokingStatus": self.smoking_status,
            "alcoholConsumption": self.alcohol_consumption,
            "attendanceStatus": self.attendance_status,
            "checkupDate": self.checkup_date.isoformat() if self.checkup_date else None,
            "checkupResult": self.checkup_result,
            "checkupNotes": self.checkup_notes,
            "assessmentNotes": self.assessment_notes,
            "validationStatus": self.validation_status,
            "validationFlags": json.loads(self.validation_flags) if self.validation_flags else [],
            "healthScore": self.health_score,
            "riskLevel": self.risk_level,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }
class MedicalReport(db.Model):
    __tablename__ = "medical_reports"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    report_name = db.Column(db.String(150), nullable=False)

    report_type = db.Column(db.String(50), nullable=False)

    file_name = db.Column(db.String(255), nullable=False)

    file_path = db.Column(db.String(300), nullable=False)

    uploaded_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    def to_dict(self):
        return {
            "id": self.id,
            "reportName": self.report_name,
            "reportType": self.report_type,
            "fileName": self.file_name,
            "filePath": self.file_path,
            "uploadedAt": self.uploaded_at.isoformat()
        }


class SentimentLog(db.Model):
    """Module 4: Mental Health & Sentiment Analytics.
    Stores daily journals, reflections, or feedback logs for NLP analysis.
    """
    __tablename__ = "sentiment_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    text_content = db.Column(db.Text, nullable=False)
    sentiment_score = db.Column(db.Float, nullable=False)        # -1.0 to 1.0
    sentiment_label = db.Column(db.String(20), nullable=False)    # Positive/Neutral/Negative
    stress_probability = db.Column(db.Float, nullable=False)      # 0 to 100
    anxiety_probability = db.Column(db.Float, nullable=False)     # 0 to 100
    burnout_probability = db.Column(db.Float, nullable=False)     # 0 to 100
    detected_emotions = db.Column(db.Text, nullable=False)        # JSON-serialized list

    logged_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "textContent": self.text_content,
            "sentimentScore": self.sentiment_score,
            "sentimentLabel": self.sentiment_label,
            "stressProbability": self.stress_probability,
            "anxietyProbability": self.anxiety_probability,
            "burnoutProbability": self.burnout_probability,
            "detectedEmotions": json.loads(self.detected_emotions) if (self.detected_emotions and isinstance(self.detected_emotions, str) and self.detected_emotions.startswith("[")) else (self.detected_emotions or []),
            "loggedAt": self.logged_at.isoformat() if self.logged_at else None
        }


class ChatMessage(db.Model):
    """Module 6: AI Wellness Chatbot conversation log."""
    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    sender = db.Column(db.String(10), nullable=False)  # 'user' or 'bot'
    text = db.Column(db.Text, nullable=False)
    intent = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "sender": self.sender,
            "text": self.text,
            "intent": self.intent,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


class WellnessReminder(db.Model):
    """Module 6: Automated wellness reminders (hydration, stretch breaks, sleep alarms)."""
    __tablename__ = "wellness_reminders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(100), nullable=False)
    reminder_type = db.Column(db.String(50), nullable=False, default="hydration")
    time_str = db.Column(db.String(50), nullable=False, default="Every 2 hours")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "reminderType": self.reminder_type,
            "timeStr": self.time_str,
            "isActive": self.is_active,
            "createdAt": self.created_at.isoformat() if self.created_at else None
        }


class HealthCheckupSchedule(db.Model):
    """Module 6: Scheduled employee health checkups."""
    __tablename__ = "health_checkup_schedules"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    checkup_type = db.Column(db.String(100), nullable=False)
    scheduled_date = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Scheduled")  # Scheduled, Completed, Cancelled
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "checkupType": self.checkup_type,
            "scheduledDate": self.scheduled_date,
            "status": self.status,
            "notes": self.notes,
            "createdAt": self.created_at.isoformat() if self.created_at else None
        }