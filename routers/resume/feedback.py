from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Feedback, User
from schemas import MultiFeedbackCreate, FeedbackRead
from utils import get_current_user
from typing import List

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
