"""Shared utilities for service layer."""
from typing import Optional
from sqlalchemy.orm import Session

from app.db.models import Checkin
from app.core.security import create_token_lookup_key


def get_checkin_by_token(
    db: Session,
    meeting_id: int,
    token: str
) -> Optional[Checkin]:
    """
    Get checkin record by token for a specific meeting.

    Uses O(1) indexed lookup via HMAC-SHA256 token key.

    Args:
        db: Database session
        meeting_id: Meeting ID to look up
        token: User's check-in token

    Returns:
        Checkin record if found, None otherwise
    """
    token_key = create_token_lookup_key(token)
    return db.query(Checkin).filter(
        Checkin.meeting_id == meeting_id,
        Checkin.token_lookup_key == token_key
    ).first()
