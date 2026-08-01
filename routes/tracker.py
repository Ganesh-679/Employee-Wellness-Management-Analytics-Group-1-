from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from extensions import db


tracker_bp = Blueprint(
    "tracker",
    __name__,
    url_prefix="/api/tracker"
)


# ============================================================
# COMPLETE A DAILY TRACKER TASK
# ============================================================

@tracker_bp.route("/complete", methods=["POST"])
@jwt_required()
def complete_task():

    claims = get_jwt()

    if claims.get("role") != "user":
        return jsonify({
            "message": "Only employee accounts can complete wellness tasks"
        }), 403

    user_id = int(get_jwt_identity())

    data = request.get_json() or {}

    task_name = data.get("task_name")
    category = data.get("category")

    if not task_name:
        return jsonify({
            "message": "task_name is required"
        }), 400

    # --------------------------------------------------------
    # Check whether this task was already completed today
    # --------------------------------------------------------

    existing_task = db.session.execute(
        db.text("""
            SELECT id
            FROM tracker_tasks
            WHERE user_id = :user_id
              AND task_name = :task_name
              AND created_date = DATE('now', 'localtime')
              AND status = 'Completed'
        """),
        {
            "user_id": user_id,
            "task_name": task_name
        }
    ).fetchone()

    if existing_task:
        return jsonify({
            "status": "already_completed",
            "message": "Task already completed today",
            "points_earned": 0
        }), 200

    # --------------------------------------------------------
    # Save completed task
    # --------------------------------------------------------

    db.session.execute(
        db.text("""
            INSERT INTO tracker_tasks
            (
                user_id,
                task_name,
                task_category,
                status,
                created_date,
                completed_at
            )
            VALUES
            (
                :user_id,
                :task_name,
                :category,
                'Completed',
                DATE('now', 'localtime'),
                CURRENT_TIMESTAMP
            )
        """),
        {
            "user_id": user_id,
            "task_name": task_name,
            "category": category or "wellness"
        }
    )

    # --------------------------------------------------------
    # Ensure user_points row exists
    # --------------------------------------------------------

    existing_points = db.session.execute(
        db.text("""
            SELECT id
            FROM user_points
            WHERE user_id = :user_id
        """),
        {"user_id": user_id}
    ).fetchone()

    if existing_points is None:

        db.session.execute(
            db.text("""
                INSERT INTO user_points
                (
                    user_id,
                    total_points,
                    current_level,
                    experience
                )
                VALUES
                (
                    :user_id,
                    0,
                    'Beginner',
                    0
                )
            """),
            {"user_id": user_id}
        )

    # --------------------------------------------------------
    # Give 10 points
    # --------------------------------------------------------

    db.session.execute(
        db.text("""
            UPDATE user_points
            SET
                total_points = total_points + 10,
                experience = experience + 10,
                last_updated = CURRENT_TIMESTAMP
            WHERE user_id = :user_id
        """),
        {"user_id": user_id}
    )

    # --------------------------------------------------------
    # Update streak
    # --------------------------------------------------------

    streak_exists = db.session.execute(
        db.text("""
            SELECT id
            FROM user_streaks
            WHERE user_id = :user_id
        """),
        {"user_id": user_id}
    ).fetchone()

    if streak_exists is None:

        db.session.execute(
            db.text("""
                INSERT INTO user_streaks
                (
                    user_id,
                    current_streak,
                    best_streak,
                    last_completed_date
                )
                VALUES
                (
                    :user_id,
                    1,
                    1,
                    DATE('now', 'localtime')
                )
            """),
            {"user_id": user_id}
        )

    else:

        last_date = db.session.execute(
            db.text("""
                SELECT last_completed_date
                FROM user_streaks
                WHERE user_id = :user_id
            """),
            {"user_id": user_id}
        ).scalar()

        # Only update streak if this is the first completed task today
        if str(last_date) != str(
            db.session.execute(
                db.text("SELECT DATE('now', 'localtime')")
            ).scalar()
        ):

            db.session.execute(
                db.text("""
                    UPDATE user_streaks
                    SET
                        current_streak = current_streak + 1,
                        best_streak =
                            MAX(best_streak, current_streak + 1),
                        last_completed_date =
                            DATE('now', 'localtime')
                    WHERE user_id = :user_id
                """),
                {"user_id": user_id}
            )

    db.session.commit()
    

    # --------------------------------------------------------
    # Get updated values
    # --------------------------------------------------------

    points = db.session.execute(
        db.text("""
            SELECT total_points
            FROM user_points
            WHERE user_id = :user_id
        """),
        {"user_id": user_id}
    ).scalar() or 0

    streak = db.session.execute(
        db.text("""
            SELECT current_streak
            FROM user_streaks
            WHERE user_id = :user_id
        """),
        {"user_id": user_id}
    ).scalar() or 0

    completed_tasks = db.session.execute(
        db.text("""
            SELECT COUNT(*)
            FROM tracker_tasks
            WHERE user_id = :user_id
              AND status = 'Completed'
              AND created_date = DATE('now', 'localtime')
        """),
        {"user_id": user_id}
    ).scalar() or 0

    return jsonify({
        "status": "success",
        "message": f"{task_name} completed successfully",
        "task_name": task_name,
        "category": category,
        "points_earned": 10,
        "total_points": points,
        "streak": streak,
        "completed_tasks": completed_tasks
    }), 200


# ============================================================
# TRACKER SUMMARY
# ============================================================

@tracker_bp.route("/summary", methods=["GET"])
@jwt_required()
def tracker_summary():

    user_id = int(get_jwt_identity())

    points = db.session.execute(
        db.text("""
            SELECT total_points
            FROM user_points
            WHERE user_id = :user_id
        """),
        {"user_id": user_id}
    ).scalar() or 0

    streak = db.session.execute(
        db.text("""
            SELECT current_streak
            FROM user_streaks
            WHERE user_id = :user_id
        """),
        {"user_id": user_id}
    ).scalar() or 0

    completed_tasks = db.session.execute(
        db.text("""
            SELECT COUNT(*)
            FROM tracker_tasks
            WHERE user_id = :user_id
              AND status = 'Completed'
              AND created_date = DATE('now', 'localtime')
        """),
        {"user_id": user_id}
    ).scalar() or 0

    completed_names = db.session.execute(
        db.text("""
            SELECT task_name
            FROM tracker_tasks
            WHERE user_id = :user_id
              AND status = 'Completed'
              AND created_date = DATE('now', 'localtime')
        """),
        {"user_id": user_id}
    ).scalars().all()

    # Rank based on points
    rank = db.session.execute(
        db.text("""
            SELECT COUNT(*) + 1
            FROM user_points
            WHERE total_points > :points
        """),
        {"points": points}
    ).scalar() or 1

    return jsonify({
        "status": "success",
        "points": points,
        "streak": streak,
        "rank": rank,
        "completed_tasks": completed_tasks,
        "completed_task_names": completed_names
    }), 200