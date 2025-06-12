import importlib
from datetime import datetime, timedelta, timezone
from io import BytesIO

import pytest
from sqlalchemy.orm import Session

from app.models import Checkin, Meeting, Poll, PollVote
from app.services import (
    checkin,
    create_meeting,
    create_poll,
    delete_meeting,
    delete_poll,
    generate_qr_code,
    get_meeting,
    get_poll,
    get_polls,
    get_user_votes,
    get_vote_counts,
    is_available,
    vote_in_poll,
)


def decode_qr_png(img_buffer: BytesIO) -> str:
    """Helper function to decode QR code from image buffer."""
    # numpy is imported this way because of the internal mypy error
    numpy = importlib.import_module("numpy")
    import PIL
    import zxingcpp

    img = PIL.Image.open(img_buffer).convert("L")
    img_data = numpy.asarray(img)
    barcode = zxingcpp.read_barcode(img_data)
    return barcode.text


def test_generate_qr_code_basic():
    """Test basic QR code generation with a simple string."""
    test_data = "https://example.com/checkin/123/ABC123"
    svg_buffer = generate_qr_code(test_data)
    png_buffer = generate_qr_code(test_data, svg=False)

    # Verify we got a BytesIO object
    assert hasattr(svg_buffer, "read")
    assert hasattr(svg_buffer, "getvalue")

    # Verify the content is an SVG
    svg_content = svg_buffer.getvalue().decode("utf-8")
    assert svg_content.startswith("<?xml")
    assert "<svg" in svg_content
    assert 'xmlns="http://www.w3.org/2000/svg"' in svg_content

    # Decode the QR code and verify the data
    decoded_data = decode_qr_png(png_buffer)
    assert decoded_data is not None, "Failed to decode QR code"
    assert test_data in decoded_data, f"Expected '{test_data}' in QR code data"


def test_generate_qr_code_special_chars():
    """Test QR code generation with special characters in the data."""
    test_data = "https://example.com/checkin/123/ABC!@#$%^&*()_+-=[]{}|;:,<>?"
    svg_buffer = generate_qr_code(test_data)
    png_buffer = generate_qr_code(test_data, svg=False)

    # Verify we got a BytesIO object
    assert hasattr(svg_buffer, "read")
    assert hasattr(svg_buffer, "getvalue")

    # Verify we can generate the QR code without errors
    svg_content = svg_buffer.getvalue().decode("utf-8")
    assert len(svg_content) > 0
    assert "<svg" in svg_content
    assert 'xmlns="http://www.w3.org/2000/svg"' in svg_content

    # Decode the QR code and verify the data
    decoded_data = decode_qr_png(png_buffer)
    assert decoded_data is not None, "Failed to decode QR code"
    assert test_data in decoded_data, f"Expected '{test_data}' in QR code data"


def test_generate_qr_code_empty_string():
    """Test QR code generation with an empty string."""
    svg_buffer = generate_qr_code("")
    svg_content = svg_buffer.getvalue().decode("utf-8")
    assert len(svg_content) > 0
    assert "<svg" in svg_content
    assert 'xmlns="http://www.w3.org/2000/svg"' in svg_content


def test_is_available_at_start_time():
    """Test that a meeting is available at its exact start time."""
    current_time = datetime.now(timezone.utc)
    start_time = current_time
    end_time = start_time + timedelta(hours=2)
    assert is_available(start_time, end_time, current_time)


def test_is_available_shortly_before_start():
    """Test that a meeting is available 5 minutes before start time."""
    current_time = datetime.now(timezone.utc)
    start_time = current_time + timedelta(minutes=5)
    end_time = start_time + timedelta(hours=2)
    assert is_available(start_time, end_time, current_time)


def test_is_available_at_15_minute_window():
    """Test that a meeting is available exactly 15 minutes before start time."""
    current_time = datetime.now(timezone.utc)
    start_time = current_time + timedelta(minutes=15)
    end_time = start_time + timedelta(hours=2)
    assert is_available(start_time, end_time, current_time)


