"""OMEGA / NFC Schema（OMEGA 文档 §8.1）。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.common import DeviceType, NfcLocationType, NfcTargetType


class NfcCardOut(BaseModel):
    model_config = {"from_attributes": True}

    card_id: str
    target_type: NfcTargetType
    target_id: Optional[int] = None
    target_url: Optional[str] = None
    location_desc: Optional[str] = None
    location_type: Optional[NfcLocationType] = None
    is_active: bool = True


class NfcTapIn(BaseModel):
    card_id: str = Field(..., min_length=1, max_length=50)
    device_type: DeviceType = DeviceType.UNKNOWN
    app_installed: bool = False


class NfcCardRegisterIn(BaseModel):
    card_id: str = Field(..., min_length=1, max_length=50)
    card_uid: Optional[str] = Field(None, max_length=50)
    location_desc: Optional[str] = Field(None, max_length=200)
    location_type: Optional[NfcLocationType] = None
    target_type: NfcTargetType = NfcTargetType.DOWNLOAD
    target_id: Optional[int] = None
    poster_batch: Optional[str] = Field(None, max_length=50)


class NfcCardAdminOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    card_id: str
    card_uid: Optional[str] = None
    location_desc: Optional[str] = None
    location_type: Optional[NfcLocationType] = None
    target_type: NfcTargetType
    target_id: Optional[int] = None
    is_active: bool = True
    poster_batch: Optional[str] = None
    deployed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    tap_count: int = 0
    unique_user_count: int = 0


class NfcCheckinOut(BaseModel):
    unique_cards: int = 0
    total_taps: int = 0
    cards: list = []
