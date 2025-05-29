import importlib
from datetime import datetime, timedelta, timezone
from io import BytesIO

import pytest
from sqlalchemy.orm import Session

from app.models import Checkin, Election, ElectionVote, Meeting
from app.services import (
    checkin,
    create_election,
    create_meeting,
    delete_election,
    delete_meeting,
    generate_qr_code,
    get_election,
    get_elections,
    get_meeting,
    get_user_votes,
    get_vote_counts,
    is_available,
    vote_in_election,
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


def test_create_meeting_success(db_connection: Session):
    """Test successfully creating a new meeting."""
    # Test data
    start_time = datetime.now(timezone.utc) + timedelta(hours=1)
    end_time = start_time + timedelta(hours=1)

    # Call the function
    meeting_id, meeting_code = create_meeting(db_connection, start_time, end_time)

    # Verify the meeting was created
    assert meeting_id is not None
    assert isinstance(meeting_id, int)
    assert isinstance(meeting_code, str)
    assert len(meeting_code) == 8
    assert all(c.isupper() for c in meeting_code)

    # Verify the meeting exists in the database
    meeting = db_connection.get(Meeting, meeting_id)
    assert meeting is not None
    assert meeting.start_time == start_time
    assert meeting.end_time == end_time
    assert meeting.meeting_code == meeting_code


def test_create_meeting_duplicate_code_handling(db_connection: Session, monkeypatch):
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
    meeting_id, meeting_code = create_meeting(db_connection, start_time, end_time)
    assert meeting_code == "DUPLICAT"

    # This should use the second code since the first one is taken
    meeting_id, meeting_code = create_meeting(db_connection, start_time, end_time)
    assert meeting_code == "UNIQUECODE"

    # Verify both meetings exist with different codes
    count = (
        db_connection.query(Meeting)
        .filter(Meeting.meeting_code.in_(["DUPLICAT", "UNIQUECODE"]))
        .count()
    )
    assert count == 2


def test_create_meeting_invalid_times(db_connection: Session):
    """Test that end time must be after start time."""
    now = datetime.now(timezone.utc)
    start_time = now + timedelta(hours=1)
    end_time = start_time - timedelta(minutes=30)  # End before start

    original_count = db_connection.query(Meeting).count()

    with pytest.raises(ValueError, match="End time must be after start time"):
        create_meeting(db_connection, start_time, end_time)

    # Edge case: start and end times are the same
    with pytest.raises(ValueError, match="End time must be after start time"):
        create_meeting(db_connection, start_time, start_time)

    # Verify no new meetings were created
    count = db_connection.query(Meeting).count()
    assert count == original_count


def test_delete_meeting_success(db_connection: Session):
    """Test successfully deleting a meeting with all its associated data."""
    # Create a new meeting
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE",
    )
    db_connection.add(meeting)
    db_connection.commit()

    # Add some elections and votes to test cascading deletes
    election1 = Election(meeting_id=meeting.id, name="Election 1")
    election2 = Election(meeting_id=meeting.id, name="Election 2")
    db_connection.add_all([election1, election2])
    db_connection.flush()

    # Add some votes
    votes = [
        ElectionVote(election_id=election1.id, vote_token="TOKEN1", vote="A"),
        ElectionVote(election_id=election1.id, vote_token="TOKEN2", vote="B"),
        ElectionVote(election_id=election2.id, vote_token="TOKEN1", vote="C"),
    ]
    db_connection.add_all(votes)

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
    db_connection.add_all(checkins)
    db_connection.commit()

    # Now delete the meeting
    delete_meeting(db_connection, meeting.id)

    db_connection.commit()

    # Verify the meeting and all related data was deleted
    assert db_connection.get(Meeting, meeting.id) is None
    assert (
        db_connection.query(Election).filter_by(meeting_id=meeting.id).first() is None
    )
    assert (
        db_connection.query(ElectionVote)
        .filter(ElectionVote.election_id.in_([election1.id, election2.id]))
        .first()
        is None
    )
    assert db_connection.query(Checkin).filter_by(meeting_id=meeting.id).first() is None


def test_delete_nonexistent_meeting(db_connection: Session):
    """Test deleting a meeting that doesn't exist."""
    # Get a non-existent meeting ID (use a very high number)
    non_existent_id = 999999

    original_count = db_connection.query(Meeting).count()

    # This should not raise an error
    delete_meeting(db_connection, non_existent_id)

    # Verify no error was raised and no data was affected
    count = db_connection.query(Meeting).count()
    assert count == original_count


