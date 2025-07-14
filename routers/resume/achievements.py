import os
import subprocess

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Response
from sqlalchemy.orm import Session
from typing import List
import tempfile
import models
import schemas
from latex_template import generate_latex_from_complete_resume
from database import get_db
from utils import get_current_user
from fastapi import Response, UploadFile, File
import tempfile
from import_resume import _pdf_to_text, _ask_gemini_for_json, import_resume_from_json, replace_resume_from_json
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi import Body
from typing import Any

from pydantic import BaseModel

router = APIRouter()


# ----- Achievement Endpoints -----

@router.post("/", response_model=schemas.AchievementRead)
def create_achievement(
        achievement_in: schemas.AchievementCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    achievement = models.Achievement(**achievement_in.dict(), user_id=current_user.id)
    db.add(achievement)
    db.commit()
    db.refresh(achievement)
    return achievement


@router.get("/", response_model=List[schemas.AchievementRead])
def get_achievements(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    achievements = db.query(models.Achievement).filter(models.Achievement.user_id == current_user.id).all()
    return achievements


@router.get("/{achievement_id}", response_model=schemas.AchievementRead)
def get_achievement(
        achievement_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    achievement = db.query(models.Achievement).filter(
        models.Achievement.id == achievement_id,
        models.Achievement.user_id == current_user.id
    ).first()
    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found")
    return achievement


@router.patch("/{achievement_id}/disable")
def toggle_achievement_disable(
        achievement_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    achievement = db.query(models.Achievement).filter(
        models.Achievement.id == achievement_id,
        models.Achievement.user_id == current_user.id
    ).first()
    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found")

    achievement.is_disabled = not achievement.is_disabled
    db.commit()
    db.refresh(achievement)
    return {"message": "Achievement updated", "is_disabled": achievement.is_disabled}

@router.put("/{achievement_id}", response_model=schemas.AchievementRead)
def update_achievement(
        achievement_id: int,
        achievement_in: schemas.AchievementUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    achievement = db.query(models.Achievement).filter(
        models.Achievement.id == achievement_id,
        models.Achievement.user_id == current_user.id
    ).first()
    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found")

    for key, value in achievement_in.dict(exclude_unset=True).items():
        setattr(achievement, key, value)

    db.commit()
    db.refresh(achievement)
    return achievement


@router.delete("/{achievement_id}")
def delete_achievement(
        achievement_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    achievement = db.query(models.Achievement).filter(
        models.Achievement.id == achievement_id,
        models.Achievement.user_id == current_user.id
    ).first()
    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found")

    db.delete(achievement)
    db.commit()
    return {"message": "Achievement deleted"}
