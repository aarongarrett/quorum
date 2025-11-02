"""Poll model."""
from sqlalchemy import Column, Integer, String, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.db.base import Base


class Poll(Base):
    __tablename__ = "polls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)

    # Relationships
    meeting = relationship("Meeting", back_populates="polls")
    votes = relationship("PollVote", back_populates="poll", cascade="all, delete-orphan")

    __table_args__ = (Index("idx_polls_meeting", "meeting_id"),)
