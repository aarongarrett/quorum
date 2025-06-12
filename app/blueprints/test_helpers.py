from flask import Blueprint, current_app, jsonify
from sqlalchemy import text

from app.database import db

test_bp = Blueprint("test_helpers", __name__, url_prefix="/_test")


@test_bp.route("/health")
def health_check():
    """
    A basic health check endpoint that returns HTTP 200 if the app can
    successfully query the database, otherwise HTTP 500.
    """
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify(status="up"), 200
    except Exception as e:
        return jsonify(status="down", error=str(e)), 500


@test_bp.route("/reset-db", methods=["POST"])
def reset_db():
    """DROP all tables and CREATE them again—only available under TESTING."""
    with current_app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()
    return jsonify({"status": "ok"}), 200
