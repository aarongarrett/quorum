from __future__ import annotations

import json
import time
from datetime import datetime

from flask import Blueprint
from flask import Response as FlaskResponse
from flask import current_app, jsonify, request, session
from sqlalchemy.orm import sessionmaker

from ...database import db
from ...services import (
    checkin,
    create_meeting,
    create_poll,
    get_all_meetings,
    get_available_meetings,
    vote_in_poll,
)

api_bp = Blueprint("api", __name__, template_folder="templates")


@api_bp.route("/login", methods=["POST"])
def admin_login_api() -> tuple[FlaskResponse, int]:
    """API endpoint to login as admin"""
    payload = request.get_json()
    if "password" not in payload:
        return jsonify({"error": "Password is required"}), 400
    if payload["password"] == current_app.config["ADMIN_PASSWORD"]:
        session["is_admin"] = True
        return jsonify({"success": True}), 200
    return jsonify({"error": "Invalid password"}), 400


@api_bp.route("/admin/meetings", methods=["POST"])
def create_meeting_api() -> tuple[FlaskResponse, int]:
    """API endpoint to create a meeting"""
    if not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 403

    payload = request.get_json()
    if "start_time" not in payload or len(payload["start_time"]) == 0:
        return jsonify({"error": "Start time is required and must not be empty"}), 400
    if "end_time" not in payload or len(payload["end_time"]) == 0:
        return jsonify({"error": "End time is required and must not be empty"}), 400
    start_time = datetime.fromisoformat(payload["start_time"])
    end_time = datetime.fromisoformat(payload["end_time"])

    try:
        m_id, m_code = create_meeting(db.session, start_time, end_time)
        return jsonify({"meeting_id": m_id, "meeting_code": m_code}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/admin/meetings/<int:meeting_id>/polls", methods=["POST"])
def create_poll_api(meeting_id: int) -> tuple[FlaskResponse, int]:
    """API endpoint to create a meeting"""
    if not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 403

    payload = request.get_json()
    if "name" not in payload or len(payload["name"]) == 0:
        return jsonify({"error": "Name is required and must not be empty"}), 400
    name = payload["name"]

    try:
        e_id = create_poll(db.session, meeting_id, name)
        return jsonify({"poll_id": e_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/meetings", methods=["GET", "POST"])
def meetings_api() -> tuple[FlaskResponse, int]:
    """API endpoint to get available meetings"""
    vote_tokens = {}
    if request.method == "POST":
        # API-driven path
        try:
            vote_tokens = {int(k): v for k, v in request.get_json().items()}
        except Exception:
            return jsonify({"error": "Invalid token map"}), 400
    else:
        cookies = dict(request.cookies)
        meeting_tokens = session.get("meeting_tokens", {})

        # Get tokens from cookies
        vote_tokens = {}
        for key, val in cookies.items():
            try:
                if key.startswith("meeting_"):
                    meeting_id = int(key.split("_", 1)[1])
                    vote_tokens[meeting_id] = val
            except (IndexError, ValueError):
                continue  # skip malformed cookie

        # In case a cookie was cleared, take tokens from the session
        meeting_tokens = {int(k): v for k, v in meeting_tokens.items()}
        vote_tokens.update(meeting_tokens)

    try:
        tz = current_app.config["TZ"]
        meetings = get_available_meetings(db.session, vote_tokens, tz)
        return jsonify(meetings), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/meetings/<int:meeting_id>/checkins", methods=["POST"])
def checkin_api(meeting_id: int) -> tuple[FlaskResponse, int]:
    """API endpoint to check in to a meeting"""
    payload = request.get_json()
    if "meeting_code" not in payload or len(payload["meeting_code"]) == 0:
        return jsonify({"error": "Meeting code is required and must not be empty"}), 400
    meeting_code = payload["meeting_code"]

    try:
        token = checkin(db.session, meeting_id, meeting_code)
        return jsonify({"token": token}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/meetings/<int:meeting_id>/polls/<int:poll_id>/votes", methods=["POST"])
def vote_api(meeting_id: int, poll_id: int) -> tuple[FlaskResponse, int]:
    """API endpoint to check in to a meeting"""
    payload = request.get_json()
    if "token" not in payload or len(payload["token"]) == 0:
        return jsonify({"error": "Token is required and must not be empty"}), 400
    if "vote" not in payload or len(payload["vote"]) == 0:
        return jsonify({"error": "Vote is required and must not be empty"}), 400
    token = payload["token"]
    vote = payload["vote"]

    try:
        vote_in_poll(db.session, meeting_id, poll_id, token, vote)
        return jsonify({"success": True}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/admin/meetings/stream")
def admin_stream_api():
    if not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 403

    tz = current_app.config["TZ"]
    engine = db.engine

    def event_stream():
        last_sent = time.time()
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        try:
            while True:
                try:
                    meetings = get_all_meetings(session, tz)
                    data = json.dumps(meetings, default=str)
                    yield f"data: {data}\n\n"
                    last_sent = time.time()
                except GeneratorExit:
                    break
                except Exception as e:
                    yield f"event: error\ndata: An error occurred {e}\n\n"
                    last_sent = time.time()
                # If it's been too long since the last update, ping
                if time.time() - last_sent > 15:
                    yield ": ping\n\n"
                    last_sent = time.time()
                time.sleep(3)
        finally:
            session.close()

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
    cookies = dict(request.cookies)
    meeting_tokens = session.get("meeting_tokens", {})

    # Get tokens from cookies
    vote_tokens = {}
    for key, val in cookies.items():
        try:
            if key.startswith("meeting_"):
                meeting_id = int(key.split("_", 1)[1])
                vote_tokens[meeting_id] = val
        except (IndexError, ValueError):
            continue  # skip malformed cookie

    # In case a cookie was cleared, take tokens from the session
    meeting_tokens = {int(k): v for k, v in meeting_tokens.items()}
    vote_tokens.update(meeting_tokens)

    tz = current_app.config["TZ"]
    engine = db.engine

    def event_stream():
        last_sent = time.time()
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        try:
            while True:
                try:
                    meetings = get_available_meetings(session, vote_tokens, tz)
                    data = json.dumps(meetings, default=str)
                    yield f"data: {data}\n\n"
                    last_sent = time.time()
                except GeneratorExit:
                    break
                except Exception as e:
                    yield f"event: error\ndata: An error occurred {e}\n\n"
                    last_sent = time.time()

                # If it's been too long since the last update, ping
                if time.time() - last_sent > 15:
                    yield ": ping\n\n"
                    last_sent = time.time()
                time.sleep(5)
        finally:
            session.close()

    return FlaskResponse(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
