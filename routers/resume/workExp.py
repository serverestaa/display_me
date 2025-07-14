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


# ----- Work Experience Endpoints -----

router = APIRouter()

@router.post("/", response_model=schemas.WorkExperienceRead)
def create_work_experience(
        work_exp_in: schemas.WorkExperienceCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    work_exp = models.WorkExperience(**work_exp_in.dict(), user_id=current_user.id)
    db.add(work_exp)
    db.commit()
    db.refresh(work_exp)
    return work_exp


@router.get("/", response_model=List[schemas.WorkExperienceRead])
def get_work_experiences(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    work_exps = db.query(models.WorkExperience).filter(models.WorkExperience.user_id == current_user.id).all()
    return work_exps


@router.get("/{work_exp_id}", response_model=schemas.WorkExperienceRead)
def get_work_experience(
        work_exp_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    work_exp = db.query(models.WorkExperience).filter(
        models.WorkExperience.id == work_exp_id,
        models.WorkExperience.user_id == current_user.id
    ).first()
    if not work_exp:
        raise HTTPException(status_code=404, detail="Work experience not found")
    return work_exp


@router.put("/{work_exp_id}", response_model=schemas.WorkExperienceRead)
def update_work_experience(
        work_exp_id: int,
        work_exp_in: schemas.WorkExperienceUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    work_exp = db.query(models.WorkExperience).filter(
        models.WorkExperience.id == work_exp_id,
        models.WorkExperience.user_id == current_user.id
    ).first()
    if not work_exp:
        raise HTTPException(status_code=404, detail="Work experience not found")

    for key, value in work_exp_in.dict(exclude_unset=True).items():
        setattr(work_exp, key, value)

    db.commit()
    db.refresh(work_exp)
    return work_exp

@router.patch("/{wid}/disable")
def toggle_we_disable(
        wid: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    work_exp = db.query(models.WorkExperience).filter(
        models.WorkExperience.id == wid,
        models.WorkExperience.user_id == current_user.id
    ).first()
    if not work_exp:
        raise HTTPException(status_code=404, detail="Work experience not found")

    work_exp.is_disabled = not work_exp.is_disabled
    db.commit()
    db.refresh(work_exp)
    return {"message": "Work experience updated", "is_disabled": work_exp.is_disabled}


@router.delete("/{work_exp_id}")
def delete_work_experience(
        work_exp_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    work_exp = db.query(models.WorkExperience).filter(
        models.WorkExperience.id == work_exp_id,
        models.WorkExperience.user_id == current_user.id
    ).first()
    if not work_exp:
        raise HTTPException(status_code=404, detail="Work experience not found")

    db.delete(work_exp)
    db.commit()
    return {"message": "Work experience deleted"}

