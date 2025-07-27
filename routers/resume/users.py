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
from helpers.resume import get_complete_resume

from pydantic import BaseModel

router = APIRouter()

@router.put("/me/username", response_model=schemas.UserRead)
def update_username(
        username_update: schemas.UserUpdateUsername,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # Check if username is already taken
    existing_user = db.query(models.User).filter(
        models.User.username == username_update.username
    ).first()

    if existing_user and existing_user.id != current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Username already taken"
        )

    current_user.username = username_update.username
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/me/full", response_model=schemas.CompleteResume)
def get_my_full_info(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    return get_complete_resume(current_user.id, db)


@router.get("/{username}/full", response_model=schemas.CompleteResume)
def get_full_info_by_username(
        username: str,
        db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return get_complete_resume(user.id, db)
