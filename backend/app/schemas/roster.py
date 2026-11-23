"""Schemas for reviewed class-roster imports."""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class RosterImportItem(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    roll_number: str = Field(min_length=1, max_length=64)
    email: EmailStr
    phone_number: Optional[str] = Field(default=None, max_length=32)


class RosterImportBatch(BaseModel):
    students: list[RosterImportItem] = Field(min_length=1, max_length=500)