def test_is_available_not_available_before_15_minute_window():
    """Test that a meeting is not available more than 15 minutes before start time."""
    current_time = datetime.now(timezone.utc)
    start_time = current_time + timedelta(minutes=16)
    end_time = start_time + timedelta(hours=2)
    assert not is_available(start_time, end_time, current_time)


def test_is_available_not_available_after_end():
    """Test that a meeting is not available after its end time."""
    current_time = datetime.now(timezone.utc)
    start_time = current_time - timedelta(hours=2, minutes=1)
    end_time = start_time + timedelta(hours=2)
    assert not is_available(start_time, end_time, current_time)


def test_is_available_not_available_long_after_end():
    """Test that a meeting is not available long after its end time."""
    current_time = datetime.now(timezone.utc)
    start_time = current_time - timedelta(hours=24)
    end_time = start_time + timedelta(hours=2)
    assert not is_available(start_time, end_time, current_time)


def test_create_meeting_success(db_session: Session):
    """Test successfully creating a new meeting."""
    # Test data
    start_time = datetime.now(timezone.utc) + timedelta(hours=1)
    end_time = start_time + timedelta(hours=1)

    # Call the function
    meeting_id, meeting_code = create_meeting(db_session, start_time, end_time)

    # Verify the meeting was created
    assert meeting_id is not None
    assert isinstance(meeting_id, int)
    assert isinstance(meeting_code, str)
    assert len(meeting_code) == 8
    assert all(c.isupper() for c in meeting_code)

    # Verify the meeting exists in the database
    meeting = db_session.get(Meeting, meeting_id)
    assert meeting is not None
    assert meeting.start_time == start_time
    assert meeting.end_time == end_time
    assert meeting.meeting_code == meeting_code


def test_create_meeting_duplicate_code_handling(db_session: Session, monkeypatch):
    """Test that the function handles duplicate meeting codes by retrying."""

    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(hours=1)

    # Mock the make_pronounceable function to return duplicate codes first
    codes = ["DUPLICAT", "UNIQUECODE"]

    def mock_make_pronounceable(length=8):
        return codes.pop(0)

    import app.services.meetings as meetings_module

    monkeypatch.setattr(meetings_module, "make_pronounceable", mock_make_pronounceable)

    # Create first meeting with the duplicate code
    meeting_id, meeting_code = create_meeting(db_session, start_time, end_time)
    assert meeting_code == "DUPLICAT"

    # This should use the second code since the first one is taken
    meeting_id, meeting_code = create_meeting(db_session, start_time, end_time)
    assert meeting_code == "UNIQUECODE"

    # Verify both meetings exist with different codes
    count = (
        db_session.query(Meeting)
        .filter(Meeting.meeting_code.in_(["DUPLICAT", "UNIQUECODE"]))
        .count()
    )
    assert count == 2


def test_create_meeting_invalid_times(db_session: Session):
    """Test that end time must be after start time."""
    now = datetime.now(timezone.utc)
    start_time = now + timedelta(hours=1)
    end_time = start_time - timedelta(minutes=30)  # End before start

    original_count = db_session.query(Meeting).count()

    with pytest.raises(ValueError, match="End time must be after start time"):
        create_meeting(db_session, start_time, end_time)

    # Edge case: start and end times are the same
    with pytest.raises(ValueError, match="End time must be after start time"):
        create_meeting(db_session, start_time, start_time)

    # Verify no new meetings were created
    count = db_session.query(Meeting).count()
    assert count == original_count


