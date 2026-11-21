"""Schemas for attendance sessions and the decision engine (API v1)."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

DecisionOutcome = Literal["VERIFIED", "REVIEW_REQUIRED", "REJECTED", "DUPLICATE", "MANUAL_OVERRIDE"]


class SessionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    class_section_id: Optional[int] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    class_section_id: Optional[int] = None
    status: str
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    started_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    created_at: datetime


class DecisionRequest(BaseModel):
    """Signals produced by the kiosk pipeline for one student."""
    user_id: int = Field(gt=0)
    confidence: float = Field(ge=0, le=100)
    quality_score: float = Field(ge=0, le=100)
    liveness_ok: bool
    spoof_suspected: bool = False
    model_version: Optional[str] = None


class DecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    session_id: int
    user_id: int
    decision: str
    confidence: Optional[float] = None
    quality_score: Optional[float] = None
    liveness_ok: Optional[bool] = None
    reason: Optional[str] = None
    marked_at: datetime


class ManualOverrideRequest(BaseModel):
    user_id: int = Field(gt=0)
    # VERIFIED or REVIEW_REQUIRED are the only sensible manual outcomes here;
    # explicit reason is mandatory and audited.
    decision: Literal["VERIFIED", "REVIEW_REQUIRED", "REJECTED"] = "VERIFIED"
    reason: str = Field(min_length=3, max_length=1000)


class ReviewRequestManual(BaseModel):
    decision: Literal["VERIFIED", "REJECTED"]
    reason: str = Field(min_length=3, max_length=1000)


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    session_id: Optional[int] = None
    user_id: Optional[int] = None
    user_unique_id: Optional[str] = None
    event_type: str
    decision: str
    confidence: Optional[float] = None
    quality_score: Optional[float] = None
    liveness_ok: Optional[bool] = None
    model_version: Optional[str] = None
    threshold: Optional[float] = None
    reason: Optional[str] = None
    created_at: datetime
