import io
import secrets
from datetime import datetime, timedelta
from typing import Any, Optional, Union

import qrcode
from qrcode.image.svg import SvgImage
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session

from app.models import Checkin, Election, ElectionVote, Meeting


def is_meeting_available(
    start_time: Union[datetime, str],
    end_time: Union[datetime, str],
    current_time: Optional[datetime] = None,
) -> bool:
    """Check if a meeting is currently available for check-in.

    Args:
        start_time: Meeting start time (datetime or ISO format string)
        end_time: Meeting end time (datetime or ISO format string)
        current_time: Optional current time for testing (defaults to now)

    Returns:
        bool: True if meeting is available for check-in
    """
    if current_time is None:
        current_time = datetime.now()

    # Convert string times to datetime objects if needed
    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time)
    if isinstance(end_time, str):
        end_time = datetime.fromisoformat(end_time)

    # Allow check-in 15 minutes before and 15 minutes after start
    checkin_start = start_time - timedelta(minutes=15)

    # Meeting is available if current time is within the check-in window
    # and before the meeting end time
    return checkin_start <= current_time <= end_time


def make_pronounceable(length: int = 6) -> str:
    """Generate a pronounceable token of the specified length

    The token alternates between consonants and vowels to make it easier to read and say.

    Args:
        length: The length of the token to generate

    Returns:
        str: A pronounceable token
    """
    consonants = "BCDFGHJKLMNPQRSTVWXYZ"
    vowels = "AEIOU"
    token = []
    for i in range(length):
        token.append(secrets.choice(vowels) if i % 2 else secrets.choice(consonants))
    return "".join(token)


def get_meetings(db: Session) -> list[dict[str, Any]]:
    """Retrieve all meetings with their details.

    Args:
        db: SQLAlchemy session

    Returns:
        list[dict[str, Any]]: List of meetings with their details
    """
    meetings = db.query(Meeting).order_by(Meeting.start_time.desc()).all()

    result = []
    for meeting in meetings:
        result.append(
            {
                "id": meeting.id,
                "start_time": meeting.start_time,
                "end_time": meeting.end_time,
                "meeting_code": meeting.meeting_code,
            }
        )

    return result


def get_available_meetings(db: Session) -> list[tuple[int, str, str]]:
    """Retrieve all available meetings with their check-in status.

    Args:
        db: SQLAlchemy session

    Returns:
        list[tuple[int, str, str]]: List of meetings where each tuple contains
            (meeting_id, start_time_isoformat, end_time_isoformat)
    """
    current_time = datetime.now()

    # Query all meetings ordered by start_time descending
    meetings = db.query(Meeting).order_by(Meeting.start_time.desc()).all()

    # Filter meetings that are currently available
    available_meetings = []
    for meeting in meetings:
        if is_meeting_available(meeting.start_time, meeting.end_time, current_time):
            available_meetings.append(
                (
                    meeting.id,
                    meeting.start_time.isoformat(),
                    meeting.end_time.isoformat(),
                )
            )

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

    def generate_meeting_code() -> str:
        """Generate a pronounceable meeting code."""
        return make_pronounceable(8)

    if end_time <= start_time:
        raise ValueError("End time must be after start time")

    # Ensure end time is within the same day
    if end_time.day > start_time.day:
        end_time = datetime.combine(
            start_time.date(), datetime.strptime("23:59", "%H:%M").time()
        )

    # Try to create a meeting with a unique code (retry once if code exists)
    for _ in range(2):
        meeting_code = generate_meeting_code()
        meeting = Meeting(
            start_time=start_time, end_time=end_time, meeting_code=meeting_code
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


def checkin(db: Session, meeting_id: int, meeting_code: str) -> tuple[str, bool]:
    """Process a meeting check-in.

    Args:
        db: SQLAlchemy session
        meeting_id: ID of the meeting to check into
        meeting_code: The meeting code to validate

    Returns:
        tuple: (vote_token, success) - The vote token if successful, error message if not,
              and a boolean indicating success
    """
    try:
        # Get the meeting with the given ID
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).one()

        # Verify the meeting code
        if meeting_code != meeting.meeting_code:
            return "Invalid meeting code", False

        # Check if the meeting is currently available for check-in
        if not is_meeting_available(meeting.start_time, meeting.end_time):
            return "Meeting is not available", False

        # Generate a unique vote token
        vote_token = make_pronounceable(8)

        # Create a new check-in record
        checkin = Checkin(
            meeting_id=meeting_id, vote_token=vote_token, timestamp=datetime.now()
        )

        db.add(checkin)
        db.commit()
        db.refresh(checkin)

        return vote_token, True

    except NoResultFound:
        # Meeting not found
        return "Meeting not found", False
    except IntegrityError:
        # If there's a duplicate token (very unlikely), try again
        db.rollback()
        return checkin(db, meeting_id, meeting_code)
    except Exception:
        db.rollback()
        raise