def test_delete_meeting_success(db_session: Session):
    """Test successfully deleting a meeting with all its associated data."""
    # Create a new meeting
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE",
    )
    db_session.add(meeting)
    db_session.commit()

    # Add some polls and votes to test cascading deletes
    poll1 = Poll(meeting_id=meeting.id, name="Poll 1")
    poll2 = Poll(meeting_id=meeting.id, name="Poll 2")
    db_session.add_all([poll1, poll2])
    db_session.flush()

    # Add some votes
    votes = [
        PollVote(poll_id=poll1.id, vote_token="TOKEN1", vote="A"),
        PollVote(poll_id=poll1.id, vote_token="TOKEN2", vote="B"),
        PollVote(poll_id=poll2.id, vote_token="TOKEN1", vote="C"),
    ]
    db_session.add_all(votes)

    # Add some check-ins
    checkins = [
        Checkin(
            meeting_id=meeting.id,
            vote_token="TOKEN1",
            timestamp=datetime.now(timezone.utc),
        ),
        Checkin(
            meeting_id=meeting.id,
            vote_token="TOKEN2",
            timestamp=datetime.now(timezone.utc),
        ),
    ]
    db_session.add_all(checkins)
    db_session.commit()

    # Now delete the meeting
    delete_meeting(db_session, meeting.id)

    db_session.commit()

    # Verify the meeting and all related data was deleted
    assert db_session.get(Meeting, meeting.id) is None
    assert db_session.query(Poll).filter_by(meeting_id=meeting.id).first() is None
    assert (
        db_session.query(PollVote)
        .filter(PollVote.poll_id.in_([poll1.id, poll2.id]))
        .first()
        is None
    )
    assert db_session.query(Checkin).filter_by(meeting_id=meeting.id).first() is None


def test_delete_nonexistent_meeting(db_session: Session):
    """Test deleting a meeting that doesn't exist."""
    # Get a non-existent meeting ID (use a very high number)
    non_existent_id = 999999

    original_count = db_session.query(Meeting).count()

    # This should not raise an error
    delete_meeting(db_session, non_existent_id)

    # Verify no error was raised and no data was affected
    count = db_session.query(Meeting).count()
    assert count == original_count


def test_delete_meeting_without_polls(db_session: Session):
    """Test deleting a meeting that has no polls."""
    # Create a new meeting with no polls
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE",
    )
    db_session.add(meeting)
    db_session.commit()

    # Add a check-in to verify it gets deleted too
    checkin = Checkin(
        meeting_id=meeting.id,
        vote_token="TESTTOKEN",
        timestamp=datetime.now(timezone.utc),
    )
    db_session.add(checkin)
    db_session.commit()

    # Delete the meeting
    delete_meeting(db_session, meeting.id)
    db_session.commit()

    # Verify the meeting and its check-in were deleted
    assert db_session.get(Meeting, meeting.id) is None
    assert db_session.query(Checkin).filter_by(meeting_id=meeting.id).first() is None


def test_create_poll_success(db_session: Session):
    """Test successful creation of a poll."""
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE",
    )
    db_session.add(meeting)
    db_session.commit()

    # Test creating a new poll
    new_poll_name = "New Test Poll"
    poll_id = create_poll(db_session, meeting.id, new_poll_name)

    # Verify the poll was created
    assert isinstance(poll_id, int)
    assert poll_id > 0

    # Verify the poll exists in the database
    poll = db_session.get(Poll, poll_id)
    assert poll is not None
    assert poll.name == new_poll_name
    assert poll.meeting_id == meeting.id


def test_create_poll_nonexistent_meeting(db_session: Session):
    """Test creating a poll with a non-existent meeting ID."""
    non_existent_meeting_id = 999999
    poll_name = "Test Nonexistent Poll"

    with pytest.raises(ValueError, match="Meeting does not exist"):
        create_poll(db_session, non_existent_meeting_id, poll_name)

    # Verify no poll was created
    count = db_session.query(Poll).filter_by(name=poll_name).count()
    assert count == 0


def test_create_poll_empty_name(db_session: Session):
    """Test creating a poll with an empty name."""
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE",
    )
    db_session.add(meeting)
    db_session.commit()

    with pytest.raises(ValueError, match="Poll name cannot be empty"):
        create_poll(db_session, meeting.id, "")


def test_create_poll_duplicate_name_same_meeting(db_session: Session):
    """Test creating a poll with a duplicate name in the same meeting."""
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE",
    )
    db_session.add(meeting)
    db_session.commit()

    poll_name = "Poll 1"
    poll1 = Poll(meeting_id=meeting.id, name=poll_name)
    db_session.add(poll1)
    db_session.flush()

    # Second creation with same name in same meeting should fail
    with pytest.raises(
        ValueError, match="A poll with this name already exists in this meeting"
    ):
        create_poll(db_session, meeting.id, poll_name)


