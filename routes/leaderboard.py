from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db


leaderboard_bp = Blueprint(
    "leaderboard",
    __name__,
    url_prefix="/api/leaderboard"
)


# ============================================================
# GET LEADERBOARD
# ============================================================

@leaderboard_bp.route("", methods=["GET"])
@jwt_required()
def get_leaderboard():

    current_user_id = int(get_jwt_identity())

    # Get all employees with their tracker points
    rows = db.session.execute(
        db.text("""
            SELECT
                u.id AS user_id,
                COALESCE(ep.full_name, 'Employee') AS employee_name,
                COALESCE(up.total_points, 0) AS total_points,
                COALESCE(us.current_streak, 0) AS current_streak
            FROM users u

            LEFT JOIN employee_profiles ep
                ON ep.user_id = u.id

            LEFT JOIN user_points up
                ON up.user_id = u.id

            LEFT JOIN user_streaks us
                ON us.user_id = u.id

            ORDER BY
                COALESCE(up.total_points, 0) DESC,
                u.id ASC
        """)
    ).mappings().all()

    leaderboard = []

    for index, row in enumerate(rows):

        user_id = row["user_id"]

        # Count completed tracker tasks
        completed_tasks = db.session.execute(
            db.text("""
                SELECT COUNT(*)
                FROM tracker_tasks
                WHERE user_id = :user_id
                AND status = 'Completed'
            """),
            {"user_id": user_id}
        ).scalar() or 0

        leaderboard.append({
            "rank": index + 1,
            "user_id": user_id,
            "employee_name": row["employee_name"],
            "points": row["total_points"],
            "streak": row["current_streak"],
            "tasks_completed": completed_tasks,
            "is_current_user": user_id == current_user_id
        })

    return jsonify({
        "status": "success",
        "leaderboard": leaderboard
    }), 200