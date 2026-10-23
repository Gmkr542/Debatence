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
    ai_stance: Optional[str] = None
    stance_match: Optional[str] = None
    ai_confidence: Optional[str] = None
    ai_analysis: Optional[str] = None
    ai_status: str = "pending"

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
    category: str = Field(default="General", max_length=80)
    debate_format: str = Field(default="Open discussion", max_length=40)
    duration_minutes: int = Field(default=0, ge=0, le=1440)

class DebateOut(BaseModel):
    id: int
    title: str
    description: str
    status: str = "open"
    category: str = "General"
    debate_format: str = "Open discussion"
    duration_minutes: int = 0
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


class RoleRequestStatusOut(BaseModel):
    id: int
    status: str
    debate_id: int
    model_config = ConfigDict(from_attributes=True)


class DebateUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=10000)
    status: Optional[str] = None
    category: Optional[str] = Field(default=None, max_length=80)
    format: Optional[str] = Field(default=None, max_length=40)

class VoteCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    vote: str

class CommentCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    user_name: str = Field(min_length=1, max_length=100)
    body: str = Field(min_length=1, max_length=3000)

class ReportCreate(BaseModel):
    reporter_id: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=40)
    details: Optional[str] = Field(default=None, max_length=2000)
    argument_id: Optional[int] = None

class ProfileUpdate(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    display_name: str = Field(min_length=1, max_length=100)
    bio: str = Field(default="", max_length=500)

class DebateStatsOut(BaseModel):
    debate_id: int
    upvotes: int
    downvotes: int
    comments: int
    bookmarked: bool
