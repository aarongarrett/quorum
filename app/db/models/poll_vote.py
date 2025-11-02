"""PollVote model."""
from datetime import datetime, timezone as tz
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class PollVote(Base):
    __tablename__ = "poll_votes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    poll_id = Column(Integer, ForeignKey("polls.id", ondelete="CASCADE"), nullable=False)
    checkin_id = Column(Integer, ForeignKey("checkins.id", ondelete="CASCADE"), nullable=False)
    vote = Column(String(1), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz.utc))

    # Relationships
    poll = relationship("Poll", back_populates="votes")
    checkin = relationship("Checkin", back_populates="votes")

    __table_args__ = (
        Index("idx_poll_votes_poll", "poll_id"),
        Index("idx_poll_votes_checkin", "checkin_id"),
        UniqueConstraint("poll_id", "checkin_id", name="uq_poll_checkin"),
    )
