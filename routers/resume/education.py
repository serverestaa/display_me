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

# ----- Education Endpoints -----

@router.post("/", response_model=schemas.EducationRead)
def create_education(
        education_in: schemas.EducationCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    education = models.Education(**education_in.dict(), user_id=current_user.id)
    db.add(education)
    db.commit()
    db.refresh(education)
    return education


@router.get("/", response_model=List[schemas.EducationRead])
def get_educations(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    educations = db.query(models.Education).filter(models.Education.user_id == current_user.id).all()
    return educations


@router.get("/{education_id}", response_model=schemas.EducationRead)
def get_education(
        education_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    education = db.query(models.Education).filter(
        models.Education.id == education_id,
        models.Education.user_id == current_user.id
    ).first()
    if not education:
        raise HTTPException(status_code=404, detail="Education not found")
    return education


@router.patch("/{education_id}/disable")
def toggle_education_disable(
        education_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    education = db.query(models.Education).filter(
        models.Education.id == education_id,
        models.Education.user_id == current_user.id
    ).first()
    if not education:
        raise HTTPException(status_code=404, detail="Education not found")

    education.is_disabled = not education.is_disabled
    db.commit()
    db.refresh(education)
    return {"message": "Education updated", "is_disabled": education.is_disabled}

@router.put("/{education_id}", response_model=schemas.EducationRead)
def update_education(
        education_id: int,
        education_in: schemas.EducationUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    education = db.query(models.Education).filter(
        models.Education.id == education_id,
        models.Education.user_id == current_user.id
    ).first()
    if not education:
        raise HTTPException(status_code=404, detail="Education not found")

    for key, value in education_in.dict(exclude_unset=True).items():
        setattr(education, key, value)

    db.commit()
    db.refresh(education)
    return education


@router.delete("/{education_id}")
def delete_education(
        education_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    education = db.query(models.Education).filter(
        models.Education.id == education_id,
        models.Education.user_id == current_user.id
    ).first()
    if not education:
        raise HTTPException(status_code=404, detail="Education not found")

    db.delete(education)
    db.commit()
    return {"message": "Education deleted"}
