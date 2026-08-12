import os
from datetime import timedelta
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


def _build_database_uri():
    """
    Builds the SQLAlchemy database URI dynamically:
    1. Checks DATABASE_URL (production/custom DB URI).
    2. Checks DB_FILE (SQLite path resolved to an absolute path).
    3. Checks DB_HOST (PostgreSQL environment configuration).
    4. Default fallback: local SQLite database (wellness.db).
    """
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]

    if os.environ.get("DB_FILE"):
        db_path = os.path.abspath(os.environ["DB_FILE"])
        return f"sqlite:///{db_path}"

    if os.environ.get("DB_HOST"):
        user = os.environ.get("DB_USER", "postgres")
        password = os.environ.get("DB_PASSWORD", "")
        host = os.environ.get("DB_HOST", "localhost")
        port = os.environ.get("DB_PORT", "5432")
        name = os.environ.get("DB_NAME", "wellness_db")
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"

    return f"sqlite:///{os.path.join(basedir, 'wellness.db')}"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # --- Database ---
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

    # --- File uploads ---
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max upload size

    # --- AI / Gemini API Integration ---
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
