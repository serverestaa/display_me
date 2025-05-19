import os
from dotenv import load_dotenv

from utils import get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user

load_dotenv()
import subprocess
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Response
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import Request
from passlib.context import CryptContext
from jose import JWTError, jwt
from starlette.middleware.sessions import SessionMiddleware
from database import SessionLocal, engine, Base, get_db
import models
import schemas
from models import User, Section, Block
from latex_template import generate_latex
from fastapi.middleware.cors import CORSMiddleware
from Resume_endpoints import router
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Resume Builder with JWT")
app.add_middleware(SessionMiddleware, secret_key="YOUR_SUPER_SECRET_KEY")
app.include_router(router, prefix="/resume", tags=["resume"])
origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8080",
    "http://localhost:8000",
    "https://www.displayme.online"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/auth/register", response_model=schemas.UserRead)
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


@app.post("/auth/login", response_model=schemas.Token)
def login_for_access_token(
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
    access_token = create_access_token(
        data={"sub": str(user.id)},  # в sub пишем user_id
        expires_delta=access_token_expires
    )
    return schemas.Token(access_token=access_token, token_type="bearer")


# ---------------------- OAuth configuration ----------------------

oauth = OAuth(app)
oauth.config = {}
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    api_base_url='https://openidconnect.googleapis.com/v1/',
    client_kwargs={'scope': 'openid email profile'},
)

oauth.register(
    name='github',
    client_id=os.getenv('GITHUB_CLIENT_ID'),
    client_secret=os.getenv('GITHUB_CLIENT_SECRET'),
    access_token_url='https://github.com/login/oauth/access_token',
    access_token_params=None,
    authorize_url='https://github.com/login/oauth/authorize',
    authorize_params=None,
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
)



