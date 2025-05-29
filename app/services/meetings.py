from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session

from app.models import Checkin, Meeting
from app.services.elections import get_election, get_elections, get_user_votes
from app.services.utils import is_available, make_pronounceable, to_utc


def get_checkin_count(db: Session, meeting_id: int) -> int:
    """Get check-in count for the meeting_id.

    Args:
        db: SQLAlchemy session
        meeting_id: the meeting id

    Returns:
        int: the check-in count
    """
    return db.query(Checkin).filter(Checkin.meeting_id == meeting_id).count()


def get_meeting(
    db: Session, meeting_id: int, time_zone: Optional[Any] = None
) -> Optional[dict[str, Any]]:
    """Retrieve a specific meeting.

    Args:
        db: SQLAlchemy session
        meeting_id: ID of the meeting to retrieve

    Returns:
        dict[str, Any]: a dictionary of the meeting/election information
    """
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()

    if not meeting:
        return None

    if time_zone is None:
        time_zone = timezone.utc

    result = {
        "id": meeting.id,
        "start_time": meeting.start_time.astimezone(time_zone),
        "end_time": meeting.end_time.astimezone(time_zone),
        "meeting_code": meeting.meeting_code,
        "checkins": get_checkin_count(db, meeting.id),
        "elections": [],
    }

    # Get elections for this meeting
    elections = get_elections(db, meeting.id)
    for election_id, name in elections.items():
        result["elections"].append(get_election(db, election_id))

    return result


def get_meetings(db: Session, time_zone: Optional[Any] = None) -> list[dict[str, Any]]:
    """Retrieve all meetings with their details.

    Args:
        db: SQLAlchemy session

    Returns:
        list[dict[str, Any]]: List of meetings with their details
    """
    meetings = db.query(Meeting).order_by(Meeting.start_time.desc()).all()

    if time_zone is None:
        time_zone = timezone.utc

    result = []
    for meeting in meetings:
        result.append(
            {
                "id": meeting.id,
                "start_time": meeting.start_time.astimezone(time_zone),
                "end_time": meeting.end_time.astimezone(time_zone),
                "meeting_code": meeting.meeting_code,
            }
        )

    return result


def get_available_meetings(
    db: Session,
    cookies: dict[str, str],
    meeting_tokens: dict[str, str],
    time_zone: Optional[Any] = None,
) -> list[dict[str, Any]]:
    """Retrieve all available meetings with their check-in status.

    Args:
        db: SQLAlchemy session
        cookies: a dictionary of user cookies

    Returns:
        list[dict[str, Any]]: List of meetings where each dictionary contains
            the meeting information and the election information for the current user
    """
    if time_zone is None:
        time_zone = timezone.utc
    current_time = datetime.now(timezone.utc)

    # Query all meetings ordered by start_time descending
    meetings = db.query(Meeting).order_by(Meeting.start_time.desc()).all()

    # Filter meetings that are currently available
    available_meetings = []
    for meeting in meetings:
        if is_available(meeting.start_time, meeting.end_time, current_time):
            meeting_id = meeting.id
            start_time = meeting.start_time.astimezone(time_zone).isoformat()
            end_time = meeting.end_time.astimezone(time_zone).isoformat()
            checked_in = cookies.get(f"meeting_{meeting_id}") is not None
            meeting_info = {
                "id": meeting_id,
                "start_time": start_time,
                "end_time": end_time,
                "checked_in": checked_in,
                "elections": [],
            }
            if checked_in:
                # Fetch elections and user's votes
                meeting = get_meeting(db, meeting_id)
                vote_token = meeting_tokens.get(str(meeting_id))
                if vote_token and meeting and meeting["end_time"] >= current_time:
                    elections = get_elections(db, meeting_id)
                    meeting_votes = get_user_votes(db, meeting_id, vote_token)
                    meeting_info["elections"] = [
                        {
                            "id": e_id,
                            "name": e_name,
                            "vote": meeting_votes.get(e_id, {}).get("vote", ""),
                        }
                        for e_id, e_name in elections.items()
                    ]
            available_meetings.append(meeting_info)

    return available_meetings


def create_meeting(
    db: Session, start_time: datetime, end_time: datetime
) -> tuple[int, str]:
    """Create a new meeting in the database.

    Args:
        db: SQLAlchemy session
        start_time: Meeting start time
        end_time: Meeting end time

    Returns:
        tuple[int, str]: A tuple containing (meeting_id, meeting_code)

    Raises:
        IntegrityError: If there's an issue with the database operation
    """

    start_utc = to_utc(start_time)
    end_utc = to_utc(end_time)

    if end_utc <= start_utc:
        raise ValueError("End time must be after start time")

    # Try to create a meeting with a unique code (retry once if code exists)
    for _ in range(2):
        meeting_code = make_pronounceable()
        meeting = Meeting(
            start_time=start_utc, end_time=end_utc, meeting_code=meeting_code
        )

        try:
            db.add(meeting)
            db.commit()
            db.refresh(meeting)
            return meeting.id, meeting.meeting_code
        except IntegrityError as e:
            db.rollback()
            # Check if error is due to duplicate meeting_code
            if "UNIQUE constraint failed: meetings.meeting_code" in str(e.orig):
                continue
            raise

    # If we get here, we've tried twice and failed
    raise ValueError("Failed to generate a unique meeting code after multiple attempts")


def delete_meeting(db: Session, meeting_id: int) -> bool:
    """Delete a meeting and all associated data from the database.

    Args:
        db: SQLAlchemy session
        meeting_id: ID of the meeting to delete

    Returns:
        bool: True if meeting was deleted, False if no meeting was found
    """
    try:
        # This will raise NoResultFound if meeting doesn't exist
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).one()

        # Cascade delete will handle related records due to the cascade="all, delete-orphan"
        # in the relationship definitions
        db.delete(meeting)
        db.commit()
        return True

    except NoResultFound:
        db.rollback()
        return False
    except Exception:
        db.rollback()
        raise
