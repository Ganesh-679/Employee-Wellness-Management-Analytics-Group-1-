-- =========================================================================
-- schema.sql (SQLite version)
-- -------------------------------------------------------------------------
-- SQL definitions for the WellSpring Analytics database schema.
-- This sets up the structure required by the login/registration API endpoints.
-- =========================================================================

-- 1. Users (Employees) Table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    totp_secret TEXT,
    two_factor_enabled BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Admins Table
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    totp_secret TEXT,
    two_factor_enabled BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Password Reset Tokens Table
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    identifier TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'admin')),
    otp_code TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT 0, -- SQLite uses 0/1 for booleans
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Health Records Table (Module 1: Employee Health Data Management)
CREATE TABLE IF NOT EXISTS health_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    record_date DATE NOT NULL,
    height_cm REAL NOT NULL,
    weight_kg REAL NOT NULL,
    bmi REAL NOT NULL,
    bmi_category TEXT NOT NULL,
    exercise_frequency TEXT NOT NULL,
    exercise_minutes_per_week INTEGER NOT NULL DEFAULT 0,
    sleep_hours REAL NOT NULL,
    water_intake_liters REAL,
    bp_systolic INTEGER,
    bp_diastolic INTEGER,
    resting_heart_rate INTEGER,
    stress_level TEXT,
    smoking_status TEXT,
    alcohol_consumption TEXT,
    attendance_status TEXT NOT NULL,
    checkup_date DATE,
    checkup_result TEXT,
    checkup_notes TEXT,
    assessment_notes TEXT,
    validation_status TEXT NOT NULL DEFAULT 'valid',
    validation_flags TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance optimization on key lookup fields
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_admins_admin_id ON admins(admin_id);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_identifier_role ON password_reset_tokens(identifier, role);
-- 5. Employee Profiles Table (Personal Information — part of Module 1)
CREATE TABLE IF NOT EXISTS employee_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
    full_name TEXT,
    employee_code TEXT,
    designation TEXT,
    department TEXT,
    date_of_joining DATE,
    phone TEXT,
    work_location TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_health_records_user_id ON health_records(user_id);
CREATE INDEX IF NOT EXISTS idx_health_records_record_date ON health_records(record_date);
