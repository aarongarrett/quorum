"""Unit tests for meeting service."""
import pytest
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from app.services.meeting import create_meeting, get_meeting, delete_meeting
from app.db.models import Meeting


@pytest.mark.unit
class TestMeetingCreation:
    """Test meeting creation logic."""

    def test_create_meeting_success(self, db_session):
        """Should create meeting with unique code."""
        start_time = datetime.now(timezone.utc) + timedelta(hours=1)
        end_time = datetime.now(timezone.utc) + timedelta(hours=2)

        meeting_id, meeting_code = create_meeting(db_session, start_time, end_time)

        assert isinstance(meeting_id, int)
        assert isinstance(meeting_code, str)
        assert len(meeting_code) == 8  # Pronounceable code format

        # Verify in database
        meeting = db_session.query(Meeting).filter(Meeting.id == meeting_id).first()
        assert meeting is not None
        assert meeting.meeting_code == meeting_code

    def test_create_meeting_invalid_times(self, db_session):
        """End time before start time should raise ValueError."""
        start_time = datetime.now(timezone.utc) + timedelta(hours=2)
        end_time = datetime.now(timezone.utc) + timedelta(hours=1)

        with pytest.raises(ValueError, match="End time must be after start time"):
            create_meeting(db_session, start_time, end_time)

    def test_create_meeting_code_uniqueness(self, db_session):
        """Each meeting should get a unique code."""
        start_time = datetime.now(timezone.utc) + timedelta(hours=1)
        end_time = datetime.now(timezone.utc) + timedelta(hours=2)

        codes = []
        for _ in range(5):
            _, code = create_meeting(db_session, start_time, end_time)
            codes.append(code)

        assert len(set(codes)) == 5  # All unique


@pytest.mark.unit
class TestMeetingRetrieval:
    """Test meeting retrieval logic."""

    def test_get_meeting_success(self, db_session):
        """Should retrieve meeting with details."""
        tz = ZoneInfo("America/New_York")

        meeting = Meeting(
            start_time=datetime.now(timezone.utc) + timedelta(hours=1),
            end_time=datetime.now(timezone.utc) + timedelta(hours=2),
            meeting_code="TEST1234"
        )
        db_session.add(meeting)
        db_session.commit()
        db_session.refresh(meeting)

        result = get_meeting(db_session, meeting.id, tz)

        assert result is not None
        assert result["id"] == meeting.id
        assert result["meeting_code"] == "TEST1234"
        assert "start_time" in result
        assert "end_time" in result
        assert "polls" in result
        assert "checkins" in result

    def test_get_meeting_not_found(self, db_session):
        """Non-existent meeting should return None."""
        tz = ZoneInfo("America/New_York")
        result = get_meeting(db_session, 99999, tz)

        assert result is None


@pytest.mark.unit
class TestMeetingDeletion:
    """Test meeting deletion logic."""

    def test_delete_meeting_success(self, db_session):
        """Should delete meeting successfully."""
        meeting = Meeting(
            start_time=datetime.now(timezone.utc) + timedelta(hours=1),
            end_time=datetime.now(timezone.utc) + timedelta(hours=2),
            meeting_code="TEST1234"
        )
        db_session.add(meeting)
        db_session.commit()
        db_session.refresh(meeting)

        result = delete_meeting(db_session, meeting.id)

        assert result is True

        # Verify deleted
        deleted_meeting = db_session.query(Meeting).filter(Meeting.id == meeting.id).first()
        assert deleted_meeting is None

    def test_delete_meeting_not_found(self, db_session):
        """Deleting non-existent meeting should return False."""
        result = delete_meeting(db_session, 99999)

        assert result is False
