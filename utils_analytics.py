from datetime import datetime, timedelta
from collections import defaultdict
from extensions import db
from models import User, HealthRecord, SentimentLog, EmployeeProfile


def _linear_forecast(values, steps=3):
    """Simple least-squares trend forecast without introducing a new dependency."""
    if len(values) < 2:
        return []
    n = len(values)
    x = list(range(n))
    x_mean = sum(x) / n
    y_mean = sum(values) / n
    denom = sum((xi - x_mean) ** 2 for xi in x)
    if denom == 0:
        slope = 0.0
    else:
        slope = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, values)) / denom
    intercept = y_mean - slope * x_mean
    return [intercept + slope * (n + i) for i in range(steps)]


def _month_start(value):
    return value.replace(day=1)


def _add_months(value, count):
    month = value.month - 1 + count
    year = value.year + month // 12
    month = month % 12 + 1
    return value.replace(year=year, month=month, day=1)


def _month_label(value, forecast=False):
    suffix = " (fcst)" if forecast else ""
    return value.strftime("%b %Y") + suffix


def calculate_wellness_kpis():
    """Calculate Module 5 KPIs strictly from the application's real records."""
    total_users = User.query.count()
    thirty_days_ago = datetime.utcnow().date() - timedelta(days=30)
    now_dt = datetime.utcnow()

    active_user_ids = set()
    active_user_ids.update(
        row[0] for row in db.session.query(HealthRecord.user_id)
        .filter(HealthRecord.record_date >= thirty_days_ago).all()
    )
    active_user_ids.update(
        row[0] for row in db.session.query(SentimentLog.user_id)
        .filter(SentimentLog.logged_at >= now_dt - timedelta(days=30)).all()
    )
    participation_rate = round((len(active_user_ids) / total_users) * 100, 1) if total_users else 0.0

    total_records = HealthRecord.query.count()
    absent_records = HealthRecord.query.filter(
        HealthRecord.attendance_status.in_(["Absent", "Leave"])
    ).count() if total_records else 0
    absenteeism_rate = round((absent_records / total_records) * 100, 1) if total_records else 0.0

    health_records = HealthRecord.query.all()
    sentiment_records = SentimentLog.query.all()

    if health_records:
        avg_health_score = sum(r.health_score or 0 for r in health_records) / len(health_records)
        avg_sleep = sum(r.sleep_hours or 0 for r in health_records) / len(health_records)
        # Health score is already the application's normalized wellness score;
        # attendance is applied as a transparent productivity adjustment.
        productivity_index = avg_health_score * (1.0 - absenteeism_rate / 100.0)
        productivity_index = round(max(0.0, min(100.0, productivity_index)), 1)
    else:
        avg_sleep = 0.0
        productivity_index = 0.0

    sixty_days_ago = datetime.utcnow().date() - timedelta(days=60)
    prev_month_records = [r for r in health_records if sixty_days_ago <= r.record_date < thirty_days_ago]
    curr_month_records = [r for r in health_records if r.record_date >= thirty_days_ago]

    if prev_month_records and curr_month_records:
        prev_avg = sum(r.health_score or 0 for r in prev_month_records) / len(prev_month_records)
        curr_avg = sum(r.health_score or 0 for r in curr_month_records) / len(curr_month_records)
        program_effectiveness = round(((curr_avg - prev_avg) / prev_avg) * 100, 1) if prev_avg else 0.0
    else:
        program_effectiveness = 0.0

    return {
        "participationRate": participation_rate,
        "absenteeismRate": absenteeism_rate,
        "productivityIndex": productivity_index,
        "programEffectiveness": program_effectiveness,
        "activeUsers": len(active_user_ids),
        "totalEmployees": total_users,
        "dataAvailability": {
            "healthRecords": len(health_records),
            "sentimentRecords": len(sentiment_records),
            "historicalComparisonAvailable": bool(prev_month_records and curr_month_records)
        }
    }