def test_create_poll_same_name_different_meeting(db_session: Session):
    """Test creating polls with the same name in different meetings."""
    meeting1 = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE1",
    )
    meeting2 = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE2",
    )
    db_session.add_all([meeting1, meeting2])
    db_session.commit()

    poll_name = "Same Name Poll"

    # Create poll in first meeting
    poll1_id = create_poll(db_session, meeting1.id, poll_name)
    assert poll1_id is not None

    # Create poll with same name in second meeting (should succeed)
    poll2_id = create_poll(db_session, meeting2.id, poll_name)
    assert poll2_id is not None
    assert poll2_id != poll1_id

    # Verify both polls were created
    count = db_session.query(Poll).filter_by(name=poll_name).count()
    assert count == 2


def test_delete_poll_success(db_session: Session):
    """Test successful deletion of a poll."""
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE",
    )
    db_session.add(meeting)
    db_session.commit()

    poll_name = "Poll 1"
    poll1 = Poll(meeting_id=meeting.id, name=poll_name)
    db_session.add(poll1)
    db_session.commit()
    poll_id = poll1.id

    votes = [
        PollVote(poll_id=poll_id, vote_token="TOKEN1", vote="A"),
        PollVote(poll_id=poll_id, vote_token="TOKEN2", vote="B"),
    ]
    db_session.add_all(votes)
    db_session.commit()

    result = delete_poll(db_session, meeting.id, poll_id)
    assert result is True

    # Verify the poll was deleted
    assert db_session.get(Poll, poll_id) is None

    # Verify associated votes were deleted
    count = db_session.query(PollVote).filter_by(poll_id=poll_id).count()
    assert count == 0


def test_delete_nonexistent_poll(db_session: Session):
    """Test deleting a poll that doesn't exist."""
    non_existent_id = 999999
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE",
    )
    db_session.add(meeting)
    db_session.commit()

    # Verify the poll doesn't exist
    assert db_session.get(Poll, non_existent_id) is None

    # Try to delete the non-existent poll
    result = delete_poll(db_session, meeting.id, non_existent_id)
    assert result is False


def test_checkin_success(db_session: Session):
    """Test successful check-in to a meeting."""
    meeting_code = "TESTCODE"
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code=meeting_code,
    )
    db_session.add(meeting)
    db_session.commit()

    vote_token = checkin(db_session, meeting.id, meeting_code)
    assert len(vote_token) > 0

    # Verify the check-in was recorded
    count = (
        db_session.query(Checkin)
        .filter_by(meeting_id=meeting.id, vote_token=vote_token)
        .count()
    )
    assert count == 1


def test_checkin_invalid_meeting_id(db_session: Session):
    """Test check-in with a non-existent meeting ID."""
    invalid_meeting_id = 999999
    meeting_code = "TESTCODE"
    with pytest.raises(ValueError, match="Meeting not found"):
        checkin(db_session, invalid_meeting_id, meeting_code)


def test_checkin_invalid_meeting_code(db_session: Session):
    """Test check-in with an incorrect meeting code."""
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE",
    )
    db_session.add(meeting)
    db_session.commit()

    invalid_meeting_code = "WRONGCODE"
    with pytest.raises(ValueError, match="Invalid meeting code"):
        checkin(db_session, meeting.id, invalid_meeting_code)


def test_checkin_meeting_not_available(db_session: Session):
    """Test check-in when the meeting is not available (already ended)."""
    meeting_code = "TESTCODE"
    meeting = Meeting(
        start_time=datetime.now(timezone.utc) - timedelta(hours=2),
        end_time=datetime.now(timezone.utc) - timedelta(minutes=1),
        meeting_code=meeting_code,
    )
    db_session.add(meeting)
    db_session.commit()

    with pytest.raises(ValueError, match="Meeting is not available"):
        checkin(db_session, meeting.id, meeting_code)


