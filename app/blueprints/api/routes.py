from __future__ import annotations

import json
import time

from flask import Blueprint
from flask import Response as FlaskResponse
from flask import jsonify, request, session

from ... import logic
from ...database import get_db_session

api_bp = Blueprint("api", __name__, template_folder="templates")


@api_bp.route("/admin/updates")
def admin_updates():
    if not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 403

    db = next(get_db_session())

    def event_stream():
        try:
            while True:
                result = {}
                for meeting in logic.get_meetings(db):
                    result[str(meeting["id"])] = {
                        "checkins": logic.get_checkin_count(db, meeting["id"]),
                        "elections": {},
                    }
                    for election_id in logic.get_elections(db, meeting["id"]):
                        result[str(meeting["id"])]["elections"][
                            str(election_id)
                        ] = logic.get_election(db, election_id)

                data = json.dumps(result)

                yield f"data: {data}\n\n"
                time.sleep(5)  # Update interval

        except Exception as e:
            print(f"Error in admin stream: {e}")
            yield "event: error\ndata: An error occurred\n\n"
            time.sleep(5)

    return FlaskResponse(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@api_bp.route("/updates")
def meeting_stream():
    db = next(get_db_session())
    cookies = dict(request.cookies)
    meeting_tokens = session.get("meeting_tokens", {})

    def event_stream():
        while True:
            try:
                meetings = logic.get_available_meetings(db, cookies, meeting_tokens)

                # Format as SSE data
                data = json.dumps(meetings)
                yield f"data: {data}\n\n"

                # Wait before next update
                time.sleep(10)
            except Exception as e:
                print(f"Error in event stream: {e}")
                yield "event: error\ndata: An error occurred\n\n"
                time.sleep(5)  # Wait before retrying

    return FlaskResponse(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


"""
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
"""


@api_bp.route("/checkin/<int:meeting_id>/<meeting_code>", methods=["POST"])
def checkin(meeting_id: int, meeting_code: str) -> tuple[FlaskResponse, int]:
    """API endpoint to check in to a meeting"""
    if not meeting_code:
        return jsonify({"error": "Meeting code is required"}), 400

    db = next(get_db_session())
    try:
        token = logic.checkin(db, meeting_id, meeting_code)
        return jsonify({"token": token}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
