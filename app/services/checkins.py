from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session

from app.models import Checkin, Meeting
from app.services.utils import is_available, make_pronounceable


def checkin(db: Session, meeting_id: int, meeting_code: str) -> str:
    """Process a meeting check-in.

    Args:
        db: SQLAlchemy session
        meeting_id: ID of the meeting to check into
        meeting_code: The meeting code to validate

    Returns:
        str: vote_token - The vote token

    Raises:
        ValueError if meeting ID does not exist,
                   meeting code is invalid,
                   or meeting is not available
    """
    try:
        # Get the meeting with the given ID
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).one()

        # Verify the meeting code
        if meeting_code != meeting.meeting_code:
            raise ValueError("Invalid meeting code")

        # Check if the meeting is currently available for check-in
        if not is_available(meeting.start_time, meeting.end_time):
            raise ValueError("Meeting is not available")

        # Generate a unique vote token
        vote_token = make_pronounceable()

        # Create a new check-in record
        checkin = Checkin(
            meeting_id=meeting_id,
            vote_token=vote_token,
            timestamp=datetime.now(timezone.utc),
        )

        db.add(checkin)
        db.commit()
        db.refresh(checkin)

        return vote_token

    except NoResultFound:
        # Meeting not found
        raise ValueError("Meeting not found")
    except IntegrityError:
        # If there's a duplicate token (very unlikely), try again
        db.rollback()
        return checkin(db, meeting_id, meeting_code)
    except Exception:
        db.rollback()
        raise
