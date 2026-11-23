from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    date: date
    time_in: Optional[time]
    # Additive fields (Phase 2): present but null when not applicable/unknown.
    time_out: Optional[time] = None
    status: str
    is_late: Optional[bool] = None
    is_early_leave: Optional[bool] = None
    created_at: datetime
