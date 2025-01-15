from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True, unique=True)  # сделаем уникальным
    linkedin = Column(String, nullable=True)
    github = Column(String, nullable=True)

    # Храним только хэш пароля
    hashed_password = Column(String, nullable=True)

    sections = relationship("Section", back_populates="owner")


class Section(Base):
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)  # Например, "Education", "Experience"
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)  # Новое поле для включения/отключения секции
    order = Column(Integer, default=0)
    # Связь с пользователем
    owner = relationship("User", back_populates="sections")
    # Связь "один ко многим" с блоками
    blocks = relationship("Block", back_populates="section")


class Block(Base):
    __tablename__ = "blocks"

    id = Column(Integer, primary_key=True, index=True)
    header = Column(String, nullable=True)       # Например, "Nazarbayev University"
    location = Column(String, nullable=True)     # Например, "Astana, Kazakhstan"
    subheader = Column(String, nullable=True)    # Например, "BSc Computer Science, GPA: 3.54, top 4%"
    dates = Column(String, nullable=True)        # Например, "August 2022 - June 2026"
    description = Column(String, nullable=True)  # Доп. информация (курс, проект, опыт)
    is_active = Column(Boolean, default=True)  # Новое поле для включения/отключения блока
    order = Column(Integer, default=0)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=False)

    # Связь с секцией
    section = relationship("Section", back_populates="blocks")