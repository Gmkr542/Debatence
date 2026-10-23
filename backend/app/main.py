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
    arg_columns = {c['name'] for c in inspect(engine).get_columns('arguments')}
    for column, definition in {
        'ai_stance': 'VARCHAR(20)',
        'stance_match': 'VARCHAR(30)',
        'ai_confidence': 'VARCHAR(20)',
        'ai_analysis': 'TEXT',
        'ai_status': "VARCHAR(20) DEFAULT 'pending'",
    }.items():
        if column not in arg_columns:
            conn.execute(text(f'ALTER TABLE arguments ADD COLUMN {column} {definition}'))

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

@app.get("/api/debates/{debate_id}/role-requests/status", response_model=list[schemas.RoleRequestOut])
def role_request_status(debate_id: int, requester_id: str, db: Session = Depends(get_db)):
    if not db.query(models.Debate).filter(models.Debate.id == debate_id).first():
        raise HTTPException(404, "Debate not found")
    return db.query(models.DebateRoleRequest).filter(
        models.DebateRoleRequest.debate_id == debate_id,
        models.DebateRoleRequest.requester_id == requester_id
    ).order_by(models.DebateRoleRequest.created_at.desc()).all()

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

def analyze_argument_with_ai(topic: str, body: str, declared_stance: str):
    """Return transparent stance analysis; if no provider key is configured, mark unavailable."""
    import json
    import urllib.request
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"ai_stance": "unable_to_assess", "stance_match": "unavailable",
                "ai_confidence": "low", "ai_analysis": "AI analysis is not configured.",
                "ai_status": "unavailable"}
    prompt = f"""Analyze the argument stance, not factual truth. Debate topic: {topic}
Declared stance: {declared_stance}
Argument: {body}
Return JSON only with keys ai_stance (supports, opposes, unrelated, unclear),
stance_match (matches, differs, unclear), confidence (low, medium, high), explanation (brief).
Do not infer evidence verification from stance."""
    payload = {"model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
               "input": prompt, "text": {"format": {"type": "json_object"}}}
    try:
        req = urllib.request.Request("https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode(), headers={"Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=18) as response:
            data = json.loads(response.read().decode())
        out_text = data.get("output_text", "")
        parsed = json.loads(out_text)
        stance = parsed.get("ai_stance", "unclear")
        match = parsed.get("stance_match", "unclear")
        return {"ai_stance": stance, "stance_match": match,
                "ai_confidence": parsed.get("confidence", "low"),
                "ai_analysis": parsed.get("explanation", ""),
                "ai_status": "complete"}
    except Exception:
        return {"ai_stance": "unclear", "stance_match": "unavailable",
                "ai_confidence": "low", "ai_analysis": "AI stance analysis failed; retry later.",
                "ai_status": "failed"}

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
    debate = db.query(models.Debate).filter(models.Debate.id == debate_id).first()
    analysis = analyze_argument_with_ai(debate.title, payload.body, payload.stance)
    item = models.Argument(debate_id=debate_id, **payload.model_dump(), **analysis)
    db.add(item)
    # Reputation points reward contribution; author identity follows the current client profile convention.
    author_parts = (payload.author or "").split(" · ")
    if len(author_parts) >= 3:
        author_id = author_parts[2].strip()
        rep = db.query(models.UserReputation).filter_by(user_id=author_id).first()
        if not rep:
            rep = models.UserReputation(user_id=author_id, display_name=author_parts[0][:100], bio="", points=5)
            db.add(rep)
        else:
            rep.points += 5
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


# ---- Debate lifecycle, discovery, engagement, profiles and moderation ----
from sqlalchemy import func

