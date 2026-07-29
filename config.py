import os
from datetime import timedelta
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


def _build_database_uri():
    # 1) Explicit DATABASE_URL always wins if set.
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]

    # 2) Aditya's SQLite .env format (DB_FILE) — matches his setup_db.py,
    #    which creates/reads the file relative to the current working
    #    directory. Run this app from the project root (same place you'd
    #    run setup_db.py) so both point at the same file.
    #    NOTE: must resolve to an absolute path — Flask-SQLAlchemy silently
    #    resolves relative sqlite:/// paths inside its own instance/
    #    folder instead of the cwd, which would create a second, empty
    #    database file instead of using Aditya's.
    if os.environ.get("DB_FILE"):
        db_path = os.path.abspath(os.environ["DB_FILE"])
        return f"sqlite:///{db_path}"

    # 3) Legacy: Postgres .env format (DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME)
    #    kept here in case the team ever switches back.
    if os.environ.get("DB_HOST"):
        user = os.environ.get("DB_USER", "postgres")
        password = os.environ.get("DB_PASSWORD", "")
        host = os.environ.get("DB_HOST", "localhost")
        port = os.environ.get("DB_PORT", "5432")
        name = os.environ.get("DB_NAME", "wellness_db")
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"

    # 4) Fallback: local SQLite file named wellness.db, zero setup needed.
    return f"sqlite:///{os.path.join(basedir, 'wellness.db')}"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # --- Database ---
    # Reads from .env automatically (same format Aditya's setup_db.py uses).
    # No .env / no DB_HOST set -> falls back to local SQLite so this still
    # runs standalone without Postgres installed.
    SQLALCHEMY_DATABASE_URI = _build_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- JWT ---
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    # Short-lived by default; "Remember me" on login extends this (see routes).
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    JWT_REMEMBER_ME_EXPIRES = timedelta(days=30)

    # --- OTP / password reset ---
    OTP_EXPIRY_MINUTES = 10

    # --- Email (for sending OTP codes) ---
    # Not required to run the app — if left unset, OTPs are just printed to
    # the console/log so you can test the flow without a real mail server.
    # Fill these in once the team decides on an email provider.
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_SENDER = os.environ.get("MAIL_SENDER", "no-reply@wellness.app")
