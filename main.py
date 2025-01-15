import os
import subprocess
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Response
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from passlib.context import CryptContext
from jose import JWTError, jwt

from database import SessionLocal, engine, Base
import models
import schemas
from models import User, Section, Block
from latex_template import generate_latex

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Resume Builder with JWT")

# ---------------------- Конфиг для JWT ----------------------
SECRET_KEY = "YOUR_SUPER_SECRET_KEY"  # замените на реальный ключ!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # токен живет, к примеру, 60 минут

# ---------------------- Подготовка паролей (passlib) ----------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# ---------------------- Создание/проверка токена ----------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Декодирование токена, получение пользователя из БД.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

# ---------------------- AUTH endpoints ----------------------
@app.post("/auth/register", response_model=schemas.UserRead)
def register_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Регистрируем нового пользователя (email + password).
    """
    # Проверим, не занят ли email
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
    """
    Авторизация: принимает form-data с полями:
    username=<email>, password=<password>.
    Возвращает JWT-токен (access_token).
    """
    # Ищем пользователя по email
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    # Проверяем пароль
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    # Создаем токен
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},  # в sub пишем user_id
        expires_delta=access_token_expires
    )
    return schemas.Token(access_token=access_token, token_type="bearer")

# ---------------------- USER endpoints ----------------------

@app.get("/users/me", response_model=schemas.UserRead)
def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Возвращаем информацию о текущем (авторизованном) пользователе.
    """
    return current_user

# По желанию, можно иметь эндпоинты вроде /users/me/update для редактирования профиля
# Но чаще такие вещи выносят на отдельный PUT/PATCH.

# ---------------------- SECTIONS endpoints ----------------------

@app.post("/sections/", response_model=schemas.SectionRead)
def create_section(
    section_in: schemas.SectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Создать новую секцию (например, Education/Experience).
    Только для авторизованного пользователя.
    """
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