def generate_predictive_analytics():
    """Generate Module 5 analytics from actual health/sentiment records only."""
    health_records = HealthRecord.query.order_by(HealthRecord.record_date.asc()).all()

    # ---- Organization monthly history ----
    monthly = defaultdict(lambda: {"total": 0, "absent": 0, "health": []})
    for record in health_records:
        month = _month_start(record.record_date)
        monthly[month]["total"] += 1
        if (record.attendance_status or "").strip().lower() in {"absent", "leave"}:
            monthly[month]["absent"] += 1
        if record.health_score is not None:
            monthly[month]["health"].append(float(record.health_score))

    actual_months = sorted(monthly.keys())[-12:]
    months = [_month_label(m) for m in actual_months]
    absenteeism_trend = []
    productivity_trend = []
    for month in actual_months:
        item = monthly[month]
        absenteeism_trend.append(round((item["absent"] / item["total"]) * 100, 1) if item["total"] else 0.0)
        productivity_trend.append(round(sum(item["health"]) / len(item["health"]), 1) if item["health"] else 0.0)

    forecast_available = len(actual_months) >= 2
    if forecast_available:
        abs_forecast = [max(0.0, min(100.0, round(v, 1))) for v in _linear_forecast(absenteeism_trend, 3)]
        prod_forecast = [max(0.0, min(100.0, round(v, 1))) for v in _linear_forecast(productivity_trend, 3)]
        last_month = actual_months[-1]
        for offset, (abs_v, prod_v) in enumerate(zip(abs_forecast, prod_forecast), start=1):
            months.append(_month_label(_add_months(last_month, offset), forecast=True))
            absenteeism_trend.append(abs_v)
            productivity_trend.append(prod_v)

    # ---- Department risk forecasts ----
    department_records = defaultdict(list)
    for record in health_records:
        profile = EmployeeProfile.query.filter_by(user_id=record.user_id).first()
        department = (profile.department if profile and profile.department else "General").strip() or "General"
        department_records[department].append(record)

    sentiment_by_user = defaultdict(list)
    for log in SentimentLog.query.all():
        sentiment_by_user[log.user_id].append(log)

    dept_forecasts = []
    for department in sorted(department_records):
        records = department_records[department]
        avg_health = sum(r.health_score or 0 for r in records) / len(records)
        current_risk = round(max(0.0, min(100.0, 100.0 - avg_health)), 1)

        # Project the department risk only when at least two monthly observations exist.
        dept_monthly = defaultdict(list)
        for record in records:
            dept_monthly[_month_start(record.record_date)].append(100.0 - (record.health_score or 0))
        dept_months = sorted(dept_monthly)
        dept_month_values = [sum(dept_monthly[m]) / len(dept_monthly[m]) for m in dept_months]
        if len(dept_month_values) >= 2:
            predicted_risk = round(max(0.0, min(100.0, _linear_forecast(dept_month_values, 1)[0])), 1)
            confidence = "Trend-based"
        else:
            predicted_risk = current_risk
            confidence = "Low data"

        dept_user_ids = {r.user_id for r in records}
        all_dept_users = EmployeeProfile.query.filter(
            EmployeeProfile.department == department
        ).all()
        total_dept_users = len(all_dept_users)
        active_cutoff = datetime.utcnow().date() - timedelta(days=30)
        active_dept_users = {
            r.user_id for r in records if r.record_date >= active_cutoff
        }
        active_dept_users.update(
            log.user_id for uid in dept_user_ids
            for log in sentiment_by_user.get(uid, [])
            if log.logged_at and log.logged_at >= datetime.utcnow() - timedelta(days=30)
        )
        participation = round((len(active_dept_users) / total_dept_users) * 100, 1) if total_dept_users else 0.0

        dept_sentiments = [log for uid in dept_user_ids for log in sentiment_by_user.get(uid, [])]
        if dept_sentiments:
            avg_burnout = sum(log.burnout_probability or 0 for log in dept_sentiments) / len(dept_sentiments)
            if avg_burnout >= 50:
                alert_level = "High"
            elif avg_burnout >= 30:
                alert_level = "Medium"
            else:
                alert_level = "Low"
            action = (
                "Urgent: Review workload and arrange a wellness check-in" if alert_level == "High"
                else "Advisory: Encourage wellness participation and review workload" if alert_level == "Medium"
                else "Stable: Continue wellness participation"
            )
        else:
            avg_burnout = None
            alert_level = "No Data"
            action = "No sentiment check-ins yet; collect mental-health data before assessing burnout."

        if confidence == "Low data":
            action = "Limited history: collect data across another month before relying on the risk forecast." if alert_level == "No Data" else action + " (forecast confidence: low)"

        dept_forecasts.append({
            "department": department,
            "currentRiskScore": current_risk,
            "predictedRiskScore": predicted_risk,
            "burnoutAlertLevel": alert_level,
            "participationRate": participation,
            "predictionConfidence": confidence,
            "averageBurnout": round(avg_burnout, 1) if avg_burnout is not None else None,
            "records": len(records)
        })

    return {
        "months": months,
        "absenteeismTrend": absenteeism_trend,
        "productivityTrend": productivity_trend,
        "departmentForecasts": dept_forecasts,
        "forecastAvailable": forecast_available,
        "forecastMessage": (
            "Forecasts are trend-based because at least two months of historical health data are available."
            if forecast_available else
            "Forecast unavailable yet: add health records across at least two different months to calculate a reliable trend."
        )
    }
