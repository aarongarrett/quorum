"""Checkin model."""
from datetime import datetime, timezone as tz
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class Checkin(Base):
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    token_lookup_key = Column(String(64), nullable=False, index=True)  # HMAC-SHA256 output (64 hex chars)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz.utc))

    # Relationships
    meeting = relationship("Meeting", back_populates="checkins")
    votes = relationship("PollVote", back_populates="checkin", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_checkins_meeting", "meeting_id"),
        UniqueConstraint("meeting_id", "token_lookup_key", name="uq_meeting_token"),
    )
