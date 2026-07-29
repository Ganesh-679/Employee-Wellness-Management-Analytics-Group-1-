from flask import Flask, jsonify
from config import Config
from extensions import db, bcrypt, jwt, cors, limiter

from models import User, Admin, PasswordResetToken

from routes.user import user_bp
from routes.admin import admin_bp
from routes.password_reset import password_reset_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)

    # Frontend runs on a different origin (e.g. opened as a local file, or
    # a separate dev server) and calls http://localhost:5000/api/*, so CORS
    # must be open enough to allow that. Restrict `origins` to your actual
    # deployed frontend URL before going to production.
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(password_reset_bp)

    @app.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify({"status": "ok", "message": "Wellness Management backend is running"}), 200

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"message": "Resource not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"message": "Internal server error"}), 500

    @app.errorhandler(429)
    def rate_limited(e):
        return jsonify({"message": "Too many attempts. Please try again shortly."}), 429

    return app


app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=5000)
