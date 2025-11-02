"""Check-in business logic."""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.models import Meeting, Checkin
from app.core.security import generate_vote_token, create_token_lookup_key
from app.core.utils import is_available
from app.services.utils import get_checkin_by_token


def checkin(db: Session, meeting_id: int, meeting_code: str, existing_token: Optional[str] = None, _retry_count: int = 0) -> str:
    """
    Check in to a meeting. If existing_token is provided and valid, return it.
    Otherwise create new checkin and return new token.

    Args:
        _retry_count: Internal parameter to track retry attempts (max 5)
    """
    if _retry_count > 5:
        raise ValueError("Failed to generate unique token after multiple attempts. Please try again.")

    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise ValueError("Meeting not found")

    if meeting.meeting_code != meeting_code:
        raise ValueError("Invalid meeting code")

    if not is_available(meeting.start_time, meeting.end_time):
        raise ValueError("Meeting is not available")

    # If token provided, check if it's valid for this meeting (O(1) indexed lookup)
    if existing_token:
        checkin_record = get_checkin_by_token(db, meeting_id, existing_token)
        if checkin_record:
            # Token is valid, return same token (idempotent)
            return existing_token

    # Create new checkin
    token = generate_vote_token()
    token_key = create_token_lookup_key(token)

    try:
        checkin_record = Checkin(
            meeting_id=meeting_id,
            token_lookup_key=token_key,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(checkin_record)
        db.commit()
        return token
    except IntegrityError:
        db.rollback()
        # Collision unlikely but possible, retry with counter
        return checkin(db, meeting_id, meeting_code, existing_token, _retry_count + 1)