@app.get("/api/discover")
def discover_debates(q: str = "", category: str = "", status: str = "", sort: str = "recent",
                     db: Session = Depends(get_db)):
    query = db.query(models.Debate)
    if q.strip():
        term = f"%{q.strip()}%"
        query = query.filter((models.Debate.title.ilike(term)) | (models.Debate.description.ilike(term)))
    if category and category != "All":
        query = query.filter(models.Debate.category == category)
    if status:
        query = query.filter(models.Debate.status == status)
    if sort == "active":
        query = query.outerjoin(models.Argument).group_by(models.Debate.id).order_by(func.count(models.Argument.id).desc())
    else:
        query = query.order_by(models.Debate.created_at.desc())
    return query.all()

@app.patch("/api/debates/{debate_id}")
def update_debate(debate_id: int, payload: schemas.DebateUpdate, initiator_id: str,
                  db: Session = Depends(get_db)):
    debate = db.query(models.Debate).filter(models.Debate.id == debate_id).first()
    if not debate: raise HTTPException(404, "Debate not found")
    if debate.creator_id != initiator_id: raise HTTPException(403, "Only the initiator can update this debate")
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in {"open", "paused", "completed"}:
        raise HTTPException(422, "status must be open, paused, or completed")
    if "debate_format" in data and data["debate_format"] not in {"Open discussion", "Oxford", "Lincoln-Douglas", "Policy", "Timed rounds"}:
        raise HTTPException(422, "Unsupported debate format")
    for key, value in data.items():
        setattr(debate, key, value)
    db.commit(); db.refresh(debate)
    return debate

@app.get("/api/debates/{debate_id}/stats", response_model=schemas.DebateStatsOut)
def debate_stats(debate_id: int, user_id: str = "", db: Session = Depends(get_db)):
    debate = db.query(models.Debate).filter(models.Debate.id == debate_id).first()
    if not debate: raise HTTPException(404, "Debate not found")
    return {"debate_id": debate_id,
            "upvotes": db.query(models.DebateVote).filter_by(debate_id=debate_id, vote="up").count(),
            "downvotes": db.query(models.DebateVote).filter_by(debate_id=debate_id, vote="down").count(),
            "comments": db.query(models.DebateComment).filter_by(debate_id=debate_id).count(),
            "bookmarked": bool(user_id and db.query(models.DebateBookmark).filter_by(debate_id=debate_id,user_id=user_id).first())}

@app.post("/api/debates/{debate_id}/vote")
def vote_debate(debate_id: int, payload: schemas.VoteCreate, db: Session = Depends(get_db)):
    if payload.vote not in {"up", "down"}: raise HTTPException(422, "vote must be up or down")
    if not db.query(models.Debate).filter_by(id=debate_id).first(): raise HTTPException(404, "Debate not found")
    row = db.query(models.DebateVote).filter_by(debate_id=debate_id,user_id=payload.user_id).first()
    if row and row.vote == payload.vote:
        db.delete(row); state = "removed"
    elif row:
        row.vote = payload.vote; state = "updated"
    else:
        db.add(models.DebateVote(debate_id=debate_id,user_id=payload.user_id,vote=payload.vote)); state = "added"
    db.commit()
    return {"status":state}

@app.post("/api/debates/{debate_id}/bookmark")
def toggle_bookmark(debate_id: int, user_id: str, db: Session = Depends(get_db)):
    if not db.query(models.Debate).filter_by(id=debate_id).first(): raise HTTPException(404, "Debate not found")
    row = db.query(models.DebateBookmark).filter_by(debate_id=debate_id,user_id=user_id).first()
    if row: db.delete(row); result = False
    else: db.add(models.DebateBookmark(debate_id=debate_id,user_id=user_id)); result = True
    db.commit()
    return {"bookmarked":result}

@app.get("/api/debates/{debate_id}/comments")
def list_comments(debate_id: int, db: Session = Depends(get_db)):
    if not db.query(models.Debate).filter_by(id=debate_id).first(): raise HTTPException(404, "Debate not found")
    return db.query(models.DebateComment).filter_by(debate_id=debate_id).order_by(models.DebateComment.created_at.asc()).all()

