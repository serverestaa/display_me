
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Query, Path
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse, JSONResponse
from datetime import datetime
from database import get_db
from config import settings
from models import User
from models import FeedbackSession, FeedbackReview, FeedbackComment
from schemas import (
    FeedbackSessionCreate, FeedbackSessionRead,
    FeedbackReviewUpsert, FeedbackReviewOut, FeedbackCommentOut
)

from fastapi import Response, Request
from starlette.responses import StreamingResponse
import requests

from utils import get_current_user
from gcs import upload_fileobj, generate_signed_url, make_object_name
import os, uuid, json, shutil

router = APIRouter(prefix="/feedback-sessions", tags=["feedback-sessions"])

HEX10 = r"^[a-f0-9]{10}$"

@router.post("", response_model=FeedbackSessionRead)
def create_session(
    payload: FeedbackSessionCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    from uuid import uuid4
    sess = FeedbackSession(
        owner_id=current.id,
        title=payload.title,
        slug=uuid4().hex[:10],
        # pdf_object remains None until upload
    )
    db.add(sess); db.commit(); db.refresh(sess)
    # pdf_url blank until we actually have a file; or return endpoint that will 404 until upload
    return FeedbackSessionRead(
        id=sess.id, title=sess.title, slug=sess.slug, token=sess.token,
        is_open=sess.is_open, pdf_url=""
    )

# === NEW: list my sessions (owner only) ===
@router.get("/mine")
def list_my_sessions(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    sessions = (
        db.query(FeedbackSession)
        .filter(FeedbackSession.owner_id == current.id)
        .order_by(FeedbackSession.created_at.desc())
        .all()
    )
    out = []
    for s in sessions:
        submitted = sum(1 for r in s.reviews if r.submitted_at is not None)
        out.append({
            "id": s.id,
            "title": s.title,
            "slug": s.slug,
            "token": s.token,
            "is_open": s.is_open,
            "created_at": s.created_at.isoformat(),
            "reviews_total": len(s.reviews),
            "reviews_submitted": submitted,
            "owner_pdf_url": f"/resume/feedback-sessions/{s.slug}/pdf?t={s.token}" if s.pdf_object else None,
        })
    return out


@router.get("/{slug}/owner", response_model=FeedbackSessionRead)
def get_session_owner(
    slug: str = Path(..., pattern=HEX10),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    sess = db.query(FeedbackSession).filter(FeedbackSession.slug == slug).first()
    if not sess: raise HTTPException(404, "Session not found")
    if sess.owner_id != current.id: raise HTTPException(403, "Forbidden")

    pdf_endpoint = f"/resume/feedback-sessions/{slug}/pdf?t={sess.token}" if sess.pdf_object else ""
    return FeedbackSessionRead(
        id=sess.id, title=sess.title, slug=sess.slug, token=sess.token,
        is_open=sess.is_open, pdf_url=pdf_endpoint
    )

@router.post("/{slug}/upload")
def upload_pdf(
    slug: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    sess = db.query(FeedbackSession).filter(FeedbackSession.slug == slug).first()
    if not sess: raise HTTPException(404, "Session not found")
    if sess.owner_id != current.id: raise HTTPException(403, "Not your session")
    if not file.filename.lower().endswith(".pdf"): raise HTTPException(400, "Only PDF allowed")

    object_name = make_object_name(sess.id)  # "feedback/<id>/cv.pdf"

    # Upload stream directly to GCS
    upload_fileobj(file.file, settings.GCS_BUCKET, object_name, content_type="application/pdf")

    sess.pdf_object = object_name
    db.commit(); db.refresh(sess)

    # (Optional) include a ready-to-use signed URL, or just return our proxy endpoint.
    # Returning proxy keeps token logic on server side:
    return {"ok": True, "pdf_url": f"/resume/feedback-sessions/{slug}/pdf"}



@router.get("/{slug}", response_model=FeedbackSessionRead)
def get_session_public(
    slug: str = Path(..., pattern=HEX10),
    t: str = Query(..., description="share token"),
    db: Session = Depends(get_db),
):
    sess = db.query(FeedbackSession).filter(FeedbackSession.slug == slug).first()
    if not sess or not sess.is_open: raise HTTPException(404, "Session closed")
    if t != sess.token: raise HTTPException(403, "Invalid token")
    if not sess.pdf_object: raise HTTPException(400, "PDF not uploaded yet")

    # Return a server endpoint; frontend doesn’t need to know the signed URL.
    # Including 't' here keeps your current frontend logic simple:
    pdf_endpoint = f"/resume/feedback-sessions/{slug}/pdf?t={t}"

    return FeedbackSessionRead(
        id=sess.id, title=sess.title, slug=sess.slug, token=sess.token,
        is_open=sess.is_open, pdf_url=pdf_endpoint
    )





@router.get("/{slug}/pdf")
def get_pdf_file(
    request: Request,
    slug: str = Path(..., pattern=HEX10),
    t: str = Query(...),
    db: Session = Depends(get_db),
):
    sess = db.query(FeedbackSession).filter(FeedbackSession.slug == slug).first()
    if not sess or not sess.is_open or t != sess.token:
        raise HTTPException(404, "Not available")
    if not sess.pdf_object:
        raise HTTPException(404, "PDF not uploaded")

    signed = generate_signed_url(settings.GCS_BUCKET, sess.pdf_object, expires_minutes=20)

    # Forward Range header so pdf.js can do partial reads
    headers = {}
    range_hdr = request.headers.get("range")
    if range_hdr:
        headers["Range"] = range_hdr

    # Stream from GCS to client
    upstream = requests.get(signed, headers=headers, stream=True)
    if upstream.status_code not in (200, 206):
        raise HTTPException(upstream.status_code, "Failed to fetch PDF")

    # Pass through important headers for pdf.js
    passthrough = {}
    for h in ["Content-Type", "Content-Length", "Accept-Ranges", "Content-Range", "ETag", "Last-Modified", "Cache-Control"]:
        if h in upstream.headers:
            passthrough[h] = upstream.headers[h]

    return StreamingResponse(
        upstream.iter_content(chunk_size=1024*256),
        status_code=upstream.status_code,
        headers=passthrough,
        media_type=upstream.headers.get("Content-Type", "application/pdf"),
    )

@router.post("/{slug}/upsert-review", response_model=FeedbackReviewOut)
def upsert_review(
    slug: str = Path(..., pattern=HEX10),
    t: str = Query(...),
    payload: FeedbackReviewUpsert = ...,
    db: Session = Depends(get_db),
    current: User | None = Depends(get_current_user)
):
    sess = db.query(FeedbackSession).filter(FeedbackSession.slug==slug).first()
    if not sess or not sess.is_open or t != sess.token: raise HTTPException(404, "Session not available")

    review = None
    if current:
        review = db.query(FeedbackReview).filter(
            FeedbackReview.session_id==sess.id,
            FeedbackReview.reviewer_user_id==current.id
        ).first()
    if not review:
        review = FeedbackReview(
            session_id=sess.id,
            reviewer_user_id=current.id if current else None,
            reviewer_name=(payload.reviewer.reviewer_name if payload.reviewer else None),
            reviewer_email=(payload.reviewer.reviewer_email if payload.reviewer else None),
        )
        db.add(review); db.flush()

    db.query(FeedbackComment).filter(FeedbackComment.review_id==review.id).delete()
    for c in payload.comments:
        db.add(FeedbackComment(
            review_id=review.id, page=c.page, quote=(c.quote or ""),
            rects_json=json.dumps(c.rects), note=c.note, sentiment=c.sentiment or "neutral"
        ))
    db.commit(); db.refresh(review)

    return FeedbackReviewOut.model_validate(review, from_attributes=True)

@router.post("/{slug}/submit")
def submit_review(
    slug: str = Path(..., pattern=HEX10),
    t: str = Query(...), db: Session = Depends(get_db)):
    sess = db.query(FeedbackSession).filter(FeedbackSession.slug==slug).first()
    if not sess or not sess.is_open or t != sess.token: raise HTTPException(404, "Session not available")
    review = (db.query(FeedbackReview)
              .filter(FeedbackReview.session_id==sess.id)
              .order_by(FeedbackReview.id.desc()).first())
    if not review: raise HTTPException(400, "No review to submit")
    review.submitted_at = datetime.utcnow()
    db.commit()
    return {"ok": True}

@router.get("/{slug}/inbox")
def owner_inbox(slug: str = Path(..., pattern=HEX10), db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    sess = db.query(FeedbackSession).filter(FeedbackSession.slug==slug).first()
    if not sess: raise HTTPException(404, "Session not found")
    if sess.owner_id != current.id: raise HTTPException(403, "Forbidden")
    reviews = (db.query(FeedbackReview)
               .filter(FeedbackReview.session_id==sess.id, FeedbackReview.submitted_at.isnot(None))
               .order_by(FeedbackReview.submitted_at.desc()).all())
    return [{
        "id": r.id, "reviewer_name": r.reviewer_name, "reviewer_email": r.reviewer_email,
        "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
        "comments": [{
            "id": c.id, "page": c.page, "quote": c.quote,
            "rects_json": c.rects_json, "note": c.note, "sentiment": c.sentiment
        } for c in r.comments]
    } for r in reviews]

@router.post("/{slug}/regenerate-link")
def regenerate_share_link(slug: str = Path(..., pattern=HEX10), db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    sess = db.query(FeedbackSession).filter(FeedbackSession.slug==slug).first()
    if not sess: raise HTTPException(404, "Session not found")
    if sess.owner_id != current.id: raise HTTPException(403, "Forbidden")
    sess.token = uuid.uuid4().hex
    db.commit()
    return {"token": sess.token}

@router.post("/{slug}/close")
def close_session(slug: str = Path(..., pattern=HEX10), db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    sess = db.query(FeedbackSession).filter(FeedbackSession.slug==slug).first()
    if not sess: raise HTTPException(404, "Session not found")
    if sess.owner_id != current.id: raise HTTPException(403, "Forbidden")
    sess.is_open = False
    db.commit()
    return {"ok": True}
