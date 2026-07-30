import os
from flask import Flask, jsonify, send_from_directory
from config import Config
from extensions import db, bcrypt, jwt, cors, limiter

from models import (
    User,
    Admin,
    PasswordResetToken,
    HealthRecord,
    EmployeeProfile,
    MedicalReport
)

from routes.user import user_bp
from routes.admin import admin_bp
from routes.password_reset import password_reset_bp
from routes.health import health_bp
from routes.report import report_bp
from routes.profile import profile_bp
from routes.risk import risk_bp
from routes.recommendations import recommendations_bp
from routes.sentiment import sentiment_bp
from routes.chatbot import chatbot_bp


def create_app():
    # Serve static frontend files from project root
    app = Flask(
        __name__,
        static_folder=os.path.dirname(os.path.abspath(__file__)),
        static_url_path="",
    )
    app.config.from_object(Config)
    app.url_map.strict_slashes = False

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)

    # The frontend is now served by this same app (see static_folder above),
    # so CORS is only needed if someone runs the frontend elsewhere (e.g. a
    # separate dev server). Restrict `origins` to your actual deployed
    # frontend URL before going to production.
    cors.init_app(app, resources={r"/*": {"origins": "*"}})

    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(password_reset_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(risk_bp)
    app.register_blueprint(recommendations_bp)
    app.register_blueprint(sentiment_bp)
    app.register_blueprint(chatbot_bp)

    @app.route("/")
    def serve_index():
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify({"status": "ok", "message": "Wellness Management backend is running"}), 200

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Private-Network"] = "true"
        return response

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"message": "Resource not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"message": "Internal server error"}), 500

    @app.errorhandler(429)
    def rate_limited(e):
        return jsonify({"message": "Too many attempts. Please try again shortly."}), 429

    @app.errorhandler(413)
    def request_entity_too_large(e):
        return jsonify({"message": "File too large. Maximum size is 5 MB."}), 413

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"message": "Method not allowed"}), 405

    return app


app = create_app()

with app.app_context():
    from seed_default_accounts import ensure_default_accounts
    ensure_default_accounts()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
