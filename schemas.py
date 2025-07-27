from datetime import datetime

from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict


# ----- User -----

class UserCreate(BaseModel):
    # Добавим поле password (plaintext)
    email: EmailStr
    password: str
    username: str
    # Остальные поля — опционально
    name: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    photo_url: Optional[str] = None

class UserRead(BaseModel):
    id: int
    email: EmailStr
    username: Optional[str]
    name: Optional[str]
    phone: Optional[str]
    linkedin: Optional[str]
    github: Optional[str]
    photo_url: Optional[str] = None
    class Config:
        orm_mode = True

class UserUpdateUsername(BaseModel):
    username: str


class UserUpdateProfile(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    photo_url: Optional[str] = None

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


# ----- New schemas for specific resume sections -----

# General Information
class GeneralBase(BaseModel):
    username: Optional[str] = None
    fullName: Optional[str] = None
    occupation: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    about: Optional[str] = None


class GeneralCreate(GeneralBase):
    pass


class GeneralUpdate(GeneralBase):
    pass


class GeneralRead(GeneralBase):
    id: int

    class Config:
        from_attributes = True


# Work Experience
class WorkExperienceBase(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    description: Optional[str] = None
    is_disabled: bool = False
    url: Optional[str] = None


class WorkExperienceCreate(WorkExperienceBase):
    pass


class WorkExperienceUpdate(WorkExperienceBase):
    pass


class WorkExperienceRead(WorkExperienceBase):
    id: int

    class Config:
        from_attributes = True


# Project
class ProjectBase(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    url: Optional[str] = None
    is_disabled: bool = False
    stack: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(ProjectBase):
    pass


class ProjectRead(ProjectBase):
    id: int

    class Config:
        from_attributes = True


# Education
class EducationBase(BaseModel):
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    institution: Optional[str] = None
    degree: Optional[str] = None
    location: Optional[str] = None
    url: Optional[str] = None
    is_disabled: bool = False
    description: Optional[str] = None


class EducationCreate(EducationBase):
    pass


class EducationUpdate(EducationBase):
    pass


class EducationRead(EducationBase):
    id: int

    class Config:
        from_attributes = True

# Achievement
class AchievementBase(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_disabled: bool = False
    startDate: Optional[str] = None
    url: Optional[str] = None


class AchievementCreate(AchievementBase):
    pass


class AchievementUpdate(AchievementBase):
    pass


class AchievementRead(AchievementBase):
    id: int

    class Config:
        from_attributes = True


# Contact
class ContactBase(BaseModel):
    media: Optional[str] = None
    link: Optional[str] = None


class ContactCreate(ContactBase):
    pass


class ContactUpdate(ContactBase):
    pass


class ContactRead(ContactBase):
    id: int

    class Config:
        from_attributes = True


# Skill
class SkillBase(BaseModel):
    category: Optional[str] = None
    stack: Optional[str] = None
    is_disabled: bool = False


class SkillCreate(SkillBase):
    pass


class SkillUpdate(SkillBase):
    pass


class SkillRead(SkillBase):
    id: int

    class Config:
        from_attributes = True


# Complete Resume for non-logged-in users
class CompleteResume(BaseModel):
    general: Optional[GeneralRead] = None
    workExperience: List[WorkExperienceRead] = []
    projects: List[ProjectRead] = []
    education: List[EducationRead] = []
    achievements: List[AchievementRead] = []
    skills: List[SkillRead] = []
    contacts: List[ContactRead] = []

    class Config:
        from_attributes = True


class FeedbackItem(BaseModel):
    text: str
    highlight_positions: Optional[str] = None

class MultiFeedbackCreate(BaseModel):
    user_id: int
    feedbacks: List[FeedbackItem]

class FeedbackRead(BaseModel):
    id: int
    author_id: int
    user_id: int
    text: str
    highlight_positions: str
    created_at: datetime

    class Config:
        orm_mode = True


class SectionsOrderUpdate(BaseModel):
    sections: List[str] 

class SectionsOrderRead(BaseModel):
    sections: List[str]