def test_delete_meeting_without_elections(db_connection: Session):
    """Test deleting a meeting that has no elections."""
    # Create a new meeting with no elections
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE",
    )
    db_connection.add(meeting)
    db_connection.commit()

    # Add a check-in to verify it gets deleted too
    checkin = Checkin(
        meeting_id=meeting.id,
        vote_token="TESTTOKEN",
        timestamp=datetime.now(timezone.utc),
    )
    db_connection.add(checkin)
    db_connection.commit()

    # Delete the meeting
    delete_meeting(db_connection, meeting.id)
    db_connection.commit()

    # Verify the meeting and its check-in were deleted
    assert db_connection.get(Meeting, meeting.id) is None
    assert db_connection.query(Checkin).filter_by(meeting_id=meeting.id).first() is None


def test_create_election_success(db_connection: Session):
    """Test successful creation of an election."""
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE",
    )
    db_connection.add(meeting)
    db_connection.commit()

    # Test creating a new election
    new_election_name = "New Test Election"
    election_id = create_election(db_connection, meeting.id, new_election_name)

    # Verify the election was created
    assert isinstance(election_id, int)
    assert election_id > 0

    # Verify the election exists in the database
    election = db_connection.get(Election, election_id)
    assert election is not None
    assert election.name == new_election_name
    assert election.meeting_id == meeting.id


def test_create_election_nonexistent_meeting(db_connection: Session):
    """Test creating an election with a non-existent meeting ID."""
    non_existent_meeting_id = 999999
    election_name = "Test Nonexistent Election"

    with pytest.raises(ValueError, match="Meeting does not exist"):
        create_election(db_connection, non_existent_meeting_id, election_name)

    # Verify no election was created
    count = db_connection.query(Election).filter_by(name=election_name).count()
    assert count == 0


def test_create_election_empty_name(db_connection: Session):
    """Test creating an election with an empty name."""
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE",
    )
    db_connection.add(meeting)
    db_connection.commit()

    with pytest.raises(ValueError, match="Election name cannot be empty"):
        create_election(db_connection, meeting.id, "")


def test_create_election_duplicate_name_same_meeting(db_connection: Session):
    """Test creating an election with a duplicate name in the same meeting."""
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE",
    )
    db_connection.add(meeting)
    db_connection.commit()

    election_name = "Election 1"
    election1 = Election(meeting_id=meeting.id, name=election_name)
    db_connection.add(election1)
    db_connection.flush()

    # Second creation with same name in same meeting should fail
    with pytest.raises(
        ValueError, match="An election with this name already exists in this meeting"
    ):
        create_election(db_connection, meeting.id, election_name)


def test_create_election_same_name_different_meeting(db_connection: Session):
    """Test creating elections with the same name in different meetings."""
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
    db_connection.add_all([meeting1, meeting2])
    db_connection.commit()

    election_name = "Same Name Election"

    # Create election in first meeting
    election1_id = create_election(db_connection, meeting1.id, election_name)
    assert election1_id is not None

    # Create election with same name in second meeting (should succeed)
    election2_id = create_election(db_connection, meeting2.id, election_name)
    assert election2_id is not None
    assert election2_id != election1_id

    # Verify both elections were created
    count = db_connection.query(Election).filter_by(name=election_name).count()
    assert count == 2


def test_delete_election_success(db_connection: Session):
    """Test successful deletion of an election."""
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE",
    )
    db_connection.add(meeting)
    db_connection.commit()

    election_name = "Election 1"
    election1 = Election(meeting_id=meeting.id, name=election_name)
    db_connection.add(election1)
    db_connection.commit()
    election_id = election1.id

    votes = [
        ElectionVote(election_id=election_id, vote_token="TOKEN1", vote="A"),
        ElectionVote(election_id=election_id, vote_token="TOKEN2", vote="B"),
    ]
    db_connection.add_all(votes)
    db_connection.commit()

    result = delete_election(db_connection, meeting.id, election_id)
    assert result is True

    # Verify the election was deleted
    assert db_connection.get(Election, election_id) is None

    # Verify associated votes were deleted
    count = db_connection.query(ElectionVote).filter_by(election_id=election_id).count()
    assert count == 0


def test_delete_nonexistent_election(db_connection: Session):
    """Test deleting an election that doesn't exist."""
    non_existent_id = 999999
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE",
    )
    db_connection.add(meeting)
    db_connection.commit()

    # Verify the election doesn't exist
    assert db_connection.get(Election, non_existent_id) is None

    # Try to delete the non-existent election
    result = delete_election(db_connection, meeting.id, non_existent_id)
    assert result is False


