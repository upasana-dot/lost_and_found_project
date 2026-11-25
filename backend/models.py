from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

class ReportCreate(BaseModel):
    item: str = Field(min_length=1, max_length=100)
    colour: str = Field(min_length=1, max_length=40)
    place: str
    time: datetime
    building: str | None = None
    floor: str | None = None
    room: str | None = None
    location_name: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    brand: str | None = None
    description: str = ""
    image_url: str | None = None
    force: bool = False

class ReuniteRequest(BaseModel):
    matched_with: str