def test_checkin_duplicate_token(db_session: Session):
    """Test that check-in generates a unique token even if there's a collision."""
    meeting_code = "TESTCODE"
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(minutes=2),
        meeting_code=meeting_code,
    )
    db_session.add(meeting)
    db_session.commit()

    first_token = "TOKEN1"
    db_session.add(
        Checkin(
            meeting_id=meeting.id,
            vote_token=first_token,
            timestamp=datetime.now(timezone.utc),
        )
    )
    db_session.commit()

    # Second check-in with same code should generate a different token
    second_token = checkin(db_session, meeting.id, meeting_code)
    assert second_token is not None
    assert first_token != second_token  # Tokens should be different

    # Verify both check-ins were recorded
    count = (
        db_session.query(Checkin)
        .filter(
            Checkin.meeting_id == meeting.id,
            Checkin.vote_token.in_([first_token, second_token]),
        )
        .count()
    )
    assert count == 2


def test_get_polls_success(db_session: Session):
    """Test retrieving the polls for a meeting."""
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE",
    )
    db_session.add(meeting)
    db_session.commit()

    # Add some polls and votes to test cascading deletes
    poll1 = Poll(meeting_id=meeting.id, name="Poll 1")
    poll2 = Poll(meeting_id=meeting.id, name="Poll 2")
    db_session.add_all([poll1, poll2])
    db_session.commit()

    # Add some votes
    votes = [
        PollVote(poll_id=poll1.id, vote_token="TOKEN1", vote="A"),
        PollVote(poll_id=poll1.id, vote_token="TOKEN2", vote="B"),
        PollVote(poll_id=poll2.id, vote_token="TOKEN1", vote="C"),
    ]
    db_session.add_all(votes)
    db_session.commit()

    # Get polls for the test meeting
    polls = get_polls(db_session, meeting.id)

    # Should return a dict with two polls as set up in the test database
    assert isinstance(polls, dict)
    assert len(polls) == 2

    # Verify the poll data
    count = 0
    for eid in polls:
        if eid == poll1.id and poll1.name == "Poll 1":
            count += 1
        elif eid == poll2.id and poll2.name == "Poll 2":
            count += 1
    assert count == 2


def test_get_polls_no_polls(db_session: Session):
    """Test retrieving polls for a meeting with no polls."""
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE",
    )
    db_session.add(meeting)
    db_session.commit()

    # Get polls for the test meeting
    polls = get_polls(db_session, meeting.id)
    assert polls == {}


def test_get_polls_nonexistent_meeting(db_session: Session):
    """Test retrieving polls for a non-existent meeting."""
    non_existent_meeting_id = 999999
    polls = get_polls(db_session, non_existent_meeting_id)
    assert polls == {}


def test_get_meeting_success(db_session: Session):
    """Test retrieving a specific meeting."""
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE",
    )
    db_session.add(meeting)
    db_session.commit()

    m = get_meeting(db_session, meeting.id)
    assert m is not None
    assert m["id"] == meeting.id
    assert m["start_time"] == meeting.start_time
    assert m["end_time"] == meeting.end_time
    assert m["meeting_code"] == meeting.meeting_code


def test_get_meeting_nonexistent_meeting(db_session: Session):
    """Test retrieving a non-existent meeting."""
    non_existent_meeting_id = 999999
    meeting = get_meeting(db_session, non_existent_meeting_id)
    assert meeting is None


def test_get_poll_success(db_session: Session):
    """Test successfully retrieving a poll with votes."""
    # Create a meeting
    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(hours=2)
    meeting = Meeting(
        start_time=start_time,
        end_time=end_time,
        meeting_code="ABC123",
    )
    db_session.add(meeting)
    db_session.commit()

    # Create a poll
    poll = Poll(meeting_id=meeting.id, name="Test Poll")
    db_session.add(poll)
    db_session.commit()

    # Create a check-in and vote
    vote_token = "test_token_123"
    checkin = Checkin(
        meeting_id=meeting.id,
        vote_token=vote_token,
        timestamp=datetime.now(timezone.utc),
    )
    db_session.add(checkin)
    db_session.commit()

    # Record a vote
    vote = PollVote(
        poll_id=poll.id,
        vote_token=vote_token,
        vote="A",
    )
    db_session.add(vote)
    db_session.commit()

    # Test getting the poll
    result = get_poll(db_session, poll.id)

    # Verify the result
    assert result is not None
    assert result["id"] == poll.id
    assert result["name"] == "Test Poll"
    assert result["meeting_id"] == meeting.id
    assert isinstance(result["votes"], dict)
    assert result["votes"]["A"] == 1  # One vote for A
    assert result["total_votes"] == 1  # Total votes should be 1


