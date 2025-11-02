"""Meeting business logic."""
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, List, Dict
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.db.models import Meeting, Poll, Checkin, PollVote
from app.core.utils import make_pronounceable, to_utc, to_timezone
from app.services.poll import get_vote_counts, get_vote_counts_bulk
from app.core.constants import VOTE_OPTIONS


def create_meeting(db: Session, start_time: datetime, end_time: datetime) -> Tuple[int, str]:
    """Create a new meeting."""
    start_utc = to_utc(start_time)
    end_utc = to_utc(end_time)

    if end_utc <= start_utc:
        raise ValueError("End time must be after start time")

    # Try to create meeting with unique code
    for _ in range(3):
        meeting_code = make_pronounceable()
        meeting = Meeting(
            start_time=start_utc,
            end_time=end_utc,
            meeting_code=meeting_code
        )

        try:
            db.add(meeting)
            db.commit()
            db.refresh(meeting)
            return meeting.id, meeting.meeting_code
        except IntegrityError:
            db.rollback()
            continue

    raise ValueError("Failed to generate unique meeting code")


def get_meeting(db: Session, meeting_id: int, tz: ZoneInfo) -> Optional[Dict]:
    """Get a specific meeting with details."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        return None

    polls = []
    for poll in meeting.polls:
        vote_counts = get_vote_counts(db, poll.id)
        polls.append({
            "id": poll.id,
            "name": poll.name,
            "total_votes": sum(vote_counts.values()),
            "votes": vote_counts
        })

    checkin_count = db.query(Checkin).filter(Checkin.meeting_id == meeting_id).count()

    return {
        "id": meeting.id,
        "start_time": to_timezone(meeting.start_time, tz).isoformat(),
        "end_time": to_timezone(meeting.end_time, tz).isoformat(),
        "meeting_code": meeting.meeting_code,
        "checkins": checkin_count,
        "polls": polls
    }


def delete_meeting(db: Session, meeting_id: int) -> bool:
    """Delete a meeting."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        return False

    db.delete(meeting)
    db.commit()
    return True


def get_all_meetings(db: Session, tz: ZoneInfo) -> List[Dict]:
    """Get all meetings with full details (admin view)."""
    meetings = db.query(Meeting).options(joinedload(Meeting.polls)).order_by(Meeting.start_time.desc()).all()

    # Bulk compute checkin counts
    checkin_counts = dict(
        db.query(Checkin.meeting_id, func.count()).group_by(Checkin.meeting_id).all()
    )

    # Bulk compute vote counts (using centralized function)
    vote_counts = get_vote_counts_bulk(db)

    result = []
    for meeting in meetings:
        polls = []
        for poll in meeting.polls:
            vc = vote_counts.get(poll.id, {option: 0 for option in VOTE_OPTIONS})
            polls.append({
                "id": poll.id,
                "name": poll.name,
                "total_votes": sum(vc.values()),
                "votes": vc
            })

        result.append({
            "id": meeting.id,
            "start_time": to_timezone(meeting.start_time, tz).isoformat(),
            "end_time": to_timezone(meeting.end_time, tz).isoformat(),
            "meeting_code": meeting.meeting_code,
            "checkins": checkin_counts.get(meeting.id, 0),
            "polls": polls
        })

    return result


def get_available_meetings(db: Session, token_map: Dict[int, str], tz: ZoneInfo) -> List[Dict]:
    """Get currently available meetings with user's check-in/vote status."""
    from app.services.utils import get_checkin_by_token

    now = datetime.now(timezone.utc)
    buffer_start = now + timedelta(minutes=15)

    meetings = db.query(Meeting).options(
        joinedload(Meeting.polls)
    ).filter(
        Meeting.start_time <= buffer_start,
        Meeting.end_time >= now
    ).order_by(Meeting.start_time.desc()).all()

    # Verify tokens and get checkin IDs (O(1) indexed lookups)
    checkin_map = {}  # meeting_id -> checkin_id
    for meeting_id, token in token_map.items():
        checkin_record = get_checkin_by_token(db, meeting_id, token)
        if checkin_record:
            checkin_map[meeting_id] = checkin_record.id

    # Get votes for these checkins
    if checkin_map:
        vote_data = db.query(
            PollVote.poll_id,
            PollVote.checkin_id,
            PollVote.vote
        ).filter(PollVote.checkin_id.in_(checkin_map.values())).all()

        vote_map = {(poll_id, checkin_id): vote for poll_id, checkin_id, vote in vote_data}
    else:
        vote_map = {}

    result = []
    for meeting in meetings:
        checkin_id = checkin_map.get(meeting.id)
        checked_in = checkin_id is not None

        polls = []
        for poll in meeting.polls:
            user_vote = vote_map.get((poll.id, checkin_id)) if checked_in else None
            polls.append({
                "id": poll.id,
                "name": poll.name,
                "vote": user_vote
            })

        result.append({
            "id": meeting.id,
            "start_time": to_timezone(meeting.start_time, tz).isoformat(),
            "end_time": to_timezone(meeting.end_time, tz).isoformat(),
            "meeting_code": meeting.meeting_code,
            "checked_in": checked_in,
            "polls": polls
        })

    return result