@app.get("/auth/google")
async def auth_google(request: Request):
    # Optionally, store callbackUrl from query params in session
    callback_url = request.query_params.get("callbackUrl")
    if callback_url:
        request.session["callbackUrl"] = callback_url

    redirect_uri = request.url_for('auth_google_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/google/callback")
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
            name=user_info.get('name', '')
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": str(user.id)}, expires_delta=access_token_expires)

    callback_url = request.session.get("callbackUrl", "/welcome")  
    redirect_url = f"http://localhost:3000{callback_url}?token={access_token}"

    return RedirectResponse(url=redirect_url)



@app.get("/auth/github")
async def auth_github(request: Request):
    redirect_uri = request.url_for('auth_github_callback')
    return await oauth.github.authorize_redirect(request, redirect_uri)


@app.get("/auth/github/callback")
async def auth_github_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.github.authorize_access_token(request)
    except OAuthError:
        raise HTTPException(status_code=400, detail="GitHub authentication failed")
    resp = await oauth.github.get('user', token=token)
    profile = resp.json()
    email = profile.get('email')
    if not email:
        resp_emails = await oauth.github.get('user/emails', token=token)
        emails = resp_emails.json()
        primary_email = next((item['email'] for item in emails if item.get('primary') and item.get('verified')), None)
        email = primary_email
    if not email:
        raise HTTPException(status_code=400, detail="GitHub account does not have a verified email")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            hashed_password="",
            name=profile.get('name') or profile.get('login')
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": str(user.id)}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

# ---------------------- USER endpoints ----------------------

@app.get("/users/me", response_model=schemas.UserRead)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


# ---------------------- USERNAME ENDPOINTS ----------------------
@app.put("/users/me/username", response_model=schemas.UserRead)
def update_username(
        username_in: schemas.UserUpdateUsername,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # Check if username is already taken
    existing_user = db.query(User).filter(
        User.username == username_in.username,
        User.id != current_user.id
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already taken")

    current_user.username = username_in.username
    db.commit()
    db.refresh(current_user)
    return current_user


@app.get("/users/{username}", response_model=schemas.UserRead)
def get_user_by_username(
        username: str,
        db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ---------------------- SECTIONS endpoints ----------------------

@app.post("/sections/", response_model=schemas.SectionRead)
def create_section(
    section_in: schemas.SectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    section = Section(
        title=section_in.title,
        owner=current_user
    )
    db.add(section)
    db.commit()
    db.refresh(section)

    # Если переданы blocks, создадим их
    for block_data in section_in.blocks:
        block = Block(
            header=block_data.header,
            location=block_data.location,
            subheader=block_data.subheader,
            dates=block_data.dates,
            description=block_data.description,
            section_id=section.id
        )
        db.add(block)
    db.commit()
    db.refresh(section)
    return section

@app.get("/sections/{section_id}", response_model=schemas.SectionRead)
def get_section(
    section_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    section = db.query(Section).filter(
        Section.id == section_id,
        Section.user_id == current_user.id
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found or not yours")
    return section

@app.delete("/sections/{section_id}")
def delete_section(
    section_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    section = db.query(Section).filter(
        Section.id == section_id,
        Section.user_id == current_user.id
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found or not yours")
    db.delete(section)
    db.commit()
    return {"message": "Section deleted"}


@app.put("/sections/{section_id}", response_model=schemas.SectionRead)
def update_section(
    section_id: int,
    section_in: schemas.SectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    section = db.query(Section).filter(
        Section.id == section_id,
        Section.user_id == current_user.id
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found or not yours")

    for key, value in section_in.dict(exclude_unset=True).items():
        setattr(section, key, value)
    db.commit()
    db.refresh(section)
    return section


@app.patch("/sections/{section_id}/activate")
def toggle_section_activation(
    section_id: int,
    is_active: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    section = db.query(Section).filter(
        Section.id == section_id,
        Section.user_id == current_user.id
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found or not yours")

    section.is_active = is_active
    db.commit()
    db.refresh(section)
    return section


@app.patch("/sections/order")
def reorder_sections(
    order: list[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sections = db.query(Section).filter(Section.user_id == current_user.id).all()
    section_map = {section.id: section for section in sections}

    for idx, section_id in enumerate(order):
        if section_id in section_map:
            section_map[section_id].order = idx
    db.commit()
    return {"message": "Sections reordered"}
# ---------------------- BLOCKS endpoints ----------------------

@app.post("/sections/{section_id}/blocks/", response_model=schemas.BlockRead)
def create_block(
    section_id: int,
    block_in: schemas.BlockCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    section = db.query(Section).filter(
        Section.id == section_id,
        Section.user_id == current_user.id
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found or not yours")

    block = Block(
        header=block_in.header,
        location=block_in.location,
        subheader=block_in.subheader,
        dates=block_in.dates,
        description=block_in.description,
        section=section
    )
    db.add(block)
    db.commit()
    db.refresh(block)
    return block

@app.delete("/blocks/{block_id}")
def delete_block(
    block_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    block = db.query(Block).join(Section).filter(
        Block.id == block_id,
        Section.user_id == current_user.id
    ).first()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found or not yours")
    db.delete(block)
    db.commit()
    return {"message": "Block deleted"}


@app.put("/blocks/{block_id}", response_model=schemas.BlockRead)
def update_block(
    block_id: int,
    block_in: schemas.BlockUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    block = db.query(Block).join(Section).filter(
        Block.id == block_id,
        Section.user_id == current_user.id
    ).first()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found or not yours")

    for key, value in block_in.dict(exclude_unset=True).items():
        setattr(block, key, value)
    db.commit()
    db.refresh(block)
    return block


@app.patch("/blocks/{block_id}/activate")
def toggle_block_activation(
    block_id: int,
    is_active: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    block = db.query(Block).join(Section).filter(
        Block.id == block_id,
        Section.user_id == current_user.id
    ).first()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found or not yours")

    block.is_active = is_active
    db.commit()
    db.refresh(block)
    return block


@app.patch("/blocks/order")
def reorder_blocks(
    section_id: int,
    order: list[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    blocks = db.query(Block).filter(
        Block.section_id == section_id,
        Section.user_id == current_user.id
    ).join(Section).all()

    block_map = {block.id: block for block in blocks}
    for idx, block_id in enumerate(order):
        if block_id in block_map:
            block_map[block_id].order = idx
    db.commit()
    return {"message": "Blocks reordered"}
# ---------------------- Генерация LaTeX/PDF ----------------------

@app.get("/resume/latex")
def get_resume_latex(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Возвращает итоговый LaTeX текст для текущего пользователя.
    """
    user = current_user  # уже авторизован
    sections = db.query(Section).filter(Section.user_id == user.id).all()

    latex_code = generate_latex(user, sections)
    return latex_code


@app.get("/resume/pdf")
def get_resume_pdf(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = current_user
    sections = db.query(Section).filter(Section.user_id == user.id).all()

    latex_code = generate_latex(user, sections)

    tex_filename = f"resume_{user.id}.tex"
    pdf_filename = f"resume_{user.id}.pdf"

    with open(tex_filename, "w", encoding="utf-8") as f:
        f.write(latex_code)

    # Компилируем pdflatex
    for _ in range(2):
        subprocess.run(["pdflatex", "-interaction=nonstopmode", tex_filename], check=True)

    with open(pdf_filename, "rb") as f:
        pdf_data = f.read()

    return Response(content=pdf_data, media_type="application/pdf")