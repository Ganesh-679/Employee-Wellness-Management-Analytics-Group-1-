import os
from werkzeug.utils import secure_filename

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from extensions import db
from models import MedicalReport

report_bp = Blueprint(
    "report",
    __name__,
    url_prefix="/api/reports"
)

ALLOWED_EXTENSIONS = {
    "pdf",
    "png",
    "jpg",
    "jpeg"
}


def allowed_file(filename):
    return "." in filename and \
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@report_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_report():

    claims = get_jwt()

    if claims.get("role") != "user":
        return jsonify({
            "message": "Only employees can upload reports."
        }), 403

    if "file" not in request.files:
        return jsonify({
            "message": "No file uploaded."
        }), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({
            "message": "No file selected."
        }), 400

    if not allowed_file(file.filename):
        return jsonify({
            "message": "Only PDF, JPG, JPEG and PNG files are allowed."
        }), 400

    upload_folder = os.path.join(
        current_app.root_path,
        "uploads",
        "reports"
    )

    os.makedirs(upload_folder, exist_ok=True)

    filename = secure_filename(file.filename)

    filepath = os.path.join(
        upload_folder,
        filename
    )

    file.save(filepath)

    report = MedicalReport(

        user_id=int(get_jwt_identity()),

        report_name=request.form.get(
            "reportName",
            filename
        ),

        report_type=request.form.get(
            "reportType",
            "Medical Report"
        ),

        file_name=filename,

        file_path=filepath

    )

    db.session.add(report)
    db.session.commit()

    return jsonify({

        "message": "Medical report uploaded successfully.",

        "report": report.to_dict()

    }), 201


@report_bp.route("", methods=["GET"])
@jwt_required()
def get_reports():

    reports = MedicalReport.query.filter_by(
        user_id=int(get_jwt_identity())
    ).all()

    return jsonify({

        "reports": [
            r.to_dict()
            for r in reports
        ]

    }), 200


@report_bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_report(id):

    report = MedicalReport.query.filter_by(

        id=id,

        user_id=int(get_jwt_identity())

    ).first()

    if not report:
        return jsonify({
            "message": "Report not found."
        }), 404

    if os.path.exists(report.file_path):
        os.remove(report.file_path)

    db.session.delete(report)

    db.session.commit()

    return jsonify({
        "message": "Report deleted successfully."
    }), 200