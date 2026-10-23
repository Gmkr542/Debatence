from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class Debate(Base):
    __tablename__ = "debates"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
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
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    debate = relationship("Debate", back_populates="arguments")
