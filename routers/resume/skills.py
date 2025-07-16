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


# ----- Skill Endpoints -----

@router.post("/", response_model=schemas.SkillRead)
def create_skill(
        skill_in: schemas.SkillCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    skill = models.Skill(**skill_in.dict(), user_id=current_user.id)
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


@router.get("/", response_model=List[schemas.SkillRead])
def get_skills(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    skills = db.query(models.Skill).filter(models.Skill.user_id == current_user.id).all()
    return skills


@router.get("/{skill_id}", response_model=schemas.SkillRead)
def get_skill(
        skill_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    skill = db.query(models.Skill).filter(
        models.Skill.id == skill_id,
        models.Skill.user_id == current_user.id
    ).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.patch("/{skill_id}/disable")
def toggle_skill_disable(
        skill_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    skill = db.query(models.Skill).filter(
        models.Skill.id == skill_id,
        models.Skill.user_id == current_user.id
    ).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    skill.is_disabled = not skill.is_disabled
    db.commit()
    db.refresh(skill)
    return {"message": "Skill updated", "is_disabled": skill.is_disabled}


@router.put("/{skill_id}", response_model=schemas.SkillRead)
def update_skill(
        skill_id: int,
        skill_in: schemas.SkillUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    skill = db.query(models.Skill).filter(
        models.Skill.id == skill_id,
        models.Skill.user_id == current_user.id
    ).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    for key, value in skill_in.dict(exclude_unset=True).items():
        setattr(skill, key, value)

    db.commit()
    db.refresh(skill)
    return skill

@router.delete("/{skill_id}")
def delete_skill(
        skill_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    skill = db.query(models.Skill).filter(
        models.Skill.id == skill_id,
        models.Skill.user_id == current_user.id
    ).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    db.delete(skill)
    db.commit()
    return {"message": "Skill deleted"} 