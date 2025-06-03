from __future__ import annotations

from datetime import datetime, timedelta

from flask import Blueprint
from flask import Response as FlaskResponse
from flask import (
    abort,
    current_app,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.services.meetings import get_all_meetings

from ...database import session_scope
from ...models import Meeting
from ...services import (
    create_election,
    create_meeting,
    delete_election,
    delete_meeting,
    generate_qr_code,
    get_meeting,
)

admin_bp = Blueprint("admin", __name__, template_folder="templates")


def _require_admin():
    if not session.get("is_admin"):
        return redirect(url_for("admin.login_ui"))
    return None


@admin_bp.route("/", methods=["GET"])
def admin_redirect():
    return redirect(url_for("admin.dashboard_ui"))


@admin_bp.route("/login", methods=["GET", "POST"])
def login_ui():
    if request.method == "POST":
        pwd = request.form.get("password", "")
        if pwd == current_app.config["ADMIN_PASSWORD"]:
            session["is_admin"] = True
            return redirect(url_for("admin.dashboard_ui"))
        flash("Invalid password", "error")
    return render_template("login.html")


@admin_bp.route("/logout", methods=["POST"])
def logout_ui():
    session.pop("is_admin", None)
    return redirect(url_for("admin.login_ui"))


@admin_bp.route("/dashboard", methods=["GET"])
def dashboard_ui():
    resp = _require_admin()
    if resp:
        return resp
    with session_scope() as db:
        meetings = get_all_meetings(db, current_app.config["TZ"])
        base_url = request.url_root.rstrip("/") + "/admin"
        return render_template("dashboard.html", meetings=meetings, base_url=base_url)


@admin_bp.route("/meetings", methods=["GET", "POST"])
def meeting_create_ui():
    resp = _require_admin()
    if resp:
        return resp
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
                date = datetime.strptime(str(date_str), "%Y-%m-%d").date()
                time = datetime.strptime(str(time_str), "%H:%M").time()
                start_time = datetime.combine(date, time).replace(
                    tzinfo=current_app.config["TZ"]
                )

                end_time = start_time + timedelta(
                    hours=current_app.config["MEETING_DURATION_HOURS"]
                )
            except ValueError:
                flash("Invalid date/time format", "error")
                return redirect(request.url)

            with session_scope() as db:
                m_id, m_code = create_meeting(db, start_time, end_time)
            flash(f"Meeting created (code: {m_code})", "success")
            return redirect(url_for("admin.dashboard_ui"))
        except Exception as e:
            flash(str(e), "error")
    return render_template("create_meeting.html")


@admin_bp.route("/meetings/<int:meeting_id>", methods=["POST", "DELETE"])
def meeting_delete_ui(meeting_id):
    # If they really sent POST, reject unless it was the override:
    if request.method == "POST":
        if request.form.get("_method", "").upper() != "DELETE":
            abort(405)

    resp = _require_admin()
    if resp:
        return resp
    with session_scope() as db:
        success = delete_meeting(db, meeting_id)
    flash("Meeting deleted" if success else "Meeting not found", "info")
    return redirect(url_for("admin.dashboard_ui"))


@admin_bp.route("/meetings/<int:meeting_id>/elections", methods=["GET", "POST"])
def election_create_ui(meeting_id):
    resp = _require_admin()
    if resp:
        return resp
    if request.method == "POST":
        try:
            name = request.form["name"]
            with session_scope() as db:
                create_election(db, meeting_id, name)
            flash(f'Election created (name: "{name}")', "success")
            return redirect(url_for("admin.dashboard_ui"))
        except Exception as e:
            flash(str(e), "error")
    return render_template("create_election.html", meeting_id=meeting_id)


@admin_bp.route(
    "/meetings/<int:meeting_id>/elections/<int:election_id>", methods=["POST", "DELETE"]
)
def election_delete_ui(meeting_id, election_id):
    # If they really sent POST, reject unless it was the override:
    if request.method == "POST":
        if request.form.get("_method", "").upper() != "DELETE":
            abort(405)

    resp = _require_admin()
    if resp:
        return resp
    with session_scope() as db:
        success = delete_election(db, meeting_id, election_id)
    flash("Election deleted" if success else "Election not found", "info")
    return redirect(url_for("admin.dashboard_ui"))


@admin_bp.route("/meetings/<int:meeting_id>/qr.<fmt>", methods=["GET"])
def generate_qr(meeting_id: int, fmt: str = "svg") -> FlaskResponse:
    """Generate a QR code for checking into a meeting

    Args:
        meeting_id: The ID of the meeting
        fmt: The format of the QR code (svg or png)

    Returns:
        FlaskResponse: The QR code image as SVG or PNG
    """
    if fmt not in ("png", "svg"):
        abort(404)

    if not session.get("is_admin"):
        response = make_response("Unauthorized", 401)
        response.mimetype = "text/plain"
        return response

    with session_scope() as db:
        meeting = get_meeting(db, meeting_id)
        if not meeting:
            response = make_response("Invalid meeting", 404)
            response.mimetype = "text/plain"
            return response

        # Generate the check-in URL
        checkin_url = url_for(
            "public.auto_checkin",
            meeting_id=meeting_id,
            _external=True,
            _anchor=meeting["meeting_code"],
        )

        # Generate QR code using the logic function
        buffer = generate_qr_code(checkin_url, fmt == "svg")

        # Return the image as a response
        response = make_response(buffer.getvalue())
        response.mimetype = "image/svg+xml" if fmt == "svg" else "image/png"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        return response
