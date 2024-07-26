from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MovieModel(BaseModel):
    id: str
    url: str
    priority: float

    name: str
    english_name: str
    keywords: list[str]
    description: str
    year: Optional[int]
    premiere: datetime
    scrape_date: Optional[datetime] = Field(default_factory=datetime.utcnow, alias='scrape_date')
    image_url: Optional[str]
