import re
import random
import smtplib
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
