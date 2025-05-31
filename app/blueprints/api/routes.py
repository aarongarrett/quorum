from __future__ import annotations

import json
import time

from flask import Blueprint
from flask import Response as FlaskResponse
from flask import current_app, jsonify, request, session

from ...database import get_db_session
from ...services import checkin, get_all_meetings, get_available_meetings

api_bp = Blueprint("api", __name__, template_folder="templates")


@api_bp.route("/admin/meetings/stream")
def admin_stream_api():
    if not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 403

    db = next(get_db_session())
    tz = current_app.config["TZ"]

    def event_stream():
        try:
            while True:
                meetings = get_all_meetings(db, tz)
                data = json.dumps(meetings, default=str)
                yield f"data: {data}\n\n"
                time.sleep(5)

        except Exception as e:
            yield f"event: error\ndata: An error occurred {e}\n\n"
            time.sleep(5)

    return FlaskResponse(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@api_bp.route("/meetings/stream")
def user_stream_api():
    db = next(get_db_session())
    cookies = dict(request.cookies)
    meeting_tokens = session.get("meeting_tokens", {})

    # Get tokens from cookies
    vote_tokens = {
        int(key.split("_", 1)[1]): val
        for key, val in cookies.items()
        if key.startswith("meeting_")
    }
    # In case a cookie was cleared, take tokens from the session
    vote_tokens.update(meeting_tokens)
    tz = current_app.config["TZ"]

    def event_stream():
        while True:
            try:
                meetings = get_available_meetings(db, vote_tokens, tz)

                # Format as SSE data
                data = json.dumps(meetings, default=str)
                yield f"data: {data}\n\n"

                # Wait before next update
                time.sleep(10)
            except Exception as e:
                yield f"event: error\ndata: An error occurred {e}\n\n"
                time.sleep(5)  # Wait before retrying

    return FlaskResponse(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@api_bp.route("/meetings/<int:meeting_id>/checkins", methods=["POST"])
def checkin_api(meeting_id: int) -> tuple[FlaskResponse, int]:
    """API endpoint to check in to a meeting"""
    payload = request.get_json()
    meeting_code = payload["meeting_code"]
    if not meeting_code:
        return jsonify({"error": "Meeting code is required"}), 400

    db = next(get_db_session())
    try:
        token = checkin(db, meeting_id, meeting_code)
        return jsonify({"token": token}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
