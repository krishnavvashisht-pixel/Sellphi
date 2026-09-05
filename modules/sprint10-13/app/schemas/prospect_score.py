from typing import List
from pydantic import BaseModel, Field
class ProspectScore(BaseModel):
    score: int = Field(..., ge=0, le=100); grade: str = Field(...); reasons: List[str] = Field(default_factory=list); confidence: int = Field(..., ge=0, le=100)
