"""Poll business logic."""
from typing import Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models import Meeting, Poll, PollVote
from app.core.constants import VOTE_OPTIONS


def create_poll(db: Session, meeting_id: int, name: str) -> int:
    """Create a new poll."""
    if not name:
        raise ValueError("Poll name cannot be empty")

    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise ValueError("Meeting not found")

    # Check for duplicate poll name in meeting
    existing = db.query(Poll).filter(
        Poll.meeting_id == meeting_id,
        Poll.name == name
    ).first()

    if existing:
        raise ValueError("Poll with this name already exists")

    poll = Poll(meeting_id=meeting_id, name=name)
    db.add(poll)
    db.commit()
    db.refresh(poll)

    return poll.id


def get_vote_counts_bulk(db: Session, poll_ids: List[int] = None) -> Dict[int, Dict[str, int]]:
    """
    Get vote counts for multiple polls efficiently.

    Args:
        db: Database session
        poll_ids: Optional list of poll IDs to filter. If None, gets all polls.

    Returns:
        Dict mapping poll_id -> {vote_option -> count}
        Each poll's vote counts are initialized with all options set to 0.
    """
    # Query all vote data for the specified polls
    query = db.query(
        PollVote.poll_id,
        PollVote.vote,
        func.count()
    ).group_by(PollVote.poll_id, PollVote.vote)

    if poll_ids:
        query = query.filter(PollVote.poll_id.in_(poll_ids))

    vote_data = query.all()

    # Build vote counts dictionary
    vote_counts = {}
    for poll_id, vote, count in vote_data:
        if poll_id not in vote_counts:
            vote_counts[poll_id] = {option: 0 for option in VOTE_OPTIONS}
        vote_counts[poll_id][vote] = count

    return vote_counts


def get_vote_counts(db: Session, poll_id: int) -> Dict[str, int]:
    """
    Get vote counts for a single poll.

    Args:
        db: Database session
        poll_id: Poll ID

    Returns:
        Dict mapping vote option -> count (all options initialized to 0)
    """
    bulk_result = get_vote_counts_bulk(db, [poll_id])
    return bulk_result.get(poll_id, {option: 0 for option in VOTE_OPTIONS})


def delete_poll(db: Session, meeting_id: int, poll_id: int) -> None:
    """Delete a poll and all associated votes."""
    poll = db.query(Poll).filter(
        Poll.id == poll_id,
        Poll.meeting_id == meeting_id
    ).first()

    if not poll:
        raise ValueError("Poll not found")

    # Delete all votes associated with this poll
    db.query(PollVote).filter(PollVote.poll_id == poll_id).delete()

    # Delete the poll
    db.delete(poll)
    db.commit()
