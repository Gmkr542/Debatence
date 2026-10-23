from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class Debate(Base):
    __tablename__ = "debates"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    status = Column(String(20), nullable=False, default="open")
    category = Column(String(80), nullable=False, default="General")
    debate_format = Column(String(40), nullable=False, default="Open discussion")
    duration_minutes = Column(Integer, nullable=False, default=0)
    creator_id = Column(String(100), nullable=True)
    creator_name = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    arguments = relationship("Argument", back_populates="debate", cascade="all, delete-orphan")

class Argument(Base):
    __tablename__ = "arguments"
    id = Column(Integer, primary_key=True, index=True)
    debate_id = Column(Integer, ForeignKey("debates.id", ondelete="CASCADE"), nullable=False)
    author = Column(String(100), nullable=False, default="Debater")
    body = Column(Text, nullable=False)
    stance = Column(String(10), nullable=False, default="for")
    point_status = Column(String(20), nullable=False, default="needs_review")
    correctness = Column(String(20), nullable=False, default="unverified")
    evidence_name = Column(String(255), nullable=True)
    evidence_url = Column(String(500), nullable=True)
    ai_stance = Column(String(20), nullable=True)
    stance_match = Column(String(30), nullable=True)
    ai_confidence = Column(String(20), nullable=True)
    ai_analysis = Column(Text, nullable=True)
    ai_status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    debate = relationship("Debate", back_populates="arguments")


class DebateRoleRequest(Base):
    __tablename__ = "debate_role_requests"
    id = Column(Integer, primary_key=True, index=True)
    debate_id = Column(Integer, ForeignKey("debates.id", ondelete="CASCADE"), nullable=False, index=True)
    requester_id = Column(String(100), nullable=False)
    requester_name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DebateMemberRole(Base):
    __tablename__ = "debate_member_roles"
    id = Column(Integer, primary_key=True, index=True)
    debate_id = Column(Integer, ForeignKey("debates.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(100), nullable=False)
    user_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default="Viewer")


class DebateVote(Base):
    __tablename__ = "debate_votes"
    id = Column(Integer, primary_key=True, index=True)
    debate_id = Column(Integer, ForeignKey("debates.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    vote = Column(String(10), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DebateBookmark(Base):
    __tablename__ = "debate_bookmarks"
    id = Column(Integer, primary_key=True, index=True)
    debate_id = Column(Integer, ForeignKey("debates.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DebateComment(Base):
    __tablename__ = "debate_comments"
    id = Column(Integer, primary_key=True, index=True)
    debate_id = Column(Integer, ForeignKey("debates.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    user_name = Column(String(100), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ContentReport(Base):
    __tablename__ = "content_reports"
    id = Column(Integer, primary_key=True, index=True)
    debate_id = Column(Integer, ForeignKey("debates.id", ondelete="CASCADE"), nullable=False, index=True)
    argument_id = Column(Integer, ForeignKey("arguments.id", ondelete="CASCADE"), nullable=True, index=True)
    reporter_id = Column(String(100), nullable=False)
    reason = Column(String(40), nullable=False)
    details = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="open")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class UserReputation(Base):
    __tablename__ = "user_reputation"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, unique=True, index=True)
    display_name = Column(String(100), nullable=False)
    bio = Column(String(500), nullable=False, default="")
    points = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
