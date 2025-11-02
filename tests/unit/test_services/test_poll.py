"""Unit tests for poll service."""
import pytest
from datetime import datetime, timezone, timedelta

from app.services.poll import create_poll, get_vote_counts, delete_poll
from app.db.models import Meeting, Poll, PollVote, Checkin


@pytest.mark.unit
class TestPollCreation:
    """Test poll creation."""

    def test_create_poll_success(self, db_session):
        """Successfully create a poll."""
        # Create a meeting first
        meeting = Meeting(
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(hours=1),
            meeting_code="TEST123"
        )
        db_session.add(meeting)
        db_session.commit()

        # Create poll
        poll_id = create_poll(db_session, meeting.id, "Test Poll")

        # Verify poll was created
        poll = db_session.query(Poll).filter(Poll.id == poll_id).first()
        assert poll is not None
        assert poll.name == "Test Poll"
        assert poll.meeting_id == meeting.id

    def test_create_poll_empty_name(self, db_session):
        """Creating poll with empty name should raise ValueError."""
        # Create a meeting first
        meeting = Meeting(
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(hours=1),
            meeting_code="TEST123"
        )
        db_session.add(meeting)
        db_session.commit()

        # Try to create poll with empty name
        with pytest.raises(ValueError, match="Poll name cannot be empty"):
            create_poll(db_session, meeting.id, "")

    def test_create_poll_meeting_not_found(self, db_session):
        """Creating poll for non-existent meeting should raise ValueError."""
        with pytest.raises(ValueError, match="Meeting not found"):
            create_poll(db_session, 99999, "Test Poll")

    def test_create_poll_duplicate_name(self, db_session):
        """Creating poll with duplicate name should raise ValueError."""
        # Create a meeting first
        meeting = Meeting(
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(hours=1),
            meeting_code="TEST123"
        )
        db_session.add(meeting)
        db_session.commit()

        # Create first poll
        create_poll(db_session, meeting.id, "Test Poll")

        # Try to create duplicate poll
        with pytest.raises(ValueError, match="Poll with this name already exists"):
            create_poll(db_session, meeting.id, "Test Poll")


@pytest.mark.unit
class TestVoteCounts:
    """Test vote counting."""

    def test_get_vote_counts_no_votes(self, db_session):
        """Get vote counts for poll with no votes."""
        # Create meeting and poll
        meeting = Meeting(
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(hours=1),
            meeting_code="TEST123"
        )
        db_session.add(meeting)
        db_session.commit()

        poll = Poll(meeting_id=meeting.id, name="Test Poll")
        db_session.add(poll)
        db_session.commit()

        # Get vote counts
        counts = get_vote_counts(db_session, poll.id)

        # Should return all zeros
        assert counts == {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0, 'F': 0, 'G': 0, 'H': 0}

    def test_get_vote_counts_with_votes(self, db_session):
        """Get vote counts for poll with votes."""
        # Create meeting and poll
        meeting = Meeting(
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(hours=1),
            meeting_code="TEST123"
        )
        db_session.add(meeting)
        db_session.commit()

        poll = Poll(meeting_id=meeting.id, name="Test Poll")
        db_session.add(poll)
        db_session.commit()

        # Create checkins and votes
        checkin1 = Checkin(meeting_id=meeting.id, token_lookup_key="a" * 64)
        checkin2 = Checkin(meeting_id=meeting.id, token_lookup_key="b" * 64)
        checkin3 = Checkin(meeting_id=meeting.id, token_lookup_key="c" * 64)
        db_session.add_all([checkin1, checkin2, checkin3])
        db_session.commit()

        vote1 = PollVote(poll_id=poll.id, checkin_id=checkin1.id, vote="A")
        vote2 = PollVote(poll_id=poll.id, checkin_id=checkin2.id, vote="A")
        vote3 = PollVote(poll_id=poll.id, checkin_id=checkin3.id, vote="B")
        db_session.add_all([vote1, vote2, vote3])
        db_session.commit()

        # Get vote counts
        counts = get_vote_counts(db_session, poll.id)

        # Should have correct counts
        assert counts['A'] == 2
        assert counts['B'] == 1
        assert counts['C'] == 0


@pytest.mark.unit
class TestPollDeletion:
    """Test poll deletion."""

    def test_delete_poll_success(self, db_session):
        """Successfully delete a poll."""
        # Create meeting and poll
        meeting = Meeting(
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(hours=1),
            meeting_code="TEST123"
        )
        db_session.add(meeting)
        db_session.commit()

        poll = Poll(meeting_id=meeting.id, name="Test Poll")
        db_session.add(poll)
        db_session.commit()

        # Create checkin and vote
        checkin = Checkin(meeting_id=meeting.id, token_lookup_key="d" * 64)
        db_session.add(checkin)
        db_session.commit()

        vote = PollVote(poll_id=poll.id, checkin_id=checkin.id, vote="A")
        db_session.add(vote)
        db_session.commit()

        poll_id = poll.id

        # Delete poll
        delete_poll(db_session, meeting.id, poll_id)

        # Verify poll and votes are deleted
        assert db_session.query(Poll).filter(Poll.id == poll_id).first() is None
        assert db_session.query(PollVote).filter(PollVote.poll_id == poll_id).first() is None

    def test_delete_poll_not_found(self, db_session):
        """Deleting non-existent poll should raise ValueError."""
        # Create a meeting first
        meeting = Meeting(
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(hours=1),
            meeting_code="TEST123"
        )
        db_session.add(meeting)
        db_session.commit()

        # Try to delete non-existent poll
        with pytest.raises(ValueError, match="Poll not found"):
            delete_poll(db_session, meeting.id, 99999)

    def test_delete_poll_wrong_meeting(self, db_session):
        """Deleting poll with wrong meeting ID should raise ValueError."""
        # Create two meetings
        meeting1 = Meeting(
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(hours=1),
            meeting_code="TEST123"
        )
        meeting2 = Meeting(
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(hours=1),
            meeting_code="TEST456"
        )
        db_session.add_all([meeting1, meeting2])
        db_session.commit()

        # Create poll in meeting1
        poll = Poll(meeting_id=meeting1.id, name="Test Poll")
        db_session.add(poll)
        db_session.commit()

        # Try to delete poll using meeting2's ID
        with pytest.raises(ValueError, match="Poll not found"):
            delete_poll(db_session, meeting2.id, poll.id)
