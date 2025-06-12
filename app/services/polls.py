from typing import Any, Optional

from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session

from app.models import Checkin, Meeting, Poll, PollVote
from app.services.utils import is_available


def create_poll(db: Session, meeting_id: int, poll_name: str) -> int:
    """Create a new poll in the database.

    Args:
        db: SQLAlchemy session
        meeting_id: ID of the meeting this poll belongs to
        poll_name: Name of the poll

    Returns:
        int: ID of the created poll

    Raises:
        ValueError if poll name is empty or meeting_id does not exist
    """
    # Disallow empty poll names
    if len(poll_name) == 0:
        raise ValueError("Poll name cannot be empty")

    try:
        # Verify the meeting exists
        db.query(Meeting).filter(Meeting.id == meeting_id).one()

        # Check if an poll with the same name already exists in this meeting
        existing_poll = (
            db.query(Poll)
            .filter(Poll.meeting_id == meeting_id, Poll.name == poll_name)
            .first()
        )

        if existing_poll is not None:
            raise ValueError("A poll with this name already exists in this meeting")

        poll = Poll(meeting_id=meeting_id, name=poll_name)

        db.add(poll)
        db.commit()
        db.refresh(poll)

        return poll.id

    except NoResultFound:
        db.rollback()
        raise ValueError("Meeting does not exist")
    except Exception:
        db.rollback()
        raise


def delete_poll(db: Session, meeting_id: int, poll_id: int) -> bool:
    """Delete an poll and all its associated votes from the database.

    Args:
        db: SQLAlchemy session
        meeting_id: ID of the meeting this poll belongs to
        poll_id: ID of the poll to delete

    Returns:
        bool: True if poll was deleted, False if no poll was found
    """
    try:
        # This will raise NoResultFound if poll doesn't exist
        poll = (
            db.query(Poll)
            .filter(Poll.id == poll_id, Poll.meeting_id == meeting_id)
            .one()
        )

        # Cascade delete will handle related votes due to the
        # cascade="all, delete-orphan" in the relationship definition
        db.delete(poll)
        db.commit()
        return True

    except NoResultFound:
        db.rollback()
        return False
    except Exception:
        db.rollback()
        raise


def get_polls(db: Session, meeting_id: int) -> dict[int, str]:
    """Retrieve all polls for a specific meeting.

    Args:
        db: SQLAlchemy session
        meeting_id: ID of the meeting to get polls for

    Returns:
        Dict[int, str]: A dictionary mapping poll IDs to poll names
    """
    polls = (
        db.query(Poll.id, Poll.name)
        .filter(Poll.meeting_id == meeting_id)
        .order_by(Poll.id)
        .all()
    )

    return {poll_id: name for poll_id, name in polls}


def get_poll(db: Session, poll_id: int) -> Optional[dict[str, Any]]:
    poll = db.query(Poll).filter(Poll.id == poll_id).first()

    if not poll:
        return None

    # Unpack poll data
    poll_id = poll.id
    name = poll.name
    meeting_id = poll.meeting_id
    votes = get_vote_counts(db, poll_id)

    return {
        "id": poll_id,
        "name": name,
        "meeting_id": meeting_id,
        "total_votes": sum([votes[k] for k in votes]),
        "votes": votes,
    }


def vote_in_poll(
    db: Session, meeting_id: int, poll_id: int, vote_token: str, vote: str
) -> None:
    """Process a vote in an poll.

    Args:
        db: SQLAlchemy session
        meeting_id: ID of the meeting
        poll_id: ID of the poll to vote in
        vote_token: Token from check-in
        vote: The vote to record

    Raises:
        ValueError if poll is invalid,
                   user has already voted in this poll,
                   token is invalid for this meeting,
                   or meeting is not available
    """
    try:
        # Check if the meeting exists
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).one()

        # Check if the poll exists and belongs to the meeting
        poll = (
            db.query(Poll)
            .filter(Poll.id == poll_id, Poll.meeting_id == meeting_id)
            .first()
        )

        if not poll:
            raise ValueError("Invalid poll")

        # Check if user has already voted in this poll
        existing_vote = (
            db.query(PollVote)
            .filter(
                PollVote.poll_id == poll_id,
                PollVote.vote_token == vote_token,
            )
            .first()
        )

        if existing_vote is not None:
            raise ValueError("You have already voted in this poll")

        # Check if the token is valid for this meeting
        checkin = (
            db.query(Checkin)
            .filter(Checkin.meeting_id == meeting_id, Checkin.vote_token == vote_token)
            .first()
        )

        if not checkin:
            raise ValueError("Invalid token for this meeting")

        # Check if the meeting is currently available for voting
        if not is_available(meeting.start_time, meeting.end_time):
            raise ValueError("Voting has ended")

        # Record the vote
        vote_record = PollVote(poll_id=poll_id, vote_token=vote_token, vote=vote)

        db.add(vote_record)
        db.commit()
        return None

    except NoResultFound:
        db.rollback()
        raise ValueError("Meeting not found")
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Failed to record vote: " + str(e))
    except Exception as e:
        db.rollback()
        raise ValueError("An error occurred while processing your vote: " + str(e))


def get_vote_counts(db: Session, poll_id: int) -> dict[str, int]:
    """Get vote counts for the specified poll.

    Args:
        db: SQLAlchemy session
        poll_id: the poll id

    Returns:
        dict[str, int]: A dictionary of the vote counts for each option (A-H)
    """
    from sqlalchemy import func

    # Initialize result with all possible votes set to 0
    result = {letter: 0 for letter in "ABCDEFGH"}

    # Get the counts for each vote type
    vote_counts = (
        db.query(PollVote.vote, func.count(PollVote.vote))
        .filter(PollVote.poll_id == poll_id, PollVote.vote.isnot(None))
        .group_by(PollVote.vote)
        .all()
    )

    # Update the result with actual counts
    for vote, count in vote_counts:
        if vote in result:
            result[vote] = count

    return result


def get_user_votes(
    db: Session, meeting_id: int, token: str
) -> dict[int, dict[str, str]]:
    """Retrieve all votes for a specific meeting.

    Args:
        db: SQLAlchemy session
        meeting_id: ID of the meeting to get votes for
        token: The vote token to filter by

    Returns:
        dict[int, dict[str, str]]: A dictionary of poll IDs to names/votes.
        Returns an empty dict if no votes exist for the given token.
    """
    # First verify the token has checked in to the meeting
    checkin_exists = (
        db.query(Checkin)
        .filter(Checkin.meeting_id == meeting_id, Checkin.vote_token == token)
        .first()
    )

    if not checkin_exists:
        return {}

    # Get all polls for this meeting with their votes for the given token
    polls = (
        db.query(Poll.id, Poll.name, PollVote.vote)
        .join(
            PollVote,
            (PollVote.poll_id == Poll.id) & (PollVote.vote_token == token),
        )
        .filter(Poll.meeting_id == meeting_id)
        .all()
    )

    return {poll_id: {"name": name, "vote": vote} for poll_id, name, vote in polls}
