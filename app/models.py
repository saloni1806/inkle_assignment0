from pydantic import BaseModel
from typing import List, Optional

class PlanRequest(BaseModel):
    place: str
    tasks: Optional[List[str]] = None  # e.g. ["weather","places"]

class PlaceInfo(BaseModel):
    name: str
    type: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
