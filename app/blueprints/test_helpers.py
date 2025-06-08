from flask import Blueprint, current_app, jsonify

from app.database import db

test_bp = Blueprint("test_helpers", __name__, url_prefix="/_test")


@test_bp.route("/reset-db", methods=["POST"])
def reset_db():
    """DROP all tables and CREATE them again—only available under TESTING."""
    with current_app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()
    return jsonify({"status": "ok"}), 200
