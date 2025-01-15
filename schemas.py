from pydantic import BaseModel, EmailStr
from typing import Optional, List


# ----- User -----

class UserCreate(BaseModel):
    # Добавим поле password (plaintext)
    email: EmailStr
    password: str

    # Остальные поля — опционально
    name: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None


class UserRead(BaseModel):
    id: int
    email: EmailStr
    name: Optional[str]
    phone: Optional[str]
    linkedin: Optional[str]
    github: Optional[str]

    class Config:
        orm_mode = True


# ----- Auth -----

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ----- Section, Block (как раньше) -----

class BlockCreate(BaseModel):
    header: Optional[str] = None
    location: Optional[str] = None
    subheader: Optional[str] = None
    dates: Optional[str] = None
    description: Optional[str] = None

class BlockRead(BaseModel):
    id: int
    header: Optional[str]
    location: Optional[str]
    subheader: Optional[str]
    dates: Optional[str]
    description: Optional[str]
    is_active: bool  # Для отображения состояния
    order: Optional[int]  # Для сохранения порядка

    class Config:
        orm_mode = True


class SectionRead(BaseModel):
    id: int
    title: str
    blocks: List[BlockRead] = []
    is_active: bool  # Для отображения состояния
    order: Optional[int]  # Для сохранения порядка

    class Config:
        orm_mode = True


class SectionCreate(BaseModel):
    title: str
    blocks: Optional[List[BlockCreate]] = []


class SectionUpdate(BaseModel):
    title: Optional[str] = None
    is_active: Optional[bool] = None  # Логика активации
    order: Optional[int] = None  # Для изменения порядка


class BlockUpdate(BaseModel):
    header: Optional[str] = None
    location: Optional[str] = None
    subheader: Optional[str] = None
    dates: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None  # Логика активации
    order: Optional[int] = None  # Для изменения порядка


class SectionOrderUpdate(BaseModel):
    order: List[int]  # Список ID секций в новом порядке


class BlockOrderUpdate(BaseModel):
    section_id: int  # ID секции, к которой относятся блоки
    order: List[int]  # Список ID блоков в новом порядке