"""Vote business logic."""
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.db.models import Meeting, Poll, PollVote
from app.core.utils import is_available
from app.services.utils import get_checkin_by_token


def vote_in_poll(db: Session, meeting_id: int, poll_id: int, token: str, vote: str) -> None:
    """Cast a vote in a poll."""
    # Verify meeting exists and is available
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise ValueError("Meeting not found")

    if not is_available(meeting.start_time, meeting.end_time):
        raise ValueError("Voting has ended")

    # Verify poll exists and belongs to meeting
    poll = db.query(Poll).filter(
        Poll.id == poll_id,
        Poll.meeting_id == meeting_id
    ).first()
    if not poll:
        raise ValueError("Invalid poll")

    # Find checkin for this token (O(1) indexed lookup)
    checkin_record = get_checkin_by_token(db, meeting_id, token)
    if not checkin_record:
        raise ValueError("Invalid token for this meeting")

    checkin_id = checkin_record.id

    # Check if already voted
    existing_vote = db.query(PollVote).filter(
        PollVote.poll_id == poll_id,
        PollVote.checkin_id == checkin_id
    ).first()

    if existing_vote:
        raise ValueError("You have already voted in this poll")

    # Record vote
    vote_record = PollVote(
        poll_id=poll_id,
        checkin_id=checkin_id,
        vote=vote,
        timestamp=datetime.now(timezone.utc)
    )

    try:
        db.add(vote_record)
        db.commit()
    except Exception as e:
        db.rollback()
        # Handle race condition: duplicate vote due to concurrent requests
        # The unique constraint (poll_id, checkin_id) prevents duplicate votes
        if "uq_poll_checkin" in str(e) or "unique constraint" in str(e).lower():
            raise ValueError("You have already voted in this poll")
        # Re-raise other exceptions
        raise
