from __future__ import annotations

from flask import Blueprint
from flask import Response as FlaskResponse
from flask import jsonify, session

from ... import logic
from ...database import get_db_session

api_bp = Blueprint("api", __name__, template_folder="templates")


@api_bp.route("/stats/checkins")
def checkins():
    if not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 401
    db = next(get_db_session())
    try:
        result = {}
        for meeting in logic.get_meetings(db):
            result[str(meeting["id"])] = logic.get_checkin_count(db, meeting["id"])
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@api_bp.route("/stats/votes")
def votes():
    if not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 401
    db = next(get_db_session())
    try:
        result = {}
        for meeting in logic.get_meetings(db):
            for election_id in logic.get_elections(db, meeting["id"]):
                result[str(election_id)] = logic.get_election(db, election_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@api_bp.route("/checkin/<int:meeting_id>/<meeting_code>", methods=["POST"])
def checkin(meeting_id: int, meeting_code: str) -> tuple[FlaskResponse, int]:
    """API endpoint to check in to a meeting"""
    if not meeting_code:
        return jsonify({"error": "Meeting code is required"}), 400

    db = next(get_db_session())
    try:
        token, success = logic.checkin(db, meeting_id, meeting_code)
        if not success:
            return jsonify({"error": "Invalid meeting or code"}), 404

        return jsonify({"token": token}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
