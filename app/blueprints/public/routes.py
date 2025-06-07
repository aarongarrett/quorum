from __future__ import annotations

from flask import Blueprint
from flask import Response as FlaskResponse
from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from ...database import db
from ...services import (
    checkin,
    get_available_meetings,
    get_meeting,
    get_poll,
    vote_in_poll,
)

public_bp = Blueprint("public", __name__, template_folder="templates")


@public_bp.route("/", methods=["GET"])
def home_ui() -> FlaskResponse:
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
    meetings = get_available_meetings(db.session, vote_tokens, tz)
    return render_template("home.html", meetings=meetings)


@public_bp.route("/meetings/<int:meeting_id>/checkins", methods=["GET", "POST"])
def checkin_ui(
    meeting_id: int,
) -> FlaskResponse:
    """Handle meeting check-in process

    Args:
        meeting_id: The ID of the meeting to check into

    Returns:
        FlaskResponse: The response object
    """
    if request.method == "POST":
        meeting_code = request.form.get("meeting_code")

        if not meeting_code:
            flash("Meeting code is required", "error")
            return redirect(url_for("public.home_ui"))

        # Check if user has already checked in to this meeting
        if f"meeting_{meeting_id}" in request.cookies or (
            session.get("checked_in_meetings")
            and meeting_id in session["checked_in_meetings"]
        ):
            flash("You have already checked in to this meeting", "error")
            return redirect(url_for("public.home_ui"))

        # Process the check-in using the logic layer
        try:
            vote_token = checkin(db.session, meeting_id, meeting_code)

            # Update session state
            if "checked_in_meetings" not in session:
                session["checked_in_meetings"] = []
            if meeting_id not in session["checked_in_meetings"]:
                session["checked_in_meetings"].append(meeting_id)

            # Store the vote token for this meeting
            if "meeting_tokens" not in session:
                session["meeting_tokens"] = {}
            session["meeting_tokens"][str(meeting_id)] = vote_token
            session.modified = True

            # Set a cookie to prevent duplicate check-ins
            flash("You are checked in!", "success")
            response = redirect(url_for("public.home_ui"))
            response.set_cookie(
                f"meeting_{meeting_id}",
                vote_token,
                max_age=3600 * current_app.config["MEETING_DURATION_HOURS"],
                httponly=True,
                secure=request.is_secure,
                samesite="Lax",
            )
            return response
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("public.home_ui"))

    # For GET requests, show the check-in form
    # Get meeting details
    tz = current_app.config["TZ"]
    meeting = get_meeting(db.session, meeting_id, tz)
    if not meeting:
        flash(f"Invalid meeting ID ({meeting_id})", "error")
        return redirect(url_for("public.home_ui"))

    return render_template(
        "checkin.html",
        meeting=meeting,
    )


@public_bp.route("/meetings/<int:meeting_id>/auto_checkin")
def auto_checkin(meeting_id):
    return render_template("auto_checkin.html", meeting_id=meeting_id)


@public_bp.route(
    "/meetings/<int:meeting_id>/polls/<int:poll_id>/votes",
    methods=["GET", "POST"],
)
def vote_ui(
    meeting_id: int,
    poll_id: int,
) -> FlaskResponse:
    """Handle voting for a specific poll

    Args:
        meeting_id: The ID of the meeting to vote in
        poll_id: The ID of the poll to vote in

    Returns:
        FlaskResponse: The response object
    """
    # Check if user has any checked-in meetings
    if "checked_in_meetings" not in session or not session["checked_in_meetings"]:
        flash("You have not checked in to any meetings", "error")
        return redirect(url_for("public.home_ui"))

    # Get the poll with its meeting ID
    poll = get_poll(db.session, poll_id)
    if not poll or poll["meeting_id"] != meeting_id:
        flash("Invalid poll", "error")
        return redirect(url_for("public.home_ui"))

    # Verify user is checked into this meeting
    if meeting_id not in session["checked_in_meetings"]:
        flash("You have not checked in to this meeting", "error")
        return redirect(url_for("public.home_ui"))

    # Get the token for this meeting
    vote_token = session.get("meeting_tokens", {}).get(str(meeting_id))
    if not vote_token:
        flash("You have not checked in to this meeting", "error")
        return redirect(url_for("public.home_ui"))

    if request.method == "POST":
        if f"poll_{poll_id}" not in request.form:
            flash("Vote is required", "error")
            return redirect(url_for("public.home_ui", poll_id=poll_id))

        vote = request.form[f"poll_{poll_id}"]
        try:
            vote_in_poll(db.session, meeting_id, poll_id, vote_token, vote)
            flash("Vote recorded successfully", "success")
        except ValueError as e:
            flash(str(e), "error")
        return redirect(url_for("public.home_ui"))

    # For GET requests, show the voting form
    return render_template("vote.html", poll_id=poll_id, poll_name=poll["name"])
