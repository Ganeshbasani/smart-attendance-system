from datetime import date, time
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

LeaveType = Literal["annual", "sick", "other"]


class ShiftCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    start_time: time
    end_time: time
    grace_minutes: int = Field(default=0, ge=0, le=120)

    @model_validator(mode="after")
    def end_after_start(self):
        # Overnight shifts are not supported by the late/early calculations.
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be later than start_time")
        return self


class ShiftUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    grace_minutes: Optional[int] = Field(default=None, ge=0, le=120)
    is_active: Optional[bool] = None

    @model_validator(mode="after")
    def end_after_start(self):
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.end_time <= self.start_time
        ):
            raise ValueError("end_time must be later than start_time")
        return self


class HolidayCreate(BaseModel):
    date: date
    name: str = Field(min_length=1, max_length=120)


class LeaveRequestCreate(BaseModel):
    start_date: date
    end_date: date
    leave_type: LeaveType = "annual"
    reason: Optional[str] = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def range_valid(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self


class CorrectionRequestCreate(BaseModel):
    attendance_id: int
    proposed_status: Literal["present", "absent"]
    proposed_time_in: Optional[time] = None
    reason: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def time_only_for_present(self):
        if self.proposed_status == "absent" and self.proposed_time_in is not None:
            raise ValueError("time_in only applies when proposing 'present'")
        return self


class ReviewRequest(BaseModel):
    """Admin decision on a leave/correction request. Note required on reject."""
    note: Optional[str] = Field(default=None, max_length=1000)


class ShiftAssignment(BaseModel):
    """Assign (or clear, with null) a shift to a user."""
    shift_id: Optional[int] = None
