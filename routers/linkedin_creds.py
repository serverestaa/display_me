# routers/linkedin_creds.py
from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from utilsl.crypto import encrypt, decrypt
from utils import get_current_user
import schemas

router = APIRouter(prefix="/linkedin", tags=["linkedin"])

class LinkedInCredsIn(BaseModel):
    email: EmailStr
    password: str

class LinkedInCredsOut(BaseModel):
    email: EmailStr     # never return the password

@router.post("/credentials", response_model=LinkedInCredsOut)
def save_creds(
    body: LinkedInCredsIn,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    user.li_email   = body.email
    user.li_pwd_enc = encrypt(body.password)
    db.commit()
    return {"email": body.email}

@router.get("/credentials", response_model=LinkedInCredsOut)
def get_creds(
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    if not user.li_email:
        raise HTTPException(status_code=404, detail="No LinkedIn credentials stored")
    return {"email": user.li_email}