def test_get_poll_no_votes(db_session: Session):
    """Test retrieving a poll with no votes."""
    # Create a meeting
    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(hours=2)
    meeting = Meeting(
        start_time=start_time,
        end_time=end_time,
        meeting_code="ABC123",
    )
    db_session.add(meeting)
    db_session.commit()

    # Create a poll
    poll = Poll(meeting_id=meeting.id, name="Test Poll No Votes")
    db_session.add(poll)
    db_session.commit()

    # Test getting the poll
    result = get_poll(db_session, poll.id)

    # Verify the result
    assert result is not None
    assert result["id"] == poll.id
    assert result["name"] == "Test Poll No Votes"
    assert result["meeting_id"] == meeting.id
    assert isinstance(result["votes"], dict)
    assert result["total_votes"] == 0  # No votes should be recorded
    # Check that all vote options are present and set to 0
    for option in "ABCDEFGH":
        assert result["votes"][option] == 0


def test_get_nonexistent_poll(db_session: Session):
    """Test retrieving a non-existent poll."""
    non_existent_poll_id = 999999
    result = get_poll(db_session, non_existent_poll_id)
    assert result is None


def test_get_poll_with_multiple_votes(db_session: Session):
    """Test retrieving a poll with multiple votes."""
    # Create a meeting
    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(hours=2)
    meeting = Meeting(
        start_time=start_time,
        end_time=end_time,
        meeting_code="MULTIVOTE",
    )
    db_session.add(meeting)
    db_session.commit()

    # Create a poll
    poll = Poll(meeting_id=meeting.id, name="Multi-Vote Poll")
    db_session.add(poll)
    db_session.commit()

    # Create check-ins and votes
    for i, vote_option in enumerate(
        ["A", "B", "C", "A", "B", "A"]
    ):  # 3 A's, 2 B's, 1 C
        vote_token = f"token_{i}"
        checkin = Checkin(
            meeting_id=meeting.id,
            vote_token=vote_token,
            timestamp=datetime.now(timezone.utc),
        )
        db_session.add(checkin)
        db_session.flush()  # Flush to get the checkin ID

        vote = PollVote(
            poll_id=poll.id,
            vote_token=vote_token,
            vote=vote_option,
        )
        db_session.add(vote)

    db_session.commit()

    # Test getting the poll
    result = get_poll(db_session, poll.id)

    # Verify the result
    assert result is not None
    assert result["id"] == poll.id
    assert result["name"] == "Multi-Vote Poll"
    assert result["meeting_id"] == meeting.id
    assert result["total_votes"] == 6  # Total votes should be 6

    # Verify vote counts
    assert result["votes"]["A"] == 3
    assert result["votes"]["B"] == 2
    assert result["votes"]["C"] == 1

    # Verify other options are 0
    for option in "DEFGH":
        assert result["votes"][option] == 0


def test_get_user_votes_success(db_session: Session):
    """Test retrieving votes from a specific meeting."""
    # Create a new meeting
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE",
    )
    db_session.add(meeting)
    db_session.commit()

    # Add some polls and votes to test cascading deletes
    poll1 = Poll(meeting_id=meeting.id, name="Poll 1")
    poll2 = Poll(meeting_id=meeting.id, name="Poll 2")
    db_session.add_all([poll1, poll2])
    db_session.flush()

    # Add some check-ins
    db_session.add_all(
        [
            Checkin(
                meeting_id=meeting.id,
                vote_token="TOKEN1",
                timestamp=datetime.now(timezone.utc),
            ),
            Checkin(
                meeting_id=meeting.id,
                vote_token="TOKEN2",
                timestamp=datetime.now(timezone.utc),
            ),
        ]
    )
    db_session.commit()

    # Add some votes
    db_session.add_all(
        [
            PollVote(poll_id=poll1.id, vote_token="TOKEN1", vote="A"),
            PollVote(poll_id=poll1.id, vote_token="TOKEN2", vote="B"),
            PollVote(poll_id=poll2.id, vote_token="TOKEN1", vote="C"),
        ]
    )
    db_session.commit()

    votes = get_user_votes(db_session, meeting.id, "TOKEN1")
    assert isinstance(votes, dict)
    assert len(votes) == 2
    assert poll1.id in votes
    assert votes[poll1.id]["name"] == "Poll 1"
    assert votes[poll1.id]["vote"] == "A"
    assert poll2.id in votes
    assert votes[poll2.id]["name"] == "Poll 2"
    assert votes[poll2.id]["vote"] == "C"


