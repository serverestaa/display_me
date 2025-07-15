from pathlib import Path
from uuid import uuid4

from utils import get_current_user

from fastapi import UploadFile, File, APIRouter
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import schemas
from models import User

# ---------------------- USER endpoints ----------------------

router = APIRouter(prefix="/users", tags=["users"])

@router.put("/me", response_model=schemas.UserRead)
def update_user_profile(
    user_in: schemas.UserUpdateProfile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Only overwrite the fields that were provided
    for attr, value in user_in.dict(exclude_unset=True).items():
        setattr(current_user, attr, value)
    db.commit()
    db.refresh(current_user)
    return current_user
@router.get("/me", response_model=schemas.UserRead)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/me/photo", response_model=schemas.UserRead)
def upload_user_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Убедиться, что директория есть
    upload_dir = Path("static/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Сгенерировать уникальное имя
    ext = Path(file.filename).suffix
    filename = f"{current_user.id}_{uuid4().hex}{ext}"
    dest = upload_dir / filename

    # Сохранить файл
    with open(dest, "wb") as out:
        out.write(file.file.read())

    # Обновить URL в базе
    current_user.photo_url = f"/static/uploads/{filename}"
    db.commit()
    db.refresh(current_user)

    return current_user
# ---------------------- USERNAME ENDPOINTS ----------------------
@router.put("/me/username", response_model=schemas.UserRead)
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


@router.get("/{username}", response_model=schemas.UserRead)
def get_user_by_username(
        username: str,
        db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user