"""活动日历 + CAS Schema（PRD §3.3 E-001 ~ E-203）。"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.common import CasType, EventStatus, OrganizerType


class EventCreateIn(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    cover_url: Optional[str] = None
    location: Optional[str] = Field(None, max_length=200)
    organizer_type: OrganizerType = OrganizerType.CLUB
    organizer_id: Optional[int] = None
    start_at: datetime
    end_at: datetime
    signup_deadline: Optional[datetime] = None
    max_participants: Optional[int] = None
    cas_type: Optional[CasType] = None


class EventOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    title: str
    description: Optional[str] = None
    cover_url: Optional[str] = None
    location: Optional[str] = None
    organizer_type: OrganizerType
    organizer_id: Optional[int] = None
    organizer_name: Optional[str] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    signup_deadline: Optional[datetime] = None
    max_participants: Optional[int] = None
    status: EventStatus = EventStatus.ACTIVE
    participant_count: int = 0
    cas_type: Optional[CasType] = None
    registered_by_me: bool = False
    is_waitlist: bool = False


class CalendarDay(BaseModel):
    date: str
    count: int = 0
    events: List[EventOut] = []


class CasRecordOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    event_id: Optional[int] = None
    title: str
    cas_type: CasType
    role: str = "participant"
    happened_at: Optional[datetime] = None
