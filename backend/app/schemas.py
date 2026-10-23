from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class ArgumentCreate(BaseModel):
    author: str = Field(default="Debater", max_length=100)
    body: str = Field(min_length=1, max_length=10000)
    stance: str = "for"
    point_status: str = "needs_review"
    correctness: str = "unverified"
    evidence_name: Optional[str] = None
    evidence_url: Optional[str] = None

class ArgumentOut(ArgumentCreate):
    id: int
    debate_id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class DebateCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""

class DebateOut(BaseModel):
    id: int
    title: str
    description: str
    created_at: Optional[datetime] = None
    arguments: list[ArgumentOut] = []
    model_config = ConfigDict(from_attributes=True)
