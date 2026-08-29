from pydantic import BaseModel
from typing import Optional

class Scene(BaseModel):
    scene_id: str
    screenplay_id: str
    number: int
    heading: str
    interior_ext: Optional[str] = None
    location: Optional[str] = None
    time_of_day: Optional[str] = None
    raw_text: str
    page_start: int
    page_end: int
