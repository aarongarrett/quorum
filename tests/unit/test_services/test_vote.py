"""Unit tests for vote service."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from app.services.vote import vote_in_poll
from app.db.models import Meeting, Poll, PollVote


@pytest.mark.unit
class TestVoteInPoll:
    """Test vote_in_poll function."""

    @patch('app.services.vote.get_checkin_by_token')
    def test_duplicate_vote_raises_value_error(self, mock_get_checkin):
        """Test that IntegrityError for duplicate vote is converted to ValueError (issue #1.1)."""
        # Create mock database session
        mock_db = Mock()

        # Create mock meeting
        mock_meeting = Mock(spec=Meeting)
        mock_meeting.id = 1
        mock_meeting.start_time = datetime.now(timezone.utc)
        mock_meeting.end_time = datetime(2099, 12, 31, tzinfo=timezone.utc)

        # Create mock poll
        mock_poll = Mock(spec=Poll)
        mock_poll.id = 1
        mock_poll.meeting_id = 1
        mock_poll.question = "Test question"
        mock_poll.created_at = datetime.now(timezone.utc)

        # Create mock checkin
        mock_checkin = Mock()
        mock_checkin.id = 1
        mock_checkin.meeting_id = 1

        # Mock get_checkin_by_token to return the mock checkin
        mock_get_checkin.return_value = mock_checkin

        # Mock query chain for meeting
        mock_meeting_query = Mock()
        mock_meeting_query.first.return_value = mock_meeting
        mock_meeting_query.filter.return_value = mock_meeting_query

        # Mock query chain for poll
        mock_poll_query = Mock()
        mock_poll_query.first.return_value = mock_poll
        mock_poll_query.filter.return_value = mock_poll_query

        # Mock query chain for existing vote check (should return None - no existing vote)
        mock_existing_vote_query = Mock()
        mock_existing_vote_query.first.return_value = None
        mock_existing_vote_query.filter.return_value = mock_existing_vote_query

        # Setup query to return appropriate mocks
        def query_side_effect(model):
            if model == Meeting:
                return mock_meeting_query
            elif model == Poll:
                return mock_poll_query
            elif model == PollVote:
                return mock_existing_vote_query
            else:
                return Mock()

        mock_db.query.side_effect = query_side_effect

        # Create a mock IntegrityError with constraint violation
        mock_orig_error = Exception("duplicate key value violates unique constraint \"uq_poll_checkin\"")
        integrity_error = IntegrityError("statement", {}, mock_orig_error)

        # Mock commit to raise IntegrityError (simulating duplicate vote)
        mock_db.commit.side_effect = integrity_error

        # Verify that ValueError is raised with the correct message
        with pytest.raises(ValueError, match="You have already voted in this poll"):
            vote_in_poll(mock_db, meeting_id=1, poll_id=1, token="test_token", vote="yes")

        # Verify rollback was called
        mock_db.rollback.assert_called_once()

    @patch('app.services.vote.get_checkin_by_token')
    def test_duplicate_vote_postgres_constraint_name(self, mock_get_checkin):
        """Test duplicate vote detection with PostgreSQL constraint name."""
        mock_db = Mock()

        # Setup mocks (similar to above)
        mock_meeting = Mock(spec=Meeting)
        mock_meeting.id = 1
        mock_meeting.start_time = datetime.now(timezone.utc)
        mock_meeting.end_time = datetime(2099, 12, 31, tzinfo=timezone.utc)

        mock_poll = Mock(spec=Poll)
        mock_poll.id = 1
        mock_poll.meeting_id = 1
        mock_poll.created_at = datetime.now(timezone.utc)

        mock_checkin = Mock()
        mock_checkin.id = 1
        mock_checkin.meeting_id = 1

        # Mock get_checkin_by_token
        mock_get_checkin.return_value = mock_checkin

        mock_meeting_query = Mock()
        mock_meeting_query.first.return_value = mock_meeting
        mock_meeting_query.filter.return_value = mock_meeting_query

        mock_poll_query = Mock()
        mock_poll_query.first.return_value = mock_poll
        mock_poll_query.filter.return_value = mock_poll_query

        # Mock query chain for existing vote check (should return None - no existing vote)
        mock_existing_vote_query = Mock()
        mock_existing_vote_query.first.return_value = None
        mock_existing_vote_query.filter.return_value = mock_existing_vote_query

        def query_side_effect(model):
            if model == Meeting:
                return mock_meeting_query
            elif model == Poll:
                return mock_poll_query
            elif model == PollVote:
                return mock_existing_vote_query
            else:
                return Mock()

        mock_db.query.side_effect = query_side_effect

        # Simulate PostgreSQL constraint violation with generic column names
        mock_orig_error = Exception("UNIQUE constraint failed: poll_vote.poll_id, poll_vote.checkin_id")
        integrity_error = IntegrityError("statement", {}, mock_orig_error)
        mock_db.commit.side_effect = integrity_error

        # Should still raise ValueError
        with pytest.raises(ValueError, match="You have already voted in this poll"):
            vote_in_poll(mock_db, meeting_id=1, poll_id=1, token="test_token", vote="yes")

        mock_db.rollback.assert_called_once()

    @patch('app.services.vote.get_checkin_by_token')
    def test_other_integrity_error_propagates(self, mock_get_checkin):
        """Test that other IntegrityErrors are not caught and converted."""
        mock_db = Mock()

        # Setup mocks
        mock_meeting = Mock(spec=Meeting)
        mock_meeting.id = 1
        mock_meeting.start_time = datetime.now(timezone.utc)
        mock_meeting.end_time = datetime(2099, 12, 31, tzinfo=timezone.utc)

        mock_poll = Mock(spec=Poll)
        mock_poll.id = 1
        mock_poll.meeting_id = 1
        mock_poll.created_at = datetime.now(timezone.utc)

        mock_checkin = Mock()
        mock_checkin.id = 1
        mock_checkin.meeting_id = 1

        # Mock get_checkin_by_token
        mock_get_checkin.return_value = mock_checkin

        mock_meeting_query = Mock()
        mock_meeting_query.first.return_value = mock_meeting
        mock_meeting_query.filter.return_value = mock_meeting_query

        mock_poll_query = Mock()
        mock_poll_query.first.return_value = mock_poll
        mock_poll_query.filter.return_value = mock_poll_query

        # Mock query chain for existing vote check (should return None - no existing vote)
        mock_existing_vote_query = Mock()
        mock_existing_vote_query.first.return_value = None
        mock_existing_vote_query.filter.return_value = mock_existing_vote_query

        def query_side_effect(model):
            if model == Meeting:
                return mock_meeting_query
            elif model == Poll:
                return mock_poll_query
            elif model == PollVote:
                return mock_existing_vote_query
            else:
                return Mock()

        mock_db.query.side_effect = query_side_effect

        # Simulate a DIFFERENT integrity error (not duplicate vote)
        mock_orig_error = Exception("FOREIGN KEY constraint failed")
        integrity_error = IntegrityError("statement", {}, mock_orig_error)
        mock_db.commit.side_effect = integrity_error

        # Should propagate the IntegrityError, not convert to ValueError
        with pytest.raises(IntegrityError):
            vote_in_poll(mock_db, meeting_id=1, poll_id=1, token="test_token", vote="yes")

        mock_db.rollback.assert_called_once()
