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


# ----- Project Endpoints -----

@router.post("/", response_model=schemas.ProjectRead)
def create_project(
        project_in: schemas.ProjectCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    project = models.Project(**project_in.dict(), user_id=current_user.id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/", response_model=List[schemas.ProjectRead])
def get_projects(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    projects = db.query(models.Project).filter(models.Project.user_id == current_user.id).all()
    return projects


@router.get("/{project_id}", response_model=schemas.ProjectRead)
def get_project(
        project_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.patch("/{project_id}/disable")
def toggle_project_disable(
        project_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.is_disabled = not project.is_disabled
    db.commit()
    db.refresh(project)
    return {"message": "Project updated", "is_disabled": project.is_disabled}

@router.put("/{project_id}", response_model=schemas.ProjectRead)
def update_project(
        project_id: int,
        project_in: schemas.ProjectUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for key, value in project_in.dict(exclude_unset=True).items():
        setattr(project, key, value)

    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}")
def delete_project(
        project_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()
    return {"message": "Project deleted"}
