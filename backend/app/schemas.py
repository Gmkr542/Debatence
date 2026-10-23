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
    creator_id: Optional[str] = Field(default=None, max_length=100)
    creator_name: Optional[str] = Field(default=None, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    description: str = ""

class DebateOut(BaseModel):
    id: int
    title: str
    description: str
    creator_id: Optional[str] = None
    creator_name: Optional[str] = None
    created_at: Optional[datetime] = None
    arguments: list[ArgumentOut] = []
    model_config = ConfigDict(from_attributes=True)


class RoleRequestCreate(BaseModel):
    requester_id: str = Field(min_length=1, max_length=100)
    requester_name: str = Field(min_length=1, max_length=100)

class RoleRequestOut(BaseModel):
    id: int
    debate_id: int
    requester_id: str
    requester_name: str
    status: str
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class RoleDecision(BaseModel):
    initiator_id: str = Field(min_length=1, max_length=100)
    decision: str

class DebateRoleOut(BaseModel):
    role: str
