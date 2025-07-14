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


@router.post("/", response_model=schemas.ContactRead)
def create_contact(
        contact_in: schemas.ContactCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    contact = models.Contact(**contact_in.dict(), user_id=current_user.id)
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.get("/", response_model=List[schemas.ContactRead])
def get_contacts(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    contacts = db.query(models.Contact).filter(models.Contact.user_id == current_user.id).all()
    return contacts


@router.get("/{contact_id}", response_model=schemas.ContactRead)
def get_contact(
        contact_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    contact = db.query(models.Contact).filter(
        models.Contact.id == contact_id,
        models.Contact.user_id == current_user.id
    ).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.put("/{contact_id}", response_model=schemas.ContactRead)
def update_contact(
        contact_id: int,
        contact_in: schemas.ContactUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    contact = db.query(models.Contact).filter(
        models.Contact.id == contact_id,
        models.Contact.user_id == current_user.id
    ).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    for key, value in contact_in.dict(exclude_unset=True).items():
        setattr(contact, key, value)

    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/{contact_id}")
def delete_contact(
        contact_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    contact = db.query(models.Contact).filter(
        models.Contact.id == contact_id,
        models.Contact.user_id == current_user.id
    ).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    db.delete(contact)
    db.commit()
    return {"message": "Contact deleted"}
