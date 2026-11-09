from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class BookingCreate(BaseModel):
    event_id: UUID


class HoldSeatRequest(BaseModel):
    seat_id: UUID


class VenueCreate(BaseModel):
    name: str
    address: str | None = None
    city: str | None = None
    capacity: int | None = Field(default=None, gt=0)


class VenueUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    city: str | None = None
    capacity: int | None = Field(default=None, gt=0)


class EventCreate(BaseModel):
    venue_id: UUID
    title: str
    description: str | None = None
    category: str | None = None
    image_url: str | None = None
    starts_at: datetime
    ends_at: datetime
    status: str = Field(default="draft", pattern="^(draft|published|cancelled)$")


class EventUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: str | None = None
    image_url: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    status: str | None = Field(default=None, pattern="^(draft|published|cancelled)$")


class SeatCreate(BaseModel):
    seat_label: str
    category: str = "general"
    price: float = Field(gt=0)


class SeatBulkCreate(BaseModel):
    seats: list[SeatCreate]


class SeatUpdate(BaseModel):
    category: str | None = None
    price: float | None = Field(default=None, gt=0)
