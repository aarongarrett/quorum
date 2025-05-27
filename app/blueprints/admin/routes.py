from __future__ import annotations

from datetime import datetime, timedelta

from flask import Blueprint
from flask import Response as FlaskResponse
from flask import (
    current_app,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from ...database import get_db_session
from ...logic import (
    create_election,
    create_meeting,
    delete_election,
    delete_meeting,
    generate_qr_code,
    get_meeting,
    get_meetings,
)

admin_bp = Blueprint("admin", __name__, template_folder="templates")


def _require_admin():
    if not session.get("is_admin"):
        return redirect(url_for("admin.login"))
    return None


@admin_bp.route("/")
def admin_redirect():
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        pwd = request.form.get("password", "")
        if pwd == current_app.config["ADMIN_PASSWORD"]:
            session["is_admin"] = True
            return redirect(url_for("admin.dashboard"))
        flash("Invalid password", "error")
    return render_template("login.html")


@admin_bp.route("/logout")
def logout():
    session.pop("is_admin", None)
    return redirect(url_for("admin.login"))


@admin_bp.route("/dashboard")
def dashboard():
    resp = _require_admin()
    if resp:
        return resp
    db = next(get_db_session())

    try:
        # Get all meetings and their stats
        meeting_info = []
        for meeting in get_meetings(db):
            meeting_info.append(get_meeting(db, meeting["id"]))

        base_url = request.url_root.rstrip("/") + "/admin"
        return render_template(
            "dashboard.html", meeting_info=meeting_info, base_url=base_url
        )
    finally:
        db.close()


@admin_bp.route("/meetings/create", methods=["GET", "POST"])
def meeting_create():
    resp = _require_admin()
    if resp:
        return resp
    db = next(get_db_session())
    if request.method == "POST":
        try:
            # Get form data
            date_str = request.form.get("date")
            time_str = request.form.get("time")

            # Validate form data
            if not date_str or not time_str:
                flash("All fields are required", "error")
                return redirect(request.url)

            try:
                # Use str() to ensure we have strings for strptime
                date = datetime.strptime(str(date_str), "%Y-%m-%d")
                time = datetime.strptime(str(time_str), "%H:%M")
                start_time = datetime.combine(date.date(), time.time())
                end_time = start_time + timedelta(
                    hours=current_app.config["MEETING_DURATION_HOURS"]
                )
            except ValueError:
                flash("Invalid date/time format", "error")
                return redirect(request.url)

            m_id, m_code = create_meeting(db, start_time, end_time)
            flash(f"Meeting created (code: {m_code})", "success")
            return redirect(url_for("admin.dashboard"))
        except Exception as e:
            flash(str(e), "error")
    return render_template("create_meeting.html")


@admin_bp.route("/meetings/<int:meeting_id>/delete", methods=["POST"])
def meeting_delete(meeting_id):
    resp = _require_admin()
    if resp:
        return resp
    db = next(get_db_session())
    success = delete_meeting(db, meeting_id)
    flash("Meeting deleted" if success else "Meeting not found", "info")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/meetings/<int:meeting_id>/elections/create", methods=["GET", "POST"])
def election_create(meeting_id):
    resp = _require_admin()
    if resp:
        return resp
    db = next(get_db_session())
    if request.method == "POST":
        try:
            name = request.form["name"]
            create_election(db, meeting_id, name)
            flash(f'Election created (name: "{name}")', "success")
            return redirect(url_for("admin.dashboard"))
        except Exception as e:
            flash(str(e), "error")
    return render_template("create_election.html", meeting_id=meeting_id)


@admin_bp.route(
    "/meetings/<int:meeting_id>/elections/<int:election_id>/delete", methods=["POST"]
)
def election_delete(meeting_id, election_id):
    resp = _require_admin()
    if resp:
        return resp
    db = next(get_db_session())
    success = delete_election(db, meeting_id, election_id)
    flash("Election deleted" if success else "Election not found", "info")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/qr/<int:meeting_id>/<meeting_code>")
def generate_qr(meeting_id: int, meeting_code: str) -> FlaskResponse:
    """Generate a QR code for checking into a meeting

    Args:
        meeting_id: The ID of the meeting
        meeting_code: The meeting code

    Returns:
        FlaskResponse: The QR code image as SVG
    """
    # Verify the meeting exists and the code is correct
    if not session.get("is_admin"):
        response = make_response("Unauthorized", 401)
        response.mimetype = "text/plain"
        return response

    db = next(get_db_session())
    try:
        meeting = get_meeting(db, meeting_id)
        if not meeting or meeting["meeting_code"] != meeting_code:
            response = make_response("Invalid meeting or code", 404)
            response.mimetype = "text/plain"
            return response

        # Generate the check-in URL
        checkin_url = url_for(
            "public.checkin",
            meeting_id=meeting_id,
            meeting_code=meeting_code,
            _external=True,
        )

        # Generate QR code using the logic function
        buffer = generate_qr_code(checkin_url)

        # Return the image as a response
        response = make_response(buffer.getvalue())
        response.mimetype = "image/svg+xml"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        return response
    finally:
        db.close()
