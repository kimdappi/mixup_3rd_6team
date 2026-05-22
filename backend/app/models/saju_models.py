from typing import Optional

from pydantic import BaseModel, Field


class SajuRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=20)
    year: int = Field(..., ge=1900, le=2100)
    month: int = Field(..., ge=1, le=12)
    day: int = Field(..., ge=1, le=31)
    hour: int = Field(0, ge=0, le=23)
    minute: int = Field(0, ge=0, le=59)
    city: Optional[str] = "서울"
    address: str


class MatchDetail(BaseModel):
    factor: str
    points: int


class SajuResponse(BaseModel):
    saju_pillars: str
    oheng_distribution: dict[str, int]
    lacking_oheng: list[str]
    match_score: int
    match_grade: str
    match_details: list[MatchDetail]
    conversational: str
    disclaimer: str
