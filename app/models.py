from datetime import datetime, timezone

from .database import db


class Meeting(db.Model):
    __tablename__ = "meetings"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    start_time = db.Column(db.DateTime(timezone=True), nullable=False)
    end_time = db.Column(db.DateTime(timezone=True), nullable=False)
    meeting_code = db.Column(db.String, unique=True, nullable=False)

    # Relationships
    polls = db.relationship(
        "Poll", back_populates="meeting", cascade="all, delete-orphan"
    )
    checkins = db.relationship(
        "Checkin", back_populates="meeting", cascade="all, delete-orphan"
    )


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
    __table_args__ = (db.Index("idx_checkins_meeting", "meeting_id"),)

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    meeting_id = db.Column(
        db.Integer, db.ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    timestamp = db.Column(
        db.DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc)
    )
    vote_token = db.Column(db.String, unique=True, nullable=False)

    # Relationships
    meeting = db.relationship("Meeting", back_populates="checkins")


class PollVote(db.Model):
    __tablename__ = "poll_votes"
    __table_args__ = (
        db.Index(
            "ix_poll_votes_poll_id_vote_token",
            "poll_id",
            "vote_token",
            unique=True,
        ),
        db.Index("idx_poll_votes_poll", "poll_id"),
        db.Index("idx_poll_votes_token", "vote_token"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    poll_id = db.Column(
        db.Integer, db.ForeignKey("polls.id", ondelete="CASCADE"), nullable=False
    )
    vote = db.Column(db.String(1), nullable=False)
    vote_token = db.Column(db.String, nullable=False)
    timestamp = db.Column(
        db.DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc)
    )

    # Relationships
    poll = db.relationship("Poll", back_populates="votes")