@app.post("/api/debates/{debate_id}/comments", status_code=201)
def create_comment(debate_id: int, payload: schemas.CommentCreate, db: Session = Depends(get_db)):
    debate = db.query(models.Debate).filter_by(id=debate_id).first()
    if not debate: raise HTTPException(404, "Debate not found")
    if debate.status != "open": raise HTTPException(409, "This debate is not open for comments")
    comment = models.DebateComment(debate_id=debate_id,user_id=payload.user_id,user_name=payload.user_name.strip(),body=payload.body.strip())
    db.add(comment); db.commit(); db.refresh(comment)
    return comment

@app.post("/api/debates/{debate_id}/report", status_code=201)
def report_content(debate_id: int, payload: schemas.ReportCreate, db: Session = Depends(get_db)):
    if not db.query(models.Debate).filter_by(id=debate_id).first(): raise HTTPException(404, "Debate not found")
    if payload.reason not in {"spam", "harassment", "misinformation", "abuse", "other"}:
        raise HTTPException(422, "Invalid report reason")
    if payload.argument_id and not db.query(models.Argument).filter_by(id=payload.argument_id,debate_id=debate_id).first():
        raise HTTPException(404, "Argument not found in this debate")
    row = models.ContentReport(debate_id=debate_id,argument_id=payload.argument_id,reporter_id=payload.reporter_id,
        reason=payload.reason,details=payload.details,status="open")
    db.add(row); db.commit(); db.refresh(row)
    return {"id":row.id,"status":row.status,"message":"Report received for moderator review"}

@app.get("/api/moderation/reports")
def moderation_reports(status: str = "open", db: Session = Depends(get_db)):
    return db.query(models.ContentReport).filter_by(status=status).order_by(models.ContentReport.created_at.asc()).all()

@app.patch("/api/moderation/reports/{report_id}")
def resolve_report(report_id: int, status: str, db: Session = Depends(get_db)):
    if status not in {"reviewed", "dismissed"}: raise HTTPException(422, "status must be reviewed or dismissed")
    report = db.query(models.ContentReport).filter_by(id=report_id).first()
    if not report: raise HTTPException(404, "Report not found")
    report.status = status; db.commit()
    return {"id":report.id,"status":report.status}

@app.put("/api/profile")
def update_profile(payload: schemas.ProfileUpdate, db: Session = Depends(get_db)):
    row = db.query(models.UserReputation).filter_by(user_id=payload.user_id).first()
    if not row:
        row = models.UserReputation(user_id=payload.user_id,display_name=payload.display_name.strip(),bio=payload.bio.strip(),points=0)
        db.add(row)
    else:
        row.display_name=payload.display_name.strip(); row.bio=payload.bio.strip()
    db.commit(); db.refresh(row)
    return row

@app.get("/api/profile/{user_id}")
def get_profile(user_id: str, db: Session = Depends(get_db)):
    row = db.query(models.UserReputation).filter_by(user_id=user_id).first()
    if row: return row
    args = db.query(models.Argument).filter(models.Argument.author.like(f"%{user_id}%")).count()
    return {"user_id":user_id,"display_name":"Debatence member","bio":"","points":args*5}

@app.get("/api/leaderboard")
def leaderboard(limit: int = 20, db: Session = Depends(get_db)):
    limit = min(max(limit,1),100)
    rows = db.query(models.UserReputation).order_by(models.UserReputation.points.desc()).limit(limit).all()
    return rows

@app.get("/api/notifications/{user_id}")
def notifications(user_id: str, db: Session = Depends(get_db)):
    # Notifications are derived from role requests and replies/mentions are future-proofed here.
    reqs = db.query(models.DebateRoleRequest).filter_by(requester_id=user_id).order_by(models.DebateRoleRequest.created_at.desc()).limit(30).all()
    return [{"id":r.id,"type":"role_request","status":r.status,"created_at":r.created_at,
             "message":f"Your request for debate #{r.debate_id} is {r.status}"} for r in reqs]
