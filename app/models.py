from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import TEXT, DateTime, Index
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import TypeDecorator

from .database import db


class TZDateTime(TypeDecorator):
    """
    - SQLite -> TEXT storing full ISO8601 (with offset)
    - Postgres -> TIMESTAMP WITH TIME ZONE
    - Others -> DateTime(timezone=True)
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "sqlite":
            return dialect.type_descriptor(TEXT())
        else:
            # Use the native timestamptz on Postgres, or DateTime(timezone=True) elsewhere
            return dialect.type_descriptor(
                postgresql.TIMESTAMP(timezone=True)
                if dialect.name == "postgresql"
                else DateTime(timezone=True)
            )

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "sqlite":
            if value.tzinfo is None:
                raise ValueError("Naive datetime cannot be stored in TZDateTime")
            return value.isoformat()
        # On Postgres/others, leave it as a datetime and let the driver handle it
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "sqlite":
            return datetime.fromisoformat(value)
        # On Postgres/others, SQLAlchemy will already return an aware datetime
        return value


class Meeting(db.Model):
    __tablename__ = "meetings"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    start_time = db.Column(TZDateTime, nullable=False)
    end_time = db.Column(TZDateTime, nullable=False)
    meeting_code = db.Column(db.String, unique=True, nullable=False)

    # Relationships
    polls = db.relationship(
        "Poll", back_populates="meeting", cascade="all, delete-orphan"
    )
    checkins = db.relationship(
        "Checkin", back_populates="meeting", cascade="all, delete-orphan"
    )

    @property
    def is_available(self, current_time: Optional[datetime] = None) -> bool:
        """Check if the meeting is currently available for check-in."""
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        # Allow check-in 15 minutes before and 15 minutes after start
        checkin_start = self.start_time - timedelta(minutes=15)

        return checkin_start <= current_time <= self.end_time


class Poll(db.Model):
    __tablename__ = "polls"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    meeting_id = db.Column(
        db.Integer, db.ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    name = db.Column(db.String, nullable=False)

    # Relationships
    meeting = db.relationship("Meeting", back_populates="polls")
    votes = db.relationship(
        "PollVote", back_populates="poll", cascade="all, delete-orphan"
    )


class Checkin(db.Model):
    __tablename__ = "checkins"
    __table_args__ = (Index("idx_checkins_meeting", "meeting_id"),)

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    meeting_id = db.Column(
        db.Integer, db.ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    timestamp = db.Column(
        TZDateTime, nullable=False, default=datetime.now(timezone.utc)
    )
    vote_token = db.Column(db.String, unique=True, nullable=False)

    # Relationships
    meeting = db.relationship("Meeting", back_populates="checkins")


class PollVote(db.Model):
    __tablename__ = "poll_votes"
    __table_args__ = (
        Index(
            "ix_poll_votes_poll_id_vote_token",
            "poll_id",
            "vote_token",
            unique=True,
        ),
        Index("idx_poll_votes_poll", "poll_id"),
        Index("idx_poll_votes_token", "vote_token"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    poll_id = db.Column(
        db.Integer, db.ForeignKey("polls.id", ondelete="CASCADE"), nullable=False
    )
    vote = db.Column(db.String(1), nullable=False)
    vote_token = db.Column(db.String, nullable=False)
    timestamp = db.Column(
        TZDateTime, nullable=False, default=datetime.now(timezone.utc)
    )

    # Relationships
    poll = db.relationship("Poll", back_populates="votes")
