from fastapi import APIRouter

import os


from utils import get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user

from datetime import timedelta
from fastapi import Response
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuthError
from fastapi import Request
from database import engine, Base, get_db
import models
import schemas
from models import User

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=schemas.UserRead)
def register_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user_in.password)
    user = User(
        email=user_in.email,
        hashed_password=hashed_password,
        name=user_in.name,
        phone=user_in.phone,
        linkedin=user_in.linkedin,
        github=user_in.github
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.Token)
def login_for_access_token(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": str(user.id)}, expires_delta=access_token_expires)
    return schemas.Token(access_token=access_token, token_type="bearer")

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(
        key="access_token",
        path="/",
        samesite="lax"
    )
    return {"detail": "logged out"}


@router.get("/google")
async def auth_google(request: Request):
    redirect_uri = f"{os.getenv('BACKEND_URL')}/auth/google/callback"
    # callbackUrl можно закодировать в параметр state:
    state = request.query_params.get("callbackUrl", "/welcome")
    return await oauth.google.authorize_redirect(
        request, redirect_uri, state=state
    )


@router.get("/google/callback")
async def auth_google_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError:
        raise HTTPException(status_code=400, detail="Google authentication failed")

    try:
        user_info = await oauth.google.parse_id_token(request, token)
    except KeyError:
        resp = await oauth.google.get('userinfo', token=token)
        user_info = resp.json()

    email = user_info.get('email')
    if not email:
        raise HTTPException(status_code=400, detail="Email not available from Google")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            hashed_password="",
            name=user_info.get('name', ''),
            photo_url=user_info.get('picture')
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        # Ensure the user's General info has a fullName
        general = db.query(models.General).filter(models.General.user_id == user.id).first()
        if general:
            if not general.fullName:
                general.fullName = user_info.get('name')
                db.commit()
        else:
            # Create a General record with fullName from Google
            general = models.General(
                username=user.username,
                fullName=user_info.get('name'),
                occupation=None,
                location=None,
                website=None,
                about=None,
                user_id=user.id
            )
            db.add(general)
            db.commit()
    else:
        # Update existing user’s name and photo on Google login
        user.name = user_info.get('name', '')
        user.photo_url = user_info.get('picture')
        db.commit()
        db.refresh(user)
        # Ensure the user's General info has a fullName
        general = db.query(models.General).filter(models.General.user_id == user.id).first()
        if general:
            if not general.fullName:
                general.fullName = user_info.get('name')
                db.commit()
        else:
            # Create a General record with fullName from Google
            general = models.General(
                username=user.username,
                fullName=user_info.get('name'),
                occupation=None,
                location=None,
                website=None,
                about=None,
                user_id=user.id
            )
            db.add(general)
            db.commit()

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": str(user.id)}, expires_delta=access_token_expires)

    callback_url = request.query_params.get("state", "/welcome")
    return RedirectResponse(
        url=f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}{callback_url}?token={access_token}",
        status_code=303,
    )
