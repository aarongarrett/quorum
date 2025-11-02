"""Unit tests for check-in service."""
import pytest
from datetime import datetime, timezone, timedelta
from app.services.checkin import checkin
from app.db.models import Meeting, Checkin
from app.core.security import generate_vote_token


@pytest.mark.unit
class TestCheckin:
    """Test check-in business logic."""

    def test_checkin_success(self, db_session):
        """Successful check-in should return token."""
        # Create a meeting
        meeting = Meeting(
            start_time=datetime.now(timezone.utc) - timedelta(minutes=5),
            end_time=datetime.now(timezone.utc) + timedelta(hours=1),
            meeting_code="TEST1234"
        )
        db_session.add(meeting)
        db_session.commit()
        db_session.refresh(meeting)

        # Check in
        token = checkin(db_session, meeting.id, "TEST1234")

        assert isinstance(token, str)
        assert len(token) > 40

        # Verify checkin was created
        checkin_record = db_session.query(Checkin).filter(
            Checkin.meeting_id == meeting.id
        ).first()
        assert checkin_record is not None

    def test_checkin_invalid_meeting_id(self, db_session):
        """Invalid meeting ID should raise ValueError."""
        with pytest.raises(ValueError, match="Meeting not found"):
            checkin(db_session, 99999, "TEST1234")

    def test_checkin_invalid_code(self, db_session):
        """Invalid meeting code should raise ValueError."""
        meeting = Meeting(
            start_time=datetime.now(timezone.utc) - timedelta(minutes=5),
            end_time=datetime.now(timezone.utc) + timedelta(hours=1),
            meeting_code="TEST1234"
        )
        db_session.add(meeting)
        db_session.commit()
        db_session.refresh(meeting)

        with pytest.raises(ValueError, match="Invalid meeting code"):
            checkin(db_session, meeting.id, "WRONG123")

    def test_checkin_meeting_not_available(self, db_session):
        """Check-in to unavailable meeting should fail."""
        # Meeting in the past
        meeting = Meeting(
            start_time=datetime.now(timezone.utc) - timedelta(hours=3),
            end_time=datetime.now(timezone.utc) - timedelta(hours=2),
            meeting_code="TEST1234"
        )
        db_session.add(meeting)
        db_session.commit()
        db_session.refresh(meeting)

        with pytest.raises(ValueError, match="Meeting is not available"):
            checkin(db_session, meeting.id, "TEST1234")

    def test_checkin_idempotent_with_existing_token(self, db_session):
        """Checking in with existing valid token should return same token."""
        # Create meeting
        meeting = Meeting(
            start_time=datetime.now(timezone.utc) - timedelta(minutes=5),
            end_time=datetime.now(timezone.utc) + timedelta(hours=1),
            meeting_code="TEST1234"
        )
        db_session.add(meeting)
        db_session.commit()
        db_session.refresh(meeting)

        # First check-in
        token1 = checkin(db_session, meeting.id, "TEST1234")

        # Second check-in with same token (idempotent)
        token2 = checkin(db_session, meeting.id, "TEST1234", existing_token=token1)

        assert token1 == token2

        # Verify only one checkin record
        checkin_count = db_session.query(Checkin).filter(
            Checkin.meeting_id == meeting.id
        ).count()
        assert checkin_count == 1

    def test_checkin_new_user_with_invalid_token(self, db_session):
        """Invalid existing token should create new checkin."""
        meeting = Meeting(
            start_time=datetime.now(timezone.utc) - timedelta(minutes=5),
            end_time=datetime.now(timezone.utc) + timedelta(hours=1),
            meeting_code="TEST1234"
        )
        db_session.add(meeting)
        db_session.commit()
        db_session.refresh(meeting)

        # Try to check in with a fake token
        fake_token = generate_vote_token()
        new_token = checkin(db_session, meeting.id, "TEST1234", existing_token=fake_token)

        # Should get a different token
        assert new_token != fake_token

        # Should have one checkin
        checkin_count = db_session.query(Checkin).filter(
            Checkin.meeting_id == meeting.id
        ).count()
        assert checkin_count == 1
