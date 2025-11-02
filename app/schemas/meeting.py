"""Meeting schemas."""
from datetime import datetime
from typing import List
from pydantic import BaseModel

from app.schemas.poll import PollDetail, PollWithVote


class MeetingCreate(BaseModel):
    start_time: datetime
    end_time: datetime


class MeetingResponse(BaseModel):
    meeting_id: int
    meeting_code: str


class MeetingDetail(BaseModel):
    id: int
    start_time: str
    end_time: str
    meeting_code: str
    checkins: int
    polls: List[PollDetail]


class AvailableMeeting(BaseModel):
    id: int
    start_time: str
    end_time: str
    meeting_code: str
    checked_in: bool
    polls: List[PollWithVote]


class AdminMeetingDetail(BaseModel):
    id: int
    start_time: str
    end_time: str
    meeting_code: str
    checkins: int
    polls: List[PollDetail]
