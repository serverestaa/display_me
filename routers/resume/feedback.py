from fastapi import APIRouter, Depends, HTTPException, Body, Path, Response, File, UploadFile, Query
from requests import session
from sqlalchemy.orm import Session
from starlette.responses import FileResponse
from datetime import datetime
from database import get_db
from models import Feedback, User, FeedbackSession, FeedbackReview, FeedbackComment
from schemas import MultiFeedbackCreate, FeedbackRead, FeedbackItem, FeedbackSessionCreate, FeedbackSessionRead, FeedbackReviewUpsert, FeedbackReviewOut, FeedbackCommentOut
from utils import get_current_user
from config import settings
from typing import List
import os, uuid, json, shutil

router = APIRouter(prefix="/feedback", tags=["feedback"])

@router.post("/", response_model=List[FeedbackRead])
def leave_feedbacks(
    feedback_in: MultiFeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check that the target user (resume owner) exists
    target_user = db.query(User).filter(User.id == feedback_in.user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    feedback_objects = []
    for item in feedback_in.feedbacks:
        feedback = Feedback(
            author_id=current_user.id,
            user_id=feedback_in.user_id,
            text=item.text,
            highlight_positions=item.highlight_positions
        )
        db.add(feedback)
        feedback_objects.append(feedback)

    db.commit()
    for fb in feedback_objects:
        db.refresh(fb)

    return feedback_objects




@router.get("/my-feedback", response_model=List[FeedbackRead])
def get_feedback_for_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    feedbacks = db.query(Feedback).filter(Feedback.user_id == current_user.id).all()
    return feedbacks

@router.put("/{feedback_id}", response_model=FeedbackRead)
def update_feedback(
    feedback_id: int = Path(..., gt=0),
    updated_data: FeedbackItem = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()

    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    if feedback.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this feedback")

    feedback.text = updated_data.text
    feedback.highlight_positions = updated_data.highlight_positions
    db.commit()
    db.refresh(feedback)

    return feedback

@router.delete("/{feedback_id}", status_code=204)
def delete_feedback(
    feedback_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()

    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    if feedback.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this feedback")

    db.delete(feedback)
    db.commit()

    return Response(status_code=204)


