from flask import Blueprint, jsonify

from app.database import engine
from app.models import Base

test_bp = Blueprint("test_helpers", __name__, url_prefix="/_test")


@test_bp.route("/reset-db", methods=["POST"])
def reset_db():
    """DROP all tables and CREATE them again—only available under TESTING."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return jsonify({"status": "ok"}), 200
