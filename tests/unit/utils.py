from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Checkin, Election, ElectionVote, Meeting


def setup_test_data(session: Session, test_data: dict) -> None:
    """Set up test data in the database using SQLAlchemy ORM

    Args:
        session: SQLAlchemy session
        test_data: Dictionary containing test data
    """
    # Create test meeting
    meeting = Meeting(
        start_time=test_data["start_time"],
        end_time=test_data["end_time"],
        meeting_code=test_data["meeting_code"],
    )
    session.add(meeting)
    session.flush()  # Flush to get the ID
    test_data["meeting_id"] = meeting.id

    # Create past meeting that's not happening now
    past_meeting = Meeting(
        start_time=test_data["past_start_time"],
        end_time=test_data["past_end_time"],
        meeting_code=test_data["past_meeting_code"],
    )
    session.add(past_meeting)
    session.flush()
    test_data["past_meeting_id"] = past_meeting.id

    # Create empty meeting with no elections
    empty_meeting = Meeting(
        start_time=test_data["start_time"],
        end_time=test_data["end_time"],
        meeting_code=test_data["empty_meeting_code"],
    )
    session.add(empty_meeting)
    session.flush()  # Flush to get the ID
    test_data["empty_meeting_id"] = empty_meeting.id

    # Create test election
    election = Election(
        meeting_id=test_data["meeting_id"], name=test_data["election_name"]
    )
    session.add(election)
    session.flush()
    test_data["election_id"] = election.id

    # Create past election
    election = Election(
        meeting_id=test_data["past_meeting_id"], name=test_data["past_election_name"]
    )
    session.add(election)
    session.flush()
    test_data["past_election_id"] = election.id

    # Create election to be deleted
    delete_election = Election(
        meeting_id=test_data["meeting_id"], name=test_data["delete_election_name"]
    )
    session.add(delete_election)
    session.flush()
    test_data["delete_election_id"] = delete_election.id

    # Create test checkin
    checkin = Checkin(
        meeting_id=test_data["meeting_id"],
        token=test_data["test_token"],
        timestamp=datetime.now(),
    )
    session.add(checkin)
    session.flush()
    test_data["checkin_id"] = checkin.id

    # Create test checkin
    checkin = Checkin(
        meeting_id=test_data["past_meeting_id"],
        token=test_data["past_token"],
        timestamp=datetime.now(),
    )
    session.add(checkin)
    session.flush()
    test_data["past_checkin_id"] = checkin.id

    # Create test election vote
    vote = ElectionVote(
        election_id=test_data["election_id"],
        token=test_data["test_token"],
        vote=test_data["test_vote"],
    )
    session.add(vote)

    session.commit()


def cleanup_test_data(session: Session, test_data: Optional[dict] = None) -> None:
    """Clean up test data from the database using SQLAlchemy ORM

    Args:
        session: SQLAlchemy session
        test_data: Optional test data dictionary (unused in this implementation)
    """
    # Clear all data from tables in reverse order of dependencies
    session.query(ElectionVote).delete()
    session.query(Checkin).delete()
    session.query(Election).delete()
    session.query(Meeting).delete()
    session.commit()