def vote_in_election(
    db: Session, meeting_id: int, election_id: int, vote_token: str, vote: str
) -> tuple[str, bool]:
    """Process a vote in an election.

    Args:
        db: SQLAlchemy session
        meeting_id: ID of the meeting
        election_id: ID of the election to vote in
        vote_token: Token from check-in
        vote: The vote to record

    Returns:
        Tuple[str, bool]: A tuple containing a message and success status
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
            return "Invalid election", False

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
            return "You have already voted in this election", False

        # Check if the token is valid for this meeting
        checkin = (
            db.query(Checkin)
            .filter(Checkin.meeting_id == meeting_id, Checkin.vote_token == vote_token)
            .first()
        )

        if not checkin:
            return "Invalid token for this meeting", False

        # Check if the meeting is currently available for voting
        if not is_meeting_available(meeting.start_time, meeting.end_time):
            return "Voting has ended", False

        # Record the vote
        vote_record = ElectionVote(
            election_id=election_id, vote_token=vote_token, vote=vote
        )

        db.add(vote_record)
        db.commit()
        return "Vote recorded successfully", True

    except NoResultFound:
        db.rollback()
        return "Meeting not found", False
    except IntegrityError as e:
        db.rollback()
        return "Failed to record vote: " + str(e), False
    except Exception as e:
        db.rollback()
        return "An error occurred while processing your vote: " + str(e), False


def generate_qr_code(data: str, svg=True) -> io.BytesIO:
    """Generate a QR code as a BytesIO object.

    Args:
        data: The data to encode in the QR code

    Returns:
        io.BytesIO: A BytesIO object containing the QR code image in SVG format
    """
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    # Create an in-memory image
    if svg:
        img = qr.make_image(
            image_factory=SvgImage, fill_color="black", back_color="white"
        )
    else:
        img = qr.make_image(fill_color="black", back_color="white")
    # Save to a bytes buffer
    buffer = io.BytesIO()
    img.save(buffer)
    buffer.seek(0)
    return buffer


def get_checkin_count(db: Session, meeting_id: int) -> int:
    """Get check-in count for the meeting_id.

    Args:
        db: SQLAlchemy session
        meeting_id: the meeting id

    Returns:
        int: the check-in count
    """
    return db.query(Checkin).filter(Checkin.meeting_id == meeting_id).count()


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


def get_meeting(db: Session, meeting_id: int) -> Optional[dict[str, Any]]:
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

    result = {
        "id": meeting.id,
        "start_time": meeting.start_time,
        "end_time": meeting.end_time,
        "meeting_code": meeting.meeting_code,
        "checkins": get_checkin_count(db, meeting.id),
        "elections": [],
    }

    # Get elections for this meeting
    elections = get_elections(db, meeting.id)
    for election_id, name in elections.items():
        result["elections"].append(get_election(db, election_id))

    return result


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
