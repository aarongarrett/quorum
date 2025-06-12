from __future__ import annotations

import json
import time
from datetime import datetime

from flask import Response as FlaskResponse
from flask import current_app, request, session
from flask_restx import Namespace, Resource, fields
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

api = Namespace(
    "api",
    description="Quorum Voting System JSON API",
    path="/",
)

login_model = api.model(
    "AdminLogin",
    {
        "password": fields.String(
            required=True, example="t3rri3rs", description="Admin password"
        )
    },
)

meeting_in = api.model(
    "MeetingCreate",
    {
        "start_time": fields.String(
            required=True,
            example="2025-06-20T15:00:00-04:00",
            description="ISO8601 start time (timezone-aware)",
        ),
        "end_time": fields.String(
            required=True,
            example="2025-06-20T17:00:00-04:00",
            description="ISO8601 end time (timezone-aware)",
        ),
    },
)

meeting_out = api.model(
    "MeetingResponse",
    {
        "meeting_id": fields.Integer(readonly=True),
        "meeting_code": fields.String(readonly=True),
    },
)

poll_in = api.model(
    "PollCreate",
    {
        "name": fields.String(
            required=True, example="Best Color", description="Poll name"
        )
    },
)

poll_out = api.model("PollResponse", {"poll_id": fields.Integer(readonly=True)})
full_poll_out = api.model(
    "FullPollResponse",
    {
        "id": fields.Integer(readonly=True),
        "name": fields.String(readonly=True),
        "vote": fields.String(readonly=True),
    },
)

token_in = api.model(
    "Checkin",
    {"meeting_code": fields.String(required=True, description="Meeting code")},
)

vote_in = api.model(
    "Vote",
    {
        "token": fields.String(required=True, description="Vote token"),
        "vote": fields.String(
            required=True, example="A", description="Choice letter A-H"
        ),
    },
)

full_meeting_out = api.model(
    "FullMeetingResponse",
    {
        "id": fields.Integer(readonly=True),
        "start_time": fields.String(readonly=True),
        "end_time": fields.String(readonly=True),
        "meeting_code": fields.String(readonly=True),
        "checked_in": fields.Boolean(readonly=True),
        "polls": fields.List(fields.Nested(full_poll_out)),
    },
)


@api.route("/login")
class AdminLogin(Resource):
    @api.expect(login_model, validate=True)
    @api.response(200, "Logged in")
    @api.response(400, "Invalid request")
    def post(self):
        """Authenticate as admin"""
        pwd = api.payload["password"]
        if len(pwd) == 0:
            api.abort(400, "Password must not be empty")
        if pwd == current_app.config["ADMIN_PASSWORD"]:
            session["is_admin"] = True
            return {"success": True}, 200
        api.abort(400, "Invalid password")


@api.route("/admin/meetings")
class CreateMeeting(Resource):
    @api.expect(meeting_in, validate=True)
    @api.marshal_with(meeting_out, code=201)
    @api.response(403, "Unauthorized")
    @api.response(500, "Server error")
    def post(self):
        """Create a new meeting (admin only)"""
        if not session.get("is_admin"):
            api.abort(403, "Unauthorized")

        data = api.payload
        start = datetime.fromisoformat(data["start_time"])
        end = datetime.fromisoformat(data["end_time"])

        try:
            mid, mcode = create_meeting(db.session, start, end)
            return {"meeting_id": mid, "meeting_code": mcode}, 201
        except Exception as e:
            api.abort(500, str(e))


@api.route("/admin/meetings/<int:meeting_id>/polls")
@api.param("meeting_id", "ID of the meeting")
class CreatePoll(Resource):
    @api.expect(poll_in, validate=True)
    @api.marshal_with(poll_out, code=201)
    @api.response(403, "Unauthorized")
    @api.response(500, "Server error")
    def post(self, meeting_id):
        """Create a new poll under a meeting (admin only)"""
        if not session.get("is_admin"):
            api.abort(403, "Unauthorized")
        name = api.payload["name"]
        if len(name) == 0:
            api.abort(400, "Name must not be empty")
        try:
            pid = create_poll(db.session, meeting_id, name)
            return {"poll_id": pid}, 201
        except Exception as e:
            api.abort(500, str(e))


@api.route("/meetings")
class Meetings(Resource):
    @api.marshal_list_with(full_meeting_out)
    @api.response(200, "Success")
    @api.response(500, "Server error")
    def get(self):
        """Get all currently available meetings"""
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
        meetings = get_available_meetings(db.session, vote_tokens, tz)
        return meetings

    @api.expect(api.model("TokenMap", {"<meeting_id>": fields.String()}), validate=True)
    @api.marshal_list_with(full_meeting_out)
    @api.response(200, "Success")
    @api.response(400, "Invalid payload")
    @api.response(500, "Server error")
    def post(self):
        """Get available meetings, passing in vote tokens via JSON"""
        try:
            vote_tokens = {int(k): v for k, v in api.payload.items()}
        except Exception:
            api.abort(400, "Invalid token map")
        tz = current_app.config["TZ"]
        meetings = get_available_meetings(db.session, vote_tokens, tz)
        return meetings


