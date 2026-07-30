from extensions import db, bcrypt
from models import Admin


def ensure_default_accounts():
    """Ensure default admin account exists in SQLite database."""
    try:
        db.create_all()
        # Ensure Default Admin Account
        admin = Admin.query.filter_by(admin_id="admin").first()
        if not admin:
            admin_pass_hash = bcrypt.generate_password_hash("Password@123").decode("utf-8")
            admin = Admin(admin_id="admin", password_hash=admin_pass_hash)
            db.session.add(admin)
            db.session.commit()
    except Exception as exc:
        print(f"Account seeding warning: {exc}")


if __name__ == "__main__":
    from app import create_app
    app = create_app()
    with app.app_context():
        ensure_default_accounts()
        print("Database admin account verified!")