def test_get_user_votes_nonexistent_meeting(db_session: Session):
    """Test retrieving votes from a specific meeting."""
    votes = get_user_votes(db_session, 9999, "TOKEN1")
    assert len(votes) == 0


def test_get_user_votes_nonexistent_vote_token(db_session: Session):
    """Test retrieving votes with a non-existent token."""
    # Create a new meeting
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE",
    )
    db_session.add(meeting)
    db_session.commit()

    # Add some polls and votes to test cascading deletes
    poll1 = Poll(meeting_id=meeting.id, name="Poll 1")
    poll2 = Poll(meeting_id=meeting.id, name="Poll 2")
    db_session.add_all([poll1, poll2])
    db_session.flush()

    # Add some check-ins
    db_session.add_all(
        [
            Checkin(
                meeting_id=meeting.id,
                vote_token="TOKEN1",
                timestamp=datetime.now(timezone.utc),
            ),
            Checkin(
                meeting_id=meeting.id,
                vote_token="TOKEN2",
                timestamp=datetime.now(timezone.utc),
            ),
        ]
    )
    db_session.commit()

    # Add some votes
    db_session.add_all(
        [
            PollVote(poll_id=poll1.id, vote_token="TOKEN1", vote="A"),
            PollVote(poll_id=poll1.id, vote_token="TOKEN2", vote="B"),
            PollVote(poll_id=poll2.id, vote_token="TOKEN1", vote="C"),
        ]
    )
    db_session.commit()
    non_existent_token = "NONEXISTENTTOKEN"
    votes = get_user_votes(db_session, meeting.id, non_existent_token)
    assert votes == {}


def test_get_vote_counts(db_session: Session):
    """Test getting vote counts."""
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE",
    )
    db_session.add(meeting)
    db_session.commit()

    poll = Poll(meeting_id=meeting.id, name="Poll 1")
    db_session.add(poll)
    db_session.commit()

    # Add some votes
    db_session.add_all(
        [
            PollVote(poll_id=poll.id, vote_token="TOKEN1", vote="A"),
            PollVote(poll_id=poll.id, vote_token="TOKEN2", vote="B"),
        ]
    )
    db_session.commit()

    vote_counts = get_vote_counts(db_session, poll.id)
    assert vote_counts == {
        "A": 1,
        "B": 1,
        "C": 0,
        "D": 0,
        "E": 0,
        "F": 0,
        "G": 0,
        "H": 0,
    }


def test_vote_in_poll_success(db_session: Session):
    """Test successfully voting in a poll."""
    # Create a meeting
    start_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    end_time = datetime.now(timezone.utc) + timedelta(hours=1)
    meeting = Meeting(
        start_time=start_time,
        end_time=end_time,
        meeting_code="ABC123",
    )
    db_session.add(meeting)
    db_session.commit()

    # Create a poll
    poll = Poll(meeting_id=meeting.id, name="Test Poll")
    db_session.add(poll)
    db_session.commit()

    # Create a check-in
    vote_token = "test_token_123"
    checkin = Checkin(
        meeting_id=meeting.id,
        vote_token=vote_token,
        timestamp=datetime.now(timezone.utc),
    )
    db_session.add(checkin)
    db_session.commit()

    vote_in_poll(
        db=db_session,
        meeting_id=meeting.id,
        poll_id=poll.id,
        vote_token=vote_token,
        vote="A",
    )

    # Verify the vote was recorded
    vote = (
        db_session.query(PollVote)
        .filter(
            PollVote.poll_id == poll.id,
            PollVote.vote_token == vote_token,
        )
        .one_or_none()
    )
    assert vote is not None
    assert vote.vote == "A"


