from typing import Any, Optional

from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session

from app.models import Checkin, Election, ElectionVote, Meeting
from app.services.utils import is_available


def create_election(db: Session, meeting_id: int, election_name: str) -> int:
    """Create a new election in the database.

    Args:
        db: SQLAlchemy session
        meeting_id: ID of the meeting this election belongs to
        election_name: Name of the election

    Returns:
        int: ID of the created election

    Raises:
        ValueError if election name is empty or meeting_id does not exist
    """
    # Disallow empty election names
    if len(election_name) == 0:
        raise ValueError("Election name cannot be empty")

    try:
        # Verify the meeting exists
        db.query(Meeting).filter(Meeting.id == meeting_id).one()

        # Check if an election with the same name already exists in this meeting
        existing_election = (
            db.query(Election)
            .filter(Election.meeting_id == meeting_id, Election.name == election_name)
            .first()
        )

        if existing_election is not None:
            raise ValueError(
                "An election with this name already exists in this meeting"
            )

        election = Election(meeting_id=meeting_id, name=election_name)

        db.add(election)
        db.commit()
        db.refresh(election)

        return election.id

    except NoResultFound:
        db.rollback()
        raise ValueError("Meeting does not exist")
    except Exception:
        db.rollback()
        raise


def delete_election(db: Session, meeting_id: int, election_id: int) -> bool:
    """Delete an election and all its associated votes from the database.

    Args:
        db: SQLAlchemy session
        meeting_id: ID of the meeting this election belongs to
        election_id: ID of the election to delete

    Returns:
        bool: True if election was deleted, False if no election was found
    """
    try:
        # This will raise NoResultFound if election doesn't exist
        election = (
            db.query(Election)
            .filter(Election.id == election_id, Election.meeting_id == meeting_id)
            .one()
        )

        # Cascade delete will handle related votes due to the cascade="all, delete-orphan"
        # in the relationship definition
        db.delete(election)
        db.commit()
        return True

    except NoResultFound:
        db.rollback()
        return False
    except Exception:
        db.rollback()
        raise


def get_elections(db: Session, meeting_id: int) -> dict[int, str]:
    """Retrieve all elections for a specific meeting.

    Args:
        db: SQLAlchemy session
        meeting_id: ID of the meeting to get elections for

    Returns:
        Dict[int, str]: A dictionary mapping election IDs to election names
    """
    elections = (
        db.query(Election.id, Election.name)
        .filter(Election.meeting_id == meeting_id)
        .order_by(Election.id)
        .all()
    )

    return {election_id: name for election_id, name in elections}


def get_election(db: Session, election_id: int) -> Optional[dict[str, Any]]:
    election = db.query(Election).filter(Election.id == election_id).first()

    if not election:
        return None

    # Unpack election data
    election_id = election.id
    name = election.name
    meeting_id = election.meeting_id
    votes = get_vote_counts(db, election_id)

    return {
        "id": election_id,
        "name": name,
        "meeting_id": meeting_id,
        "total_votes": sum([votes[k] for k in votes]),
        "votes": votes,
    }


def vote_in_election(
    db: Session, meeting_id: int, election_id: int, vote_token: str, vote: str
) -> None:
    """Process a vote in an election.

    Args:
        db: SQLAlchemy session
        meeting_id: ID of the meeting
        election_id: ID of the election to vote in
        vote_token: Token from check-in
        vote: The vote to record

    Raises:
        ValueError if election is invalid,
                   user has already voted in this election,
                   token is invalid for this meeting,
                   or meeting is not available
    """
    try:
        # Check if the meeting exists
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).one()

        # Check if the election exists and belongs to the meeting
        election = (
            db.query(Election)
            .filter(Election.id == election_id, Election.meeting_id == meeting_id)
            .first()
        )

        if not election:
            raise ValueError("Invalid election")

        # Check if user has already voted in this election
        existing_vote = (
            db.query(ElectionVote)
            .filter(
                ElectionVote.election_id == election_id,
                ElectionVote.vote_token == vote_token,
            )
            .first()
        )

        if existing_vote is not None:
            raise ValueError("You have already voted in this election")

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
        vote_record = ElectionVote(
            election_id=election_id, vote_token=vote_token, vote=vote
        )

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


def get_vote_counts(db: Session, election_id: int) -> dict[str, int]:
    """Get vote counts for the specified election.

    Args:
        db: SQLAlchemy session
        election_id: the election id

    Returns:
        dict[str, int]: A dictionary of the vote counts for each option (A-H)
    """
    from sqlalchemy import func

    # Initialize result with all possible votes set to 0
    result = {letter: 0 for letter in "ABCDEFGH"}

    # Get the counts for each vote type
    vote_counts = (
        db.query(ElectionVote.vote, func.count(ElectionVote.vote))
        .filter(ElectionVote.election_id == election_id, ElectionVote.vote.isnot(None))
        .group_by(ElectionVote.vote)
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
        dict[int, dict[str, str]]: A dictionary mapping election IDs to names and votes.
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

    # Get all elections for this meeting with their votes for the given token
    elections = (
        db.query(Election.id, Election.name, ElectionVote.vote)
        .join(
            ElectionVote,
            (ElectionVote.election_id == Election.id)
            & (ElectionVote.vote_token == token),
        )
        .filter(Election.meeting_id == meeting_id)
        .all()
    )

    return {
        election_id: {"name": name, "vote": vote}
        for election_id, name, vote in elections
    }
