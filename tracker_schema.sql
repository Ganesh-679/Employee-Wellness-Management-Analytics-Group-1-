-- ============================================================
-- TRACKER MODULE DATABASE
-- Employee Wellness Tracker & Leaderboard
-- ============================================================


-- ============================================================
-- 1. Daily Tracker Tasks
-- ============================================================

CREATE TABLE IF NOT EXISTS tracker_tasks (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER NOT NULL,

    task_name TEXT NOT NULL,

    task_category TEXT NOT NULL,

    task_description TEXT,

    recommendation_source TEXT,

    scheduled_time TEXT,

    estimated_minutes INTEGER DEFAULT 15,

    priority TEXT DEFAULT 'Medium',

    status TEXT DEFAULT 'Pending',

    reminder_count INTEGER DEFAULT 0,

    is_notification_enabled INTEGER DEFAULT 1,

    created_date DATE DEFAULT CURRENT_DATE,

    completed_at DATETIME,

    FOREIGN KEY(user_id) REFERENCES users(id)

);



-- ============================================================
-- 2. Task Progress
-- ============================================================

CREATE TABLE IF NOT EXISTS tracker_progress (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    task_id INTEGER NOT NULL,

    user_id INTEGER NOT NULL,

    completion_percentage INTEGER DEFAULT 0,

    completed INTEGER DEFAULT 0,

    skipped INTEGER DEFAULT 0,

    completed_time DATETIME,

    notes TEXT,

    FOREIGN KEY(task_id) REFERENCES tracker_tasks(id),

    FOREIGN KEY(user_id) REFERENCES users(id)

);



-- ============================================================
-- 3. User Points
-- ============================================================

CREATE TABLE IF NOT EXISTS user_points (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER UNIQUE,

    total_points INTEGER DEFAULT 0,

    current_level TEXT DEFAULT 'Beginner',

    experience INTEGER DEFAULT 0,

    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(user_id) REFERENCES users(id)

);



-- ============================================================
-- 4. User Streaks
-- ============================================================

CREATE TABLE IF NOT EXISTS user_streaks (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER UNIQUE,

    current_streak INTEGER DEFAULT 0,

    best_streak INTEGER DEFAULT 0,

    last_completed_date DATE,

    FOREIGN KEY(user_id) REFERENCES users(id)

);



-- ============================================================
-- 5. Badges
-- ============================================================

CREATE TABLE IF NOT EXISTS badges (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    badge_name TEXT,

    badge_icon TEXT,

    badge_description TEXT,

    required_points INTEGER

);



-- ============================================================
-- 6. User Badges
-- ============================================================

CREATE TABLE IF NOT EXISTS user_badges (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER,

    badge_id INTEGER,

    earned_date DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(user_id) REFERENCES users(id),

    FOREIGN KEY(badge_id) REFERENCES badges(id)

);



-- ============================================================
-- 7. Leaderboard
-- ============================================================

CREATE TABLE IF NOT EXISTS leaderboard (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER UNIQUE,

    total_points INTEGER DEFAULT 0,

    total_tasks_completed INTEGER DEFAULT 0,

    current_streak INTEGER DEFAULT 0,

    health_score INTEGER DEFAULT 0,

    overall_score INTEGER DEFAULT 0,

    rank_position INTEGER DEFAULT 0,

    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(user_id) REFERENCES users(id)

);