def test_checkin_success(db_connection: Session):
    """Test successful check-in to a meeting."""
    meeting_code = "TESTCODE"
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code=meeting_code,
    )
    db_connection.add(meeting)
    db_connection.commit()

    vote_token = checkin(db_connection, meeting.id, meeting_code)
    assert len(vote_token) > 0

    # Verify the check-in was recorded
    count = (
        db_connection.query(Checkin)
        .filter_by(meeting_id=meeting.id, vote_token=vote_token)
        .count()
    )
    assert count == 1


def test_checkin_invalid_meeting_id(db_connection: Session):
    """Test check-in with a non-existent meeting ID."""
    invalid_meeting_id = 999999
    meeting_code = "TESTCODE"
    with pytest.raises(ValueError, match="Meeting not found"):
        checkin(db_connection, invalid_meeting_id, meeting_code)


def test_checkin_invalid_meeting_code(db_connection: Session):
    """Test check-in with an incorrect meeting code."""
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE",
    )
    db_connection.add(meeting)
    db_connection.commit()

    invalid_meeting_code = "WRONGCODE"
    with pytest.raises(ValueError, match="Invalid meeting code"):
        checkin(db_connection, meeting.id, invalid_meeting_code)


def test_checkin_meeting_not_available(db_connection: Session):
    """Test check-in when the meeting is not available (already ended)."""
    meeting_code = "TESTCODE"
    meeting = Meeting(
        start_time=datetime.now(timezone.utc) - timedelta(hours=2),
        end_time=datetime.now(timezone.utc) - timedelta(minutes=1),
        meeting_code=meeting_code,
    )
    db_connection.add(meeting)
    db_connection.commit()

    with pytest.raises(ValueError, match="Meeting is not available"):
        checkin(db_connection, meeting.id, meeting_code)


def test_checkin_duplicate_token(db_connection: Session):
    """Test that check-in generates a unique token even if there's a collision."""
    meeting_code = "TESTCODE"
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(minutes=2),
        meeting_code=meeting_code,
    )
    db_connection.add(meeting)
    db_connection.commit()

    first_token = "TOKEN1"
    db_connection.add(
        Checkin(
            meeting_id=meeting.id,
            vote_token=first_token,
            timestamp=datetime.now(timezone.utc),
        )
    )
    db_connection.commit()

    # Second check-in with same code should generate a different token
    second_token = checkin(db_connection, meeting.id, meeting_code)
    assert second_token is not None
    assert first_token != second_token  # Tokens should be different

    # Verify both check-ins were recorded
    count = (
        db_connection.query(Checkin)
        .filter(
            Checkin.meeting_id == meeting.id,
            Checkin.vote_token.in_([first_token, second_token]),
        )
        .count()
    )
    assert count == 2


def test_get_elections_success(db_connection: Session):
    """Test retrieving the elections for a meeting."""
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE",
    )
    db_connection.add(meeting)
    db_connection.commit()

    # Add some elections and votes to test cascading deletes
    election1 = Election(meeting_id=meeting.id, name="Election 1")
    election2 = Election(meeting_id=meeting.id, name="Election 2")
    db_connection.add_all([election1, election2])
    db_connection.commit()

    # Add some votes
    votes = [
        ElectionVote(election_id=election1.id, vote_token="TOKEN1", vote="A"),
        ElectionVote(election_id=election1.id, vote_token="TOKEN2", vote="B"),
        ElectionVote(election_id=election2.id, vote_token="TOKEN1", vote="C"),
    ]
    db_connection.add_all(votes)
    db_connection.commit()

    # Get elections for the test meeting
    elections = get_elections(db_connection, meeting.id)

    # Should return a dict with two elections as set up in the test database
    assert isinstance(elections, dict)
    assert len(elections) == 2

    # Verify the election data
    count = 0
    for eid in elections:
        if eid == election1.id and election1.name == "Election 1":
            count += 1
        elif eid == election2.id and election2.name == "Election 2":
            count += 1
    assert count == 2


def test_get_elections_no_elections(db_connection: Session):
    """Test retrieving elections for a meeting with no elections."""
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE",
    )
    db_connection.add(meeting)
    db_connection.commit()

    # Get elections for the test meeting
    elections = get_elections(db_connection, meeting.id)
    assert elections == {}


