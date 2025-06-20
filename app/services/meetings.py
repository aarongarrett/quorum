from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import func, tuple_
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session, joinedload

from app.models import Checkin, Meeting, PollVote
from app.services.polls import get_poll, get_polls
from app.services.utils import make_pronounceable, to_utc


def get_meeting(
    db: Session, meeting_id: int, time_zone: Optional[Any] = None
) -> Optional[dict[str, Any]]:
    """Retrieve a specific meeting.

    Args:
        db: SQLAlchemy session
        meeting_id: ID of the meeting to retrieve

    Returns:
        dict[str, Any]: a dictionary of the meeting/poll information
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
        "checkins": db.query(Checkin).filter(Checkin.meeting_id == meeting_id).count(),
        "polls": [],
    }

    # Get polls for this meeting
    polls = get_polls(db, meeting.id)
    for poll_id, name in polls.items():
        result["polls"].append(get_poll(db, poll_id))

    return result


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
            unique_error = "UNIQUE constraint failed: meetings.meeting_code"
            if unique_error in str(e.orig):
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

        # Cascade delete will handle related records due to the
        # cascade="all, delete-orphan" in the relationship definitions
        db.delete(meeting)
        db.commit()
        return True

    except NoResultFound:
        db.rollback()
        return False
    except Exception:
        db.rollback()
        raise


def get_all_meetings(db: Session, tz: ZoneInfo) -> list[dict]:
    """
    Returns a list of meetings, each as a dict:
    {
      "id": int,
      "start_time": "ISO8601 string in tz",
      "end_time":   "ISO8601 string in tz",
      "meeting_code": str,
      "checkins": int,
      "polls": [
        {
          "id": int,
          "name": str,
          "total_votes": int,
          "votes": { "A": int, ..., "H": int }
        }, ...
      ]
    }
    """

    def to_local_iso(dt: datetime, tz: ZoneInfo) -> str:
        return dt.astimezone(tz).isoformat()

    # 1) fetch meetings + polls
    meetings = (
        db.query(Meeting)
        .options(joinedload(Meeting.polls))
        .order_by(Meeting.start_time.desc())
        .all()
    )

    # 2) bulk‑compute checkin counts
    checkin_counts = {
        mid: cnt
        for mid, cnt in db.query(Checkin.meeting_id, func.count())
        .group_by(Checkin.meeting_id)
        .all()
    }

    # 3) bulk‑compute vote counts
    raw_votes = (
        db.query(PollVote.poll_id, PollVote.vote, func.count().label("cnt"))
        .group_by(PollVote.poll_id, PollVote.vote)
        .all()
    )
    vote_counts: dict[int, dict[str, int]] = {}
    for eid, vote, cnt in raw_votes:
        vote_counts.setdefault(eid, {}).update({vote: cnt})

    result = []
    for m in meetings:
        elects = []
        for e in m.polls:
            vc = vote_counts.get(e.id, {})
            elects.append(
                {
                    "id": e.id,
                    "name": e.name,
                    "total_votes": sum(vc.values()),
                    "votes": {opt: vc.get(opt, 0) for opt in "ABCDEFGH"},
                }
            )
        result.append(
            {
                "id": m.id,
                "start_time": to_local_iso(m.start_time, tz),
                "end_time": to_local_iso(m.end_time, tz),
                "meeting_code": m.meeting_code,
                "checkins": checkin_counts.get(m.id, 0),
                "polls": elects,
            }
        )
    return result


def get_available_meetings(
    db: Session, vote_tokens: dict[int, str], tz: ZoneInfo
) -> list[dict]:
    """Return only meetings that are currently active (start-15m → end).

    Each meeting is of the following form:
    {
      "id": int,
      "start_time": "ISO8601 string in tz",
      "end_time":   "ISO8601 string in tz",
      "meeting_code": str,
      "checked_in": bool,
      "polls": [
        {
          "id": int,
          "name": str,
          "vote": str | None
        }, ...
      ]
    }
    """
    now_utc = datetime.now(timezone.utc)
    window_end = now_utc + timedelta(minutes=15)

    # 1) Bulk fetch only the “active” meetings + their polls
    active = (
        db.query(Meeting)
        .options(joinedload(Meeting.polls))
        .filter(Meeting.start_time <= window_end, Meeting.end_time >= now_utc)
        .order_by(Meeting.start_time.desc())
        .all()
    )

    # 2) Verify that each provided token is valid for its claimed meeting
    if vote_tokens:
        valid_checkins = set(
            db.query(Checkin.meeting_id, Checkin.vote_token)
            .filter(
                tuple_(Checkin.meeting_id, Checkin.vote_token).in_(
                    list(vote_tokens.items())
                )
            )
            .all()
        )
    else:
        valid_checkins = set()

    # 3) Bulk‐fetch all votes for those tokens in one go
    #    (So we don’t do one query per poll per meeting)
    rows = (
        db.query(PollVote.poll_id, PollVote.vote, PollVote.vote_token)
        .filter(PollVote.vote_token.in_(vote_tokens.values()))
        .all()
    )
    # pivot into: { (poll_id, vote_token) → vote }
    vote_map = {(eid, token): v for eid, v, token in rows}

    result = []
    for m in active:
        token = vote_tokens.get(m.id)
        checked_in = token is not None and (m.id, token) in valid_checkins

        elect_list = []
        for e in m.polls:
            user_vote = vote_map.get((e.id, token)) if checked_in else None
            elect_list.append({"id": e.id, "name": e.name, "vote": user_vote})

        result.append(
            {
                "id": m.id,
                # convert into the local zone & ISO‑format for JSON
                "start_time": m.start_time.astimezone(tz).isoformat(),
                "end_time": m.end_time.astimezone(tz).isoformat(),
                "meeting_code": m.meeting_code,
                "checked_in": checked_in,
                "polls": elect_list,
            }
        )

    return result