@api.route("/meetings/<int:meeting_id>/checkins")
@api.param("meeting_id", "ID of the meeting")
class CheckinAPI(Resource):
    @api.expect(token_in, validate=True)
    @api.marshal_with(api.model("TokenResponse", {"token": fields.String()}))
    @api.response(200, "Checked in")
    @api.response(400, "Bad request")
    @api.response(404, "Not found")
    @api.response(500, "Server error")
    def post(self, meeting_id):
        """Check in to a meeting and receive a vote token"""
        code = api.payload["meeting_code"]
        if len(code) == 0:
            api.abort(400, "Meeting code must not be empty")

        try:
            token = checkin(db.session, meeting_id, code)
            return {"token": token}
        except ValueError as e:
            api.abort(404, str(e))
        except Exception as e:
            api.abort(500, str(e))


@api.route("/meetings/<int:meeting_id>/polls/<int:poll_id>/votes")
@api.param("meeting_id", "ID of the meeting")
@api.param("poll_id", "ID of the poll")
class VoteAPI(Resource):
    @api.expect(vote_in, validate=True)
    @api.response(200, "Vote recorded")
    @api.response(400, "Bad request")
    @api.response(404, "Not found")
    @api.response(500, "Server error")
    def post(self, meeting_id, poll_id):
        """Cast a vote in a poll"""
        data = api.payload
        try:
            vote_in_poll(db.session, meeting_id, poll_id, data["token"], data["vote"])
            return {"success": True}
        except ValueError as e:
            api.abort(404, str(e))
        except Exception as e:
            api.abort(500, str(e))


@api.route("/admin/meetings/stream")
class AdminStream(Resource):
    @api.doc(
        description="Server-sent events stream of all meetings metrics (admin only)",
        responses={200: "SSE text/event-stream", 403: "Unauthorized"},
        produces=["text/event-stream"],
    )
    def get(self):
        """Admin-only SSE: real-time check-ins and vote tallies (updates every 3s)."""
        if not session.get("is_admin"):
            api.abort(403, "Unauthorized")

        tz = current_app.config["TZ"]
        engine = db.engine

        def event_stream():
            last_sent = time.time()
            SessionLocal = sessionmaker(bind=engine)
            sess = SessionLocal()
            try:
                while True:
                    try:
                        data = json.dumps(get_all_meetings(sess, tz), default=str)
                        yield f"data: {data}\n\n"
                        last_sent = time.time()
                    except GeneratorExit:
                        break
                    except Exception as e:
                        yield f"event: error\ndata: {e}\n\n"
                        last_sent = time.time()

                    if time.time() - last_sent > 15:
                        yield ": ping\n\n"
                        last_sent = time.time()

                    time.sleep(3)
            finally:
                sess.close()

        return FlaskResponse(
            event_stream(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )


@api.route("/meetings/stream")
class UserStream(Resource):
    @api.doc(
        description="Server-sent events stream of currently available meetings",
        responses={200: "SSE text/event-stream"},
        produces=["text/event-stream"],
    )
    def get(self):
        """Public SSE: list of currently available meetings (updates every 5s)."""
        # reconstruct vote tokens from cookies + session
        vote_tokens = {}
        for k, v in dict(request.cookies).items():
            if k.startswith("meeting_"):
                try:
                    vote_tokens[int(k.split("_", 1)[1])] = v
                except ValueError:
                    pass
        vote_tokens.update(
            {int(k): v for k, v in session.get("meeting_tokens", {}).items()}
        )

        tz = current_app.config["TZ"]
        engine = db.engine

        def event_stream():
            last_sent = time.time()
            SessionLocal = sessionmaker(bind=engine)
            sess = SessionLocal()
            try:
                while True:
                    try:
                        data = json.dumps(
                            get_available_meetings(sess, vote_tokens, tz), default=str
                        )
                        yield f"data: {data}\n\n"
                        last_sent = time.time()
                    except GeneratorExit:
                        break
                    except Exception as e:
                        yield f"event: error\ndata: {e}\n\n"
                        last_sent = time.time()

                    if time.time() - last_sent > 15:
                        yield ": ping\n\n"
                        last_sent = time.time()

                    time.sleep(5)
            finally:
                sess.close()

        return FlaskResponse(
            event_stream(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
