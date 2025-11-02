"""Meeting model."""
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

from app.db.base import Base


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    meeting_code = Column(String(50), unique=True, nullable=False, index=True)

    # Relationships
    polls = relationship("Poll", back_populates="meeting", cascade="all, delete-orphan")
    checkins = relationship("Checkin", back_populates="meeting", cascade="all, delete-orphan")
