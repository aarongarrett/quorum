from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import TEXT, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator


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


class Base(DeclarativeBase):
    pass


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    start_time: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    meeting_code: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    # Relationships
    elections: Mapped[list["Election"]] = relationship(
        "Election", back_populates="meeting", cascade="all, delete-orphan"
    )
    checkins: Mapped[list["Checkin"]] = relationship(
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


class Election(Base):
    __tablename__ = "elections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)

    # Relationships
    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="elections")
    votes: Mapped[list["ElectionVote"]] = relationship(
        "ElectionVote", back_populates="election", cascade="all, delete-orphan"
    )


class Checkin(Base):
    __tablename__ = "checkins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        TZDateTime, nullable=False, default=datetime.now(timezone.utc)
    )
    vote_token: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    # Relationships
    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="checkins")


class ElectionVote(Base):
    __tablename__ = "election_votes"
    __table_args__ = (
        Index(
            "ix_election_votes_election_id_vote_token",
            "election_id",
            "vote_token",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    election_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("elections.id", ondelete="CASCADE"), nullable=False
    )
    vote: Mapped[str] = mapped_column(String(1), nullable=False)
    vote_token: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        TZDateTime, nullable=False, default=datetime.now(timezone.utc)
    )

    # Relationships
    election: Mapped["Election"] = relationship("Election", back_populates="votes")


# Create indexes for better performance

Checkin.meeting_id_index = Index("idx_checkins_meeting", Checkin.meeting_id)
ElectionVote.election_id_index = Index(
    "idx_election_votes_election", ElectionVote.election_id
)
ElectionVote.token_index = Index("idx_election_votes_token", ElectionVote.vote_token)