def test_vote_in_poll_invalid_poll(db_session: Session):
    """Test voting with an invalid poll ID."""
    # Create a meeting
    start_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    end_time = datetime.now(timezone.utc) + timedelta(hours=1)
    meeting = Meeting(
        start_time=start_time,
        end_time=end_time,
        meeting_code="ABC123",
    )
    db_session.add(meeting)
    db_session.commit()

    # Create a check-in
    vote_token = "test_token_123"
    checkin = Checkin(
        meeting_id=meeting.id,
        vote_token=vote_token,
        timestamp=datetime.now(timezone.utc),
    )
    db_session.add(checkin)
    db_session.commit()

    with pytest.raises(ValueError, match="Invalid poll"):
        vote_in_poll(
            db=db_session,
            meeting_id=meeting.id,
            poll_id=999,  # Non-existent poll
            vote_token=vote_token,
            vote="A",
        )


def test_vote_in_poll_already_voted(db_session: Session):
    """Test that a user cannot vote twice in the same poll."""
    # Create a meeting
    start_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    end_time = datetime.now(timezone.utc) + timedelta(hours=1)
    meeting = Meeting(
        start_time=start_time,
        end_time=end_time,
        meeting_code="ABC123",
    )
    db_session.add(meeting)
    db_session.commit()

    # Create a poll
    poll = Poll(meeting_id=meeting.id, name="Test Poll")
    db_session.add(poll)
    db_session.commit()

    # Create a check-in
    vote_token = "test_token_123"
    checkin = Checkin(
        meeting_id=meeting.id,
        vote_token=vote_token,
        timestamp=datetime.now(timezone.utc),
    )
    db_session.add(checkin)
    db_session.commit()

    # Record a vote
    vote = PollVote(
        poll_id=poll.id,
        vote_token=vote_token,
        vote="A",
    )
    db_session.add(vote)
    db_session.commit()

    # Try to vote again with the same token
    with pytest.raises(ValueError, match="already voted"):
        vote_in_poll(
            db=db_session,
            meeting_id=meeting.id,
            poll_id=poll.id,
            vote_token=vote_token,
            vote="B",  # Different vote
        )


def test_vote_in_poll_invalid_token(db_session: Session):
    """Test voting with an invalid token."""
    # Create a meeting
    start_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    end_time = datetime.now(timezone.utc) + timedelta(hours=1)
    meeting = Meeting(
        start_time=start_time,
        end_time=end_time,
        meeting_code="ABC123",
    )
    db_session.add(meeting)
    db_session.commit()

    # Create a poll
    poll = Poll(meeting_id=meeting.id, name="Test Poll")
    db_session.add(poll)
    db_session.commit()

    # Try to vote with an invalid token
    with pytest.raises(ValueError, match="Invalid token"):
        vote_in_poll(
            db=db_session,
            meeting_id=meeting.id,
            poll_id=poll.id,
            vote_token="invalid_token",
            vote="A",
        )


def test_vote_in_poll_meeting_ended(db_session: Session):
    """Test that voting is not allowed after the meeting has ended."""
    # Create a meeting that has already ended
    start_time = datetime.now(timezone.utc) - timedelta(hours=2)
    end_time = datetime.now(timezone.utc) - timedelta(hours=1)
    meeting = Meeting(
        start_time=start_time,
        end_time=end_time,
        meeting_code="ABC123",
    )
    db_session.add(meeting)
    db_session.commit()

    # Create a poll
    poll = Poll(meeting_id=meeting.id, name="Test Poll")
    db_session.add(poll)
    db_session.commit()

    # Create a check-in (even though meeting has ended, the check-in exists)
    vote_token = "test_token_123"
    checkin = Checkin(
        meeting_id=meeting.id,
        vote_token=vote_token,
        timestamp=datetime.now(timezone.utc),
    )
    db_session.add(checkin)
    db_session.commit()

    # Try to vote after meeting has ended
    with pytest.raises(ValueError, match="Voting has ended"):
        vote_in_poll(
            db=db_session,
            meeting_id=meeting.id,
            poll_id=poll.id,
            vote_token=vote_token,
            vote="A",
        )
