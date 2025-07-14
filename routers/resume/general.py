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

# ----- General Information Endpoints -----
router = APIRouter()

@router.post("/", response_model=schemas.GeneralRead)
def create_general(
        general_in: schemas.GeneralCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # Check if general info already exists
    existing = db.query(models.General).filter(models.General.user_id == current_user.id).first()
    if existing:
        # Update existing
        for key, value in general_in.dict().items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing

    # Create new
    general = models.General(**general_in.dict(), user_id=current_user.id)
    db.add(general)
    db.commit()
    db.refresh(general)
    return general


@router.get("/", response_model=schemas.GeneralRead)
def get_general(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    general = db.query(models.General).filter(models.General.user_id == current_user.id).first()
    if not general:
        general = models.General(username = current_user.username,
            fullName = None,
            occupation = None,
            location = None,
            website = None,
            about = None,
            user_id = current_user.id)
        db.add(general)
        db.commit()
        db.refresh(general)
    return general


@router.put("/", response_model=schemas.GeneralRead)
def update_general(
        general_in: schemas.GeneralUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    general = db.query(models.General).filter(models.General.user_id == current_user.id).first()
    if not general:
        # Create if doesn't exist
        general = models.General(**general_in.dict(), user_id=current_user.id)
        db.add(general)
    else:
        # Update existing
        for key, value in general_in.dict(exclude_unset=True).items():
            setattr(general, key, value)

    db.commit()
    db.refresh(general)
    return general
