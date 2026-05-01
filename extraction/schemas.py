from pydantic import BaseModel
from datetime import date, time
from typing import Optional


class Event(BaseModel):
    title: str
    description: Optional[str] = None
    organizer: str
    date: date
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    location_name: Optional[str] = None
    address: Optional[str] = None
    category: Optional[str] = None
    cost: Optional[str] = None
    language: Optional[str] = None
    source_url: Optional[str] = None
    source_platform: Optional[str] = None
    image_url: Optional[str] = None


class RawContent(BaseModel):
    organizer: str
    text: Optional[str] = None
    image_url: Optional[str] = None
    source_url: Optional[str] = None
    source_platform: str
    scraped_at: str