def test_get_elections_nonexistent_meeting(db_connection: Session):
    """Test retrieving elections for a non-existent meeting."""
    non_existent_meeting_id = 999999
    elections = get_elections(db_connection, non_existent_meeting_id)
    assert elections == {}


def test_get_meeting_success(db_connection: Session):
    """Test retrieving a specific meeting."""
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE",
    )
    db_connection.add(meeting)
    db_connection.commit()

    m = get_meeting(db_connection, meeting.id)
    assert m is not None
    assert m["id"] == meeting.id
    assert m["start_time"] == meeting.start_time
    assert m["end_time"] == meeting.end_time
    assert m["meeting_code"] == meeting.meeting_code


def test_get_meeting_nonexistent_meeting(db_connection: Session):
    """Test retrieving a non-existent meeting."""
    non_existent_meeting_id = 999999
    meeting = get_meeting(db_connection, non_existent_meeting_id)
    assert meeting is None


def test_get_election_success(db_connection: Session):
    """Test successfully retrieving an election with votes."""
    # Create a meeting
    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(hours=2)
    meeting = Meeting(
        start_time=start_time,
        end_time=end_time,
        meeting_code="ABC123",
    )
    db_connection.add(meeting)
    db_connection.commit()

    # Create an election
    election = Election(meeting_id=meeting.id, name="Test Election")
    db_connection.add(election)
    db_connection.commit()

    # Create a check-in and vote
    vote_token = "test_token_123"
    checkin = Checkin(
        meeting_id=meeting.id,
        vote_token=vote_token,
        timestamp=datetime.now(timezone.utc),
    )
    db_connection.add(checkin)
    db_connection.commit()

    # Record a vote
    vote = ElectionVote(
        election_id=election.id,
        vote_token=vote_token,
        vote="A",
    )
    db_connection.add(vote)
    db_connection.commit()

    # Test getting the election
    result = get_election(db_connection, election.id)

    # Verify the result
    assert result is not None
    assert result["id"] == election.id
    assert result["name"] == "Test Election"
    assert result["meeting_id"] == meeting.id
    assert isinstance(result["votes"], dict)
    assert result["votes"]["A"] == 1  # One vote for A
    assert result["total_votes"] == 1  # Total votes should be 1


def test_get_election_no_votes(db_connection: Session):
    """Test retrieving an election with no votes."""
    # Create a meeting
    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(hours=2)
    meeting = Meeting(
        start_time=start_time,
        end_time=end_time,
        meeting_code="ABC123",
    )
    db_connection.add(meeting)
    db_connection.commit()

    # Create an election
    election = Election(meeting_id=meeting.id, name="Test Election No Votes")
    db_connection.add(election)
    db_connection.commit()

    # Test getting the election
    result = get_election(db_connection, election.id)

    # Verify the result
    assert result is not None
    assert result["id"] == election.id
    assert result["name"] == "Test Election No Votes"
    assert result["meeting_id"] == meeting.id
    assert isinstance(result["votes"], dict)
    assert result["total_votes"] == 0  # No votes should be recorded
    # Check that all vote options are present and set to 0
    for option in "ABCDEFGH":
        assert result["votes"][option] == 0


def test_get_nonexistent_election(db_connection: Session):
    """Test retrieving a non-existent election."""
    non_existent_election_id = 999999
    result = get_election(db_connection, non_existent_election_id)
    assert result is None


def test_get_election_with_multiple_votes(db_connection: Session):
    """Test retrieving an election with multiple votes."""
    # Create a meeting
    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(hours=2)
    meeting = Meeting(
        start_time=start_time,
        end_time=end_time,
        meeting_code="MULTIVOTE",
    )
    db_connection.add(meeting)
    db_connection.commit()

    # Create an election
    election = Election(meeting_id=meeting.id, name="Multi-Vote Election")
    db_connection.add(election)
    db_connection.commit()

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
        db_connection.add(checkin)
        db_connection.flush()  # Flush to get the checkin ID

        vote = ElectionVote(
            election_id=election.id,
            vote_token=vote_token,
            vote=vote_option,
        )
        db_connection.add(vote)

    db_connection.commit()

    # Test getting the election
    result = get_election(db_connection, election.id)

    # Verify the result
    assert result is not None
    assert result["id"] == election.id
    assert result["name"] == "Multi-Vote Election"
    assert result["meeting_id"] == meeting.id
    assert result["total_votes"] == 6  # Total votes should be 6

    # Verify vote counts
    assert result["votes"]["A"] == 3
    assert result["votes"]["B"] == 2
    assert result["votes"]["C"] == 1

    # Verify other options are 0
    for option in "DEFGH":
        assert result["votes"][option] == 0


