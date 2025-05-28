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

from ... import logic
from ...database import get_db_session

public_bp = Blueprint("public", __name__, template_folder="templates")


@public_bp.route("/")
def home() -> FlaskResponse:
    db = next(get_db_session())
    cookies = dict(request.cookies)
    meeting_tokens = session.get("meeting_tokens", {})
    try:
        meetings = logic.get_available_meetings(db, cookies, meeting_tokens)
        return render_template("home.html", meetings=meetings)
    finally:
        db.close()


@public_bp.route("/checkin/<int:meeting_id>", methods=["GET", "POST"])
def checkin(
    meeting_id: int,
) -> FlaskResponse:
    """Handle meeting check-in process

    Args:
        meeting_id: The ID of the meeting to check into

    Returns:
        FlaskResponse: The response object
    """
    db = next(get_db_session())
    try:
        if request.method == "POST" or "meeting_code" in request.args:
            meeting_code = (
                request.form.get("meeting_code")
                if request.method == "POST"
                else request.args.get("meeting_code")
            )

            if not meeting_code:
                flash("Meeting code is required", "error")
                return redirect(url_for("public.home"))

            # Check if user has already checked in to this meeting
            if f"meeting_{meeting_id}" in request.cookies or (
                session.get("checked_in_meetings")
                and meeting_id in session["checked_in_meetings"]
            ):
                flash("You have already checked in to this meeting", "error")
                return redirect(url_for("public.home"))

            # Process the check-in using the logic layer
            try:
                vote_token = logic.checkin(db, meeting_id, meeting_code)

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
                response = redirect(url_for("public.home"))
                response.set_cookie(
                    f"meeting_{meeting_id}",
                    "checked_in",
                    max_age=3600 * current_app.config["MEETING_DURATION_HOURS"],
                    httponly=True,
                    secure=request.is_secure,
                    samesite="Lax",
                )
                return response
            except ValueError as e:
                flash(str(e), "error")
                return redirect(url_for("public.home"))

        # For GET requests, show the check-in form
        # Get meeting details
        meeting = logic.get_meeting(db, meeting_id)
        if not meeting:
            flash(f"Invalid meeting ID ({meeting_id})", "error")
            return redirect(url_for("public.home"))

        return render_template(
            "checkin.html",
            meeting=meeting,
        )
    finally:
        db.close()


@public_bp.route("/vote/election/<int:election_id>", methods=["GET", "POST"])
def vote(
    election_id: int,
) -> FlaskResponse:
    """Handle voting for a specific election

    Args:
        election_id: The ID of the election to vote in

    Returns:
        FlaskResponse: The response object
    """
    # Check if user has any checked-in meetings
    if "checked_in_meetings" not in session or not session["checked_in_meetings"]:
        flash("You have not checked in to any meetings", "error")
        return redirect(url_for("public.home"))

    db = next(get_db_session())
    try:
        # Get the election with its meeting ID
        election = logic.get_election(db, election_id)
        if not election:
            flash("Invalid election", "error")
            return redirect(url_for("public.home"))

        meeting_id = election["meeting_id"]

        # Verify user is checked into this meeting
        if meeting_id not in session["checked_in_meetings"]:
            flash("You have not checked in to this meeting", "error")
            return redirect(url_for("public.home"))

        # Get the token for this meeting
        vote_token = session.get("meeting_tokens", {}).get(str(meeting_id))
        if not vote_token:
            flash("You have not checked in to this meeting", "error")
            return redirect(url_for("public.home"))

        if request.method == "POST":
            if "vote" not in request.form:
                flash("Vote is required", "error")
                return redirect(url_for("public.home", election_id=election_id))

            vote = request.form["vote"]
            try:
                logic.vote_in_election(db, meeting_id, election_id, vote_token, vote)
                flash("Vote recorded successfully", "success")
            except ValueError as e:
                flash(str(e), "error")
            return redirect(url_for("public.home"))

        # For GET requests, show the voting form
        return render_template("vote.html", election_name=election["name"])
    finally:
        db.close()
