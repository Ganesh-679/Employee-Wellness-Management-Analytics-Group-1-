import os
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
import numpy as np

from extensions import db
from models import HealthRecord, EmployeeProfile
from routes.risk import predict_risk_ml

recommendations_bp = Blueprint("recommendations", __name__, url_prefix="/api/recommendations")

@recommendations_bp.route("", methods=["GET"])
@jwt_required()
def get_recommendations():
    claims = get_jwt()
    if claims.get("role") != "user":
        return jsonify({"message": "Only employee accounts can retrieve wellness recommendations"}), 403

    user_id = int(get_jwt_identity())
    
    # 1. Fetch latest health record
    record = HealthRecord.query.filter_by(user_id=user_id).order_by(HealthRecord.updated_at.desc(), HealthRecord.record_date.desc()).first()
    if not record:
        return jsonify({
            "status": "no_data",
            "message": "No health data available. Please submit your first Health Data check-in to receive recommendations."
        }), 200

    # 2. Extract employee profile name for personalization
    profile = EmployeeProfile.query.filter_by(user_id=user_id).first()
    full_name = profile.full_name if profile and profile.full_name else "Employee"

    # 3. Fetch predicted risk score and level from ML model in routes/risk.py
    try:
        ml_score, ml_level = predict_risk_ml(record)
    except Exception as e:
        # Fallback to database values if ML model is currently compiling/training
        ml_score, ml_level = record.health_score, record.risk_level

    # 4. Extract metrics entered in the health data section
    height = record.height_cm
    weight = record.weight_kg
    bmi = record.bmi
    sleep = record.sleep_hours
    water = record.water_intake_liters if record.water_intake_liters is not None else 1.5
    bp_sys = record.bp_systolic
    bp_dia = record.bp_diastolic
    stress = record.stress_level if record.stress_level else "Low"
    exercise_mins = record.exercise_minutes_per_week

    # 5. Determine active conditions
    is_obese = bmi >= 30
    is_overweight = (bmi >= 25) and (bmi < 30)
    is_underweight = bmi < 18.5
    is_low_sleep = sleep < 7
    is_high_stress = stress == "High"
    is_med_stress = stress == "Medium"
    
    is_hypertensive = False
    if bp_sys is not None and bp_dia is not None:
        if bp_sys >= 130 or bp_dia >= 85:
            is_hypertensive = True
            
    is_sedentary = record.exercise_frequency == "Sedentary" or exercise_mins < 150

    # --- DYNAMIC PERSONALIZED RECOMMENDATIONS GENERATION ---
    recommendations = {}

    # Calculate target healthy weight range (BMI 18.5 to 24.9)
    height_m = height / 100.0
    healthy_min = round(18.5 * (height_m ** 2), 1)
    healthy_max = round(24.9 * (height_m ** 2), 1)

    # A. FITNESS RECOMMENDATION
    if is_obese or is_overweight:
        weight_deficit = round(weight - healthy_max, 1)
        recommendations["fitness"] = {
            "category": "fitness",
            "title": "Low-Impact Caloric Deficit Plan",
            "metric_summary": f"BMI: {bmi} ({record.bmi_category}). Current weight: {weight} kg.",
            "target": f"Target Healthy Weight: {healthy_min} - {healthy_max} kg (Aim to lose {weight_deficit} kg)",
            "description": f"Your current BMI of {bmi} is in the {record.bmi_category} range. To achieve your target weight range of {healthy_min}-{healthy_max} kg, we recommend starting a calorie deficit of 500 kcal/day alongside low-impact cardiovascular activity (brisk walking, swimming, cycling). This burns fat while protecting your joints from excess loading stress.",
            "duration": "30-40 mins, 4x a week",
            "impact": "Gradual fat loss (approx 0.5 kg/week) and significant reduction in joint stress and blood pressure.",
            "needs_improvement": True
        }
    elif is_underweight:
        weight_surplus = round(healthy_min - weight, 1)
        recommendations["fitness"] = {
            "category": "fitness",
            "title": "Hypertrophy & Strength Conditioning",
            "metric_summary": f"BMI: {bmi} ({record.bmi_category}). Current weight: {weight} kg.",
            "target": f"Target Healthy Weight: {healthy_min} - {healthy_max} kg (Aim to gain {weight_surplus} kg)",
            "description": f"Your current BMI of {bmi} is in the Underweight range. To reach a healthy weight safely, focus on lean muscle hypertrophy using resistance training (bodyweight, free weights, or bands) rather than high-intensity cardio which drains caloric reserves.",
            "duration": "30 mins, 3x a week",
            "impact": "Promotes skeletal muscle synthesis, builds bone mineral density, and increases strength.",
            "needs_improvement": True
        }
    elif is_sedentary:
        exercise_deficit = 150 - exercise_mins
        recommendations["fitness"] = {
            "category": "fitness",
            "title": "Cardiovascular Reconditioning Plan",
            "metric_summary": f"Weekly exercise: {exercise_mins} mins (Below target: 150 mins).",
            "target": f"Target: 150 mins/week (Deficit: {exercise_deficit} mins).",
            "description": f"You currently get {exercise_mins} minutes of exercise weekly. To resolve your deficit of {exercise_deficit} minutes and build baseline cardiovascular fitness, engage in moderate-intensity workouts like jogging or brisk walking. Try splitting this into 30-minute sessions across 5 days.",
            "duration": "30 mins, 5x a week",
            "impact": "Improves insulin sensitivity, increases VO2 max, and reverses markers of office sedentary behavior.",
            "needs_improvement": True
        }
    else:
        recommendations["fitness"] = {
            "category": "fitness",
            "title": "Advanced Strength & HIIT Conditioning",
            "metric_summary": f"BMI: {bmi} (Normal). Weekly exercise: {exercise_mins} mins.",
            "target": "Maintenance & High-Performance Conditioning",
            "description": "Your physical metrics are in the ideal range! To maintain this condition and build muscle density, perform core strength training mixed with High-Intensity Interval Training (HIIT) to boost physical performance and metabolic flexibility.",
            "duration": "40 mins, 3x a week",
            "impact": "Optimizes cardiovascular output, muscular tone, and bone density.",
            "needs_improvement": False
        }

    # B. DIET RECOMMENDATION
    if is_hypertensive:
        bp_classification = "Hypertension Range" if (bp_sys >= 140 or bp_dia >= 90) else "Pre-Hypertension Range"
        recommendations["diet"] = {
            "category": "diet",
            "title": "Cardiovascular Support DASH Diet",
            "metric_summary": f"Blood Pressure: {bp_sys}/{bp_dia} mmHg ({bp_classification}).",
            "target": "Target Sodium: <1,500 mg/day. BP Target: <120/80 mmHg",
            "description": f"Your blood pressure is elevated ({bp_sys}/{bp_dia} mmHg). Implement a DASH (Dietary Approaches to Stop Hypertension) protocol. Focus on rich mineral sources (potassium, magnesium, calcium) from bananas, sweet potatoes, and green leafy vegetables while keeping processed salt to a minimum.",
            "duration": "Daily meals",
            "impact": "Aids vasodilation, naturally lowering systolic pressure by up to 8-11 mmHg in 2-3 weeks.",
            "needs_improvement": True
        }
    elif is_obese or is_overweight:
        protein_target = int(weight * 1.2)
        calorie_target = int((weight * 22) - 500)
        recommendations["diet"] = {
            "category": "diet",
            "title": "Satiety-Focused Caloric Control",
            "metric_summary": f"Weight: {weight} kg. High BMI intake correction.",
            "target": f"Target: ~{calorie_target} kcal/day & {protein_target}g Protein/day",
            "description": f"To support fat loss without constant hunger, prioritize a protein intake of {protein_target}g daily to retain muscle mass, combined with high-fiber whole vegetables (chia seeds, broccoli, beans). Keep daily energy intake close to {calorie_target} kcal.",
            "duration": "Ongoing",
            "impact": "Stabilizes insulin and ghrelin (hunger hormone) levels, making caloric deficits sustainable.",
            "needs_improvement": True
        }
    elif is_underweight:
        protein_target = int(weight * 1.5)
        calorie_target = int((weight * 33) + 400)
        recommendations["diet"] = {
            "category": "diet",
            "title": "Caloric Surplus & Protein-Rich Nutrition",
            "metric_summary": f"Weight: {weight} kg. Underweight intake correction.",
            "target": f"Target: ~{calorie_target} kcal/day & {protein_target}g Protein/day",
            "description": f"To safely gain weight and support muscle recovery, eat a nutrient-dense diet rich in proteins ({protein_target}g daily) and healthy fats. Focus on whole grains, avocados, eggs, nuts, poultry, or plant protein shakes to reach your surplus goal of ~{calorie_target} kcal daily.",
            "duration": "Daily meals",
            "impact": "Provides the structural building blocks and energy surplus required for healthy tissue growth.",
            "needs_improvement": True
        }
    else:
        recommendations["diet"] = {
            "category": "diet",
            "title": "Anti-Inflammatory Whole Foods Plan",
            "metric_summary": "Healthy weight and normal metabolic metrics.",
            "target": "Nutrient Density & Longevity Optimization",
            "description": "Maintain your health status with the Mediterranean whole foods model. Focus on healthy monounsaturated fats (extra virgin olive oil, nuts, avocados), omega-3 fatty acids (salmon, walnuts) and colorful fruits.",
            "duration": "Daily meals",
            "impact": "Reduces systemic oxidative stress, supports cognitive longevity, and maintains energy.",
            "needs_improvement": False
        }

    # C. HYDRATION RECOMMENDATION
    if water < 3.0:
        water_deficit = round(3.0 - water, 1)
        recommendations["lifestyle"] = {
            "category": "lifestyle",
            "title": "Dehydration Reversal Protocol",
            "metric_summary": f"Daily Water: {water}L (Below target: 3.0L).",
            "target": f"Target Daily Intake: 3.0 Liters (Deficit: {water_deficit}L).",
            "description": f"You are currently drinking {water}L, which is {water_deficit}L short of optimal hydration. Place a 1-liter flask at your desk with strict milestones: finish flask 1 by 11:30 AM, flask 2 by 3:00 PM, and flask 3 by 7:30 PM.",
            "duration": "Daily intervals",
            "impact": "Prevents cognitive fatigue, improves skin elasticity, and supports renal filtration.",
            "needs_improvement": True
        }
    else:
        recommendations["lifestyle"] = {
            "category": "lifestyle",
            "title": "Hydration Balance & Electrolyte Maintenance",
            "metric_summary": f"Daily Water: {water}L (Optimal).",
            "target": "Maintain 3.0 Liters daily volume",
            "description": "Excellent job! You are well-hydrated. Keep up this intake. If your physical activity increases or you spend time in hot conditions, increase intake by 500ml for every 30 minutes of heavy sweating.",
            "duration": "Daily habit",
            "impact": "Maintains physical cellular volume, body temperature regulation, and high digestion efficiency.",
            "needs_improvement": False
        }

    # D. MENTAL HEALTH & STRESS RECOMMENDATION
    if is_high_stress:
        recommendations["mental_health"] = {
            "category": "mental_health",
            "title": "Active Cortisol Reduction Protocol",
            "metric_summary": "Self-reported stress: High.",
            "target": "Calm Autonomic System & Cortisol Drainage",
            "description": "High stress activates the sympathetic (fight-or-flight) nervous system, triggering cortisol release. Implement twice-daily 4-7-8 breathing blocks (inhale 4s, hold 7s, exhale 8s) and spend 10 minutes writing a gratitude journal before sleep.",
            "duration": "15 mins twice daily",
            "impact": "Lowers acute heart rate, increases heart rate variability (HRV), and improves mental clarity.",
            "needs_improvement": True
        }
    elif is_med_stress:
        recommendations["mental_health"] = {
            "category": "mental_health",
            "title": "Mindfulness & Screen Boundaries",
            "metric_summary": "Self-reported stress: Medium.",
            "target": "Stress Prevention & Boundary Integration",
            "description": "You reported moderate stress levels. Establish cognitive boundaries by silencing work notifications outside work hours. Schedule short 5-minute walks during the day without checking your phone.",
            "duration": "Daily intervals",
            "impact": "Allows neural reset, preventing workplace stress from turning into chronic burnout.",
            "needs_improvement": True
        }
    else:
        recommendations["mental_health"] = {
            "category": "mental_health",
            "title": "Cognitive Focus & Flow Practice",
            "metric_summary": "Self-reported stress: Low.",
            "target": "Optimal Cognitive Efficiency & Focus",
            "description": "Your stress level is low. Optimize your cognitive productivity by working in 90-minute blocks (Pomodoro style) followed by 10 minutes of complete mental rests (no devices) to build baseline resilience.",
            "duration": "Daily workspace structure",
            "impact": "Deepens focus states, enhances problem-solving skills, and maintains emotional stability.",
            "needs_improvement": False
        }

    # E. SLEEP HYGIENE RECOMMENDATION
    if is_low_sleep:
        sleep_deficit = round(8.0 - sleep, 1)
        recommendations["yoga"] = {
            "category": "yoga",
            "title": "Somatic Relaxation & Sleep Debt Recovery",
            "metric_summary": f"Daily Sleep: {sleep} hours (Below target: 8.0 hours).",
            "target": f"Target Sleep: 8.0 hours (Deficit: {sleep_deficit} hours).",
            "description": f"You sleep {sleep} hours nightly, creating a sleep debt of {sleep_deficit} hours. To recover, perform 10 minutes of Progressive Muscle Relaxation (PMR) in bed. Ensure your bedroom is completely dark and cool. Stop reading digital screens 90 minutes before bed.",
            "duration": "Nightly routine",
            "impact": "Accelerates deep non-REM sleep onset, promoting biological recovery and cognitive repair.",
            "needs_improvement": True
        }
    else:
        recommendations["yoga"] = {
            "category": "yoga",
            "title": "Melatonin Production & Circadian Alignment",
            "metric_summary": f"Daily Sleep: {sleep} hours (Optimal).",
            "target": "Maintain 7.5 - 8.5 hours range",
            "description": "Your sleep duration is in the healthy zone. To protect this, maintain a consistent wake-up time even on weekends. Expose your eyes to direct outdoor sunlight for 10 minutes within an hour of waking to lock in your circadian phase.",
            "duration": "Daily habits",
            "impact": "Strengthens circadian amplitude, ensuring high morning alertness and rapid nighttime sleepiness.",
            "needs_improvement": False
        }

    # 6. Generate the hourly schedule
    schedule_steps = []
    morning_time = "07:30 AM"
    noon_time = "12:30 PM"
    afternoon_time = "03:30 PM"
    evening_time = "07:00 PM"
    night_time = "09:30 PM"

    # Morning
    if is_low_sleep:
        schedule_steps.append({
            "time": morning_time,
            "activity": "Circadian Morning Sunlight Exposure",
            "notes": "Get 10 minutes of direct sunlight. Inhibits melatonin production immediately, boosting daytime alertness."
        })
    else:
        schedule_steps.append({
            "time": morning_time,
            "activity": "Surya Namaskar (Sun Salutations)",
            "notes": "Perform 4 cycles of Sun Salutations to warm up your muscles and coordinate breathing."
        })

    # Midday
    if is_sedentary:
        schedule_steps.append({
            "time": noon_time,
            "activity": "Ergonomic Walk & Stretch snack",
            "notes": "Walk for 10 minutes after lunch. Reverses blood pooling in the legs and prevents postural fatigue."
        })
    else:
        schedule_steps.append({
            "time": noon_time,
            "activity": "Hydration Integration check",
            "notes": "Ensure your first 1-liter bottle is fully completed by now to prevent mid-day cognitive decline."
        })

    # Afternoon
    if is_high_stress:
        schedule_steps.append({
            "time": afternoon_time,
            "activity": "4-7-8 Deep Breathing Reset",
            "notes": "Perform 4 cycles of paced breathing. Direct vagal stimulation to reduce work tension."
        })
    elif water < 3.0:
        schedule_steps.append({
            "time": afternoon_time,
            "activity": "Hydration Refill Milestone",
            "notes": "Finish your second 1-liter water bottle to clear active dehydration indicators."
        })
    else:
        schedule_steps.append({
            "time": afternoon_time,
            "activity": "Ergonomic Mobilization Break",
            "notes": "Stand up and do chest and hip flexor stretches to combat seated desk compression."
        })

    # Evening
    if is_obese or is_overweight or is_hypertensive:
        schedule_steps.append({
            "time": evening_time,
            "activity": "DASH-Inspired Calorie-Controlled Dinner",
            "notes": "A low-sodium, high-protein meal. Highly restricts processed salt to help lower blood pressure."
        })
    else:
        schedule_steps.append({
            "time": evening_time,
            "activity": "Anti-Inflammatory Whole Foods Dinner",
            "notes": "Eat a dinner featuring healthy fats (olive oil, avocados) and colorful vegetables."
        })

    # Night
    if is_low_sleep or is_high_stress:
        schedule_steps.append({
            "time": night_time,
            "activity": "Digital Curfew & Somatic PMR",
            "notes": "Turn off screens. Spend 10 minutes performing Progressive Muscle Relaxation (PMR) in bed."
        })
    else:
        schedule_steps.append({
            "time": night_time,
            "activity": "Circadian Wind-Down Routine",
            "notes": "Dim home lighting and engage in low-stimulation activity (reading a physical book) to prompt sleepiness."
        })

    # 7. Synthesize a Personalized Summary (HTML tags instead of Markdown **)
    trigger_names = []
    if is_obese: trigger_names.append("Obese BMI classification")
    elif is_overweight: trigger_names.append("Overweight BMI classification")
    elif is_underweight: trigger_names.append("Underweight BMI classification")
    if is_low_sleep: trigger_names.append("Sleep Deprivation (under 7 hours)")
    if is_high_stress: trigger_names.append("High Psychological Stress")
    elif is_med_stress: trigger_names.append("Moderate Stress Indicators")
    if is_hypertensive: trigger_names.append("Pre-Hypertension/Hypertension blood pressure readings")
    if is_sedentary: trigger_names.append("Sedentary Workplace Habits")
    if water < 3.0: trigger_names.append("Inadequate daily hydration")

    # Combine into a highly custom text using HTML bold tags
    if not trigger_names:
        summary_intro = f"Hello {full_name}! Based on your latest check-in, your health metrics are outstanding. The machine learning model predicts a <strong>{ml_level} Wellness Risk</strong> (Risk Score: <strong>{ml_score}%</strong>). To maintain your status, our content-based system has compiled a wellness maintenance plan focusing on core strength, hydration, and circadian alignment."
    else:
        triggers_str = ", ".join(trigger_names)
        intensity_text = "focused clinical intervention" if ml_level == "High" else "active habit correction" if ml_level == "Medium" else "general wellness optimization"
        summary_intro = f"Hello {full_name}! Based on your latest check-in, the machine learning model predicts a <strong>{ml_level} Wellness Risk</strong> (Risk Score: <strong>{ml_score}%</strong>). Our algorithm detected active concerns: <strong>{triggers_str}</strong>. To address these issues, we have generated an <strong>{intensity_text} plan</strong> tailored specifically to your metrics."

    return jsonify({
        "status": "success",
        "full_name": full_name,
        "record_date": record.record_date.isoformat(),
        "risk_level": ml_level,
        "risk_score": ml_score,
        "stats": {
            "bmi": bmi,
            "category": record.bmi_category,
            "sleep": sleep,
            "water": water,
            "bp": f"{bp_sys}/{bp_dia}" if (bp_sys and bp_dia) else "Not Provided",
            "stress": stress,
            "exercise": exercise_mins
        },
        "summary": summary_intro,
        "recommendations": recommendations,
        "schedule": schedule_steps
    }), 200
