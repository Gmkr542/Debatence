import os
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from .database import Base, engine, get_db
from . import models, schemas

Base.metadata.create_all(bind=engine)
# Additive migration for existing deployments.
from sqlalchemy import inspect, text
with engine.begin() as conn:
    columns = {c['name'] for c in inspect(engine).get_columns('debates')}
    if 'creator_id' not in columns:
        conn.execute(text('ALTER TABLE debates ADD COLUMN creator_id VARCHAR(100)'))
    if 'creator_name' not in columns:
        conn.execute(text('ALTER TABLE debates ADD COLUMN creator_name VARCHAR(100)'))

app = FastAPI(title="Debatence API", version="1.0.0")
origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware, allow_origins=origins, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/debates", response_model=list[schemas.DebateOut])
def list_debates(db: Session = Depends(get_db)):
    return db.query(models.Debate).order_by(models.Debate.created_at.desc()).all()

@app.post("/api/debates", response_model=schemas.DebateOut, status_code=201)
def create_debate(payload: schemas.DebateCreate, db: Session = Depends(get_db)):
    debate = models.Debate(title=payload.title.strip(), description=payload.description.strip(), creator_id=payload.creator_id, creator_name=payload.creator_name)
    db.add(debate)
    db.commit()
    db.refresh(debate)
    return debate


@app.delete("/api/debates/{debate_id}", status_code=204)
def delete_debate(debate_id: int, db: Session = Depends(get_db)):
    """Delete a debate and its associated arguments."""
    debate = db.query(models.Debate).filter(models.Debate.id == debate_id).first()
    if not debate:
        raise HTTPException(404, "Debate not found")
    db.delete(debate)
    db.commit()
    return None

@app.get("/api/debates/{debate_id}", response_model=schemas.DebateOut)
def get_debate(debate_id: int, db: Session = Depends(get_db)):
    debate = db.query(models.Debate).filter(models.Debate.id == debate_id).first()
    if not debate:
        raise HTTPException(404, "Debate not found")
    return debate



@app.post("/api/debates/{debate_id}/role-requests", response_model=schemas.RoleRequestOut, status_code=201)
def submit_role_request(debate_id: int, payload: schemas.RoleRequestCreate, db: Session = Depends(get_db)):
    debate = db.query(models.Debate).filter(models.Debate.id == debate_id).first()
    if not debate:
        raise HTTPException(404, "Debate not found")
    if payload.requester_id == debate.creator_id:
        raise HTTPException(400, "Debate creator already has the Initiator role")
    existing = db.query(models.DebateRoleRequest).filter(
        models.DebateRoleRequest.debate_id == debate_id,
        models.DebateRoleRequest.requester_id == payload.requester_id,
        models.DebateRoleRequest.status == "pending"
    ).first()
    if existing:
        return existing
    req = models.DebateRoleRequest(debate_id=debate_id, requester_id=payload.requester_id,
        requester_name=payload.requester_name.strip(), status="pending")
    db.add(req); db.commit(); db.refresh(req)
    return req

@app.get("/api/debates/{debate_id}/role-requests", response_model=list[schemas.RoleRequestOut])
def list_role_requests(debate_id: int, initiator_id: str, db: Session = Depends(get_db)):
    debate = db.query(models.Debate).filter(models.Debate.id == debate_id).first()
    if not debate:
        raise HTTPException(404, "Debate not found")
    if not debate.creator_id or debate.creator_id != initiator_id:
        raise HTTPException(403, "Only the debate initiator can manage role requests")
    return db.query(models.DebateRoleRequest).filter(
        models.DebateRoleRequest.debate_id == debate_id,
        models.DebateRoleRequest.status == "pending"
    ).order_by(models.DebateRoleRequest.created_at.asc()).all()

@app.post("/api/debates/{debate_id}/role-requests/{request_id}/decision", response_model=schemas.RoleRequestOut)
def decide_role_request(debate_id: int, request_id: int, payload: schemas.RoleDecision, db: Session = Depends(get_db)):
    debate = db.query(models.Debate).filter(models.Debate.id == debate_id).first()
    if not debate:
        raise HTTPException(404, "Debate not found")
    if not debate.creator_id or debate.creator_id != payload.initiator_id:
        raise HTTPException(403, "Only the debate initiator can manage role requests")
    if payload.decision not in {"approve", "reject"}:
        raise HTTPException(422, "Decision must be approve or reject")
    req = db.query(models.DebateRoleRequest).filter(
        models.DebateRoleRequest.id == request_id,
        models.DebateRoleRequest.debate_id == debate_id,
        models.DebateRoleRequest.status == "pending"
    ).first()
    if not req:
        raise HTTPException(404, "Pending role request not found")
    req.status = "approved" if payload.decision == "approve" else "rejected"
    if payload.decision == "approve":
        member = db.query(models.DebateMemberRole).filter(
            models.DebateMemberRole.debate_id == debate_id,
            models.DebateMemberRole.user_id == req.requester_id
        ).first()
        if member:
            member.role = "Debater"; member.user_name = req.requester_name
        else:
            db.add(models.DebateMemberRole(debate_id=debate_id, user_id=req.requester_id,
                user_name=req.requester_name, role="Debater"))
    db.commit(); db.refresh(req)
    return req

@app.get("/api/debates/{debate_id}/role", response_model=schemas.DebateRoleOut)
def get_debate_role(debate_id: int, user_id: str, db: Session = Depends(get_db)):
    debate = db.query(models.Debate).filter(models.Debate.id == debate_id).first()
    if not debate:
        raise HTTPException(404, "Debate not found")
    if debate.creator_id == user_id:
        return {"role": "Initiator"}
    member = db.query(models.DebateMemberRole).filter(
        models.DebateMemberRole.debate_id == debate_id,
        models.DebateMemberRole.user_id == user_id
    ).first()
    return {"role": member.role if member else "Viewer"}

@app.post("/api/debates/{debate_id}/arguments", response_model=schemas.ArgumentOut, status_code=201)
def create_argument(debate_id: int, payload: schemas.ArgumentCreate, db: Session = Depends(get_db)):
    if not db.query(models.Debate).filter(models.Debate.id == debate_id).first():
        raise HTTPException(404, "Debate not found")
    if payload.stance not in {"for", "against"}:
        raise HTTPException(422, "stance must be for or against")
    if payload.point_status not in {"valid", "invalid", "needs_review"}:
        raise HTTPException(422, "Invalid point_status")
    if payload.correctness not in {"correct", "incorrect", "unverified"}:
        raise HTTPException(422, "Invalid correctness")
    item = models.Argument(debate_id=debate_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@app.post("/api/evidence", status_code=201)
async def upload_evidence(file: UploadFile = File(...)):
    allowed = {".pdf", ".png", ".jpg", ".jpeg", ".txt", ".doc", ".docx"}
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in allowed:
        raise HTTPException(400, "Unsupported file type")
    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(413, "File exceeds 15 MB limit")
    safe_name = f"{uuid4().hex}{suffix}"
    (UPLOAD_DIR / safe_name).write_bytes(content)
    return {"filename": file.filename, "url": f"/uploads/{safe_name}"}
