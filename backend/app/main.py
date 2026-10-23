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
    debate = models.Debate(title=payload.title.strip(), description=payload.description.strip())
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