def test_get_user_votes_success(db_connection: Session):
    """Test retrieving votes from a specific meeting."""
    # Create a new meeting
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE",
    )
    db_connection.add(meeting)
    db_connection.commit()

    # Add some elections and votes to test cascading deletes
    election1 = Election(meeting_id=meeting.id, name="Election 1")
    election2 = Election(meeting_id=meeting.id, name="Election 2")
    db_connection.add_all([election1, election2])
    db_connection.flush()

    # Add some check-ins
    db_connection.add_all(
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
    db_connection.commit()

    # Add some votes
    db_connection.add_all(
        [
            ElectionVote(election_id=election1.id, vote_token="TOKEN1", vote="A"),
            ElectionVote(election_id=election1.id, vote_token="TOKEN2", vote="B"),
            ElectionVote(election_id=election2.id, vote_token="TOKEN1", vote="C"),
        ]
    )
    db_connection.commit()

    votes = get_user_votes(db_connection, meeting.id, "TOKEN1")
    assert isinstance(votes, dict)
    assert len(votes) == 2
    assert election1.id in votes
    assert votes[election1.id]["name"] == "Election 1"
    assert votes[election1.id]["vote"] == "A"
    assert election2.id in votes
    assert votes[election2.id]["name"] == "Election 2"
    assert votes[election2.id]["vote"] == "C"


def test_get_user_votes_nonexistent_meeting(db_connection: Session):
    """Test retrieving votes from a specific meeting."""
    votes = get_user_votes(db_connection, 9999, "TOKEN1")
    assert len(votes) == 0


def test_get_user_votes_nonexistent_vote_token(db_connection: Session):
    """Test retrieving votes with a non-existent token."""
    # Create a new meeting
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE",
    )
    db_connection.add(meeting)
    db_connection.commit()

    # Add some elections and votes to test cascading deletes
    election1 = Election(meeting_id=meeting.id, name="Election 1")
    election2 = Election(meeting_id=meeting.id, name="Election 2")
    db_connection.add_all([election1, election2])
    db_connection.flush()

    # Add some check-ins
    db_connection.add_all(
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
    db_connection.commit()

    # Add some votes
    db_connection.add_all(
        [
            ElectionVote(election_id=election1.id, vote_token="TOKEN1", vote="A"),
            ElectionVote(election_id=election1.id, vote_token="TOKEN2", vote="B"),
            ElectionVote(election_id=election2.id, vote_token="TOKEN1", vote="C"),
        ]
    )
    db_connection.commit()
    non_existent_token = "NONEXISTENTTOKEN"
    votes = get_user_votes(db_connection, meeting.id, non_existent_token)
    assert votes == {}


def test_get_vote_counts(db_connection: Session):
    """Test getting vote counts."""
    meeting = Meeting(
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        meeting_code="TESTCODE",
    )
    db_connection.add(meeting)
    db_connection.commit()

    election = Election(meeting_id=meeting.id, name="Election 1")
    db_connection.add(election)
    db_connection.commit()

    # Add some votes
    db_connection.add_all(
        [
            ElectionVote(election_id=election.id, vote_token="TOKEN1", vote="A"),
            ElectionVote(election_id=election.id, vote_token="TOKEN2", vote="B"),
        ]
    )
    db_connection.commit()

    vote_counts = get_vote_counts(db_connection, election.id)
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


def test_vote_in_election_success(db_connection: Session):
    """Test successfully voting in an election."""
    # Create a meeting
    start_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    end_time = datetime.now(timezone.utc) + timedelta(hours=1)
    meeting = Meeting(
        start_time=start_time,
        end_time=end_time,
        meeting_code="ABC123",
    )
    db_connection.add(meeting)
    db_connection.commit()

    # Create an election
    election = Election(meeting_id=meeting.id, name="Test Election")
    db_connection.add(election)
    db_connection.commit()

    # Create a check-in
    vote_token = "test_token_123"
    checkin = Checkin(
        meeting_id=meeting.id,
        vote_token=vote_token,
        timestamp=datetime.now(timezone.utc),
    )
    db_connection.add(checkin)
    db_connection.commit()

    vote_in_election(
        db=db_connection,
        meeting_id=meeting.id,
        election_id=election.id,
        vote_token=vote_token,
        vote="A",
    )

    # Verify the vote was recorded
    vote = (
        db_connection.query(ElectionVote)
        .filter(
            ElectionVote.election_id == election.id,
            ElectionVote.vote_token == vote_token,
        )
        .one_or_none()
    )
    assert vote is not None
    assert vote.vote == "A"


def test_vote_in_election_invalid_election(db_connection: Session):
    """Test voting with an invalid election ID."""
    # Create a meeting
    start_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    end_time = datetime.now(timezone.utc) + timedelta(hours=1)
    meeting = Meeting(
        start_time=start_time,
        end_time=end_time,
        meeting_code="ABC123",
    )
    db_connection.add(meeting)
    db_connection.commit()

    # Create a check-in
    vote_token = "test_token_123"
    checkin = Checkin(
        meeting_id=meeting.id,
        vote_token=vote_token,
        timestamp=datetime.now(timezone.utc),
    )
    db_connection.add(checkin)
    db_connection.commit()

    with pytest.raises(ValueError, match="Invalid election"):
        vote_in_election(
            db=db_connection,
            meeting_id=meeting.id,
            election_id=999,  # Non-existent election
            vote_token=vote_token,
            vote="A",
        )


def test_vote_in_election_already_voted(db_connection: Session):
    """Test that a user cannot vote twice in the same election."""
    # Create a meeting
    start_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    end_time = datetime.now(timezone.utc) + timedelta(hours=1)
    meeting = Meeting(
        start_time=start_time,
        end_time=end_time,
        meeting_code="ABC123",
    )
    db_connection.add(meeting)
    db_connection.commit()

    # Create an election
    election = Election(meeting_id=meeting.id, name="Test Election")
    db_connection.add(election)
    db_connection.commit()

    # Create a check-in
    vote_token = "test_token_123"
    checkin = Checkin(
        meeting_id=meeting.id,
        vote_token=vote_token,
        timestamp=datetime.now(timezone.utc),
    )
    db_connection.add(checkin)
    db_connection.commit()

    # Record a vote
    vote = ElectionVote(
        election_id=election.id,
        vote_token=vote_token,
        vote="A",
    )
    db_connection.add(vote)
    db_connection.commit()

    # Try to vote again with the same token
    with pytest.raises(ValueError, match="already voted"):
        vote_in_election(
            db=db_connection,
            meeting_id=meeting.id,
            election_id=election.id,
            vote_token=vote_token,
            vote="B",  # Different vote
        )


def test_vote_in_election_invalid_token(db_connection: Session):
    """Test voting with an invalid token."""
    # Create a meeting
    start_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    end_time = datetime.now(timezone.utc) + timedelta(hours=1)
    meeting = Meeting(
        start_time=start_time,
        end_time=end_time,
        meeting_code="ABC123",
    )
    db_connection.add(meeting)
    db_connection.commit()

    # Create an election
    election = Election(meeting_id=meeting.id, name="Test Election")
    db_connection.add(election)
    db_connection.commit()

    # Try to vote with an invalid token
    with pytest.raises(ValueError, match="Invalid token"):
        vote_in_election(
            db=db_connection,
            meeting_id=meeting.id,
            election_id=election.id,
            vote_token="invalid_token",
            vote="A",
        )


def test_vote_in_election_meeting_ended(db_connection: Session):
    """Test that voting is not allowed after the meeting has ended."""
    # Create a meeting that has already ended
    start_time = datetime.now(timezone.utc) - timedelta(hours=2)
    end_time = datetime.now(timezone.utc) - timedelta(hours=1)
    meeting = Meeting(
        start_time=start_time,
        end_time=end_time,
        meeting_code="ABC123",
    )
    db_connection.add(meeting)
    db_connection.commit()

    # Create an election
    election = Election(meeting_id=meeting.id, name="Test Election")
    db_connection.add(election)
    db_connection.commit()

    # Create a check-in (even though meeting has ended, the check-in exists)
    vote_token = "test_token_123"
    checkin = Checkin(
        meeting_id=meeting.id,
        vote_token=vote_token,
        timestamp=datetime.now(timezone.utc),
    )
    db_connection.add(checkin)
    db_connection.commit()

    # Try to vote after meeting has ended
    with pytest.raises(ValueError, match="Voting has ended"):
        vote_in_election(
            db=db_connection,
            meeting_id=meeting.id,
            election_id=election.id,
            vote_token=vote_token,
            vote="A",
        )
