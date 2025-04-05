from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    username = Column(String, unique=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True, unique=True)  # сделаем уникальным
    linkedin = Column(String, nullable=True)
    github = Column(String, nullable=True)

    hashed_password = Column(String, nullable=True)

    sections = relationship("Section", back_populates="owner")


class Section(Base):
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    order = Column(Integer, default=0)

    owner = relationship("User", back_populates="sections")

    blocks = relationship("Block", back_populates="section")


class Block(Base):
    __tablename__ = "blocks"

    id = Column(Integer, primary_key=True, index=True)
    header = Column(String, nullable=True)
    location = Column(String, nullable=True)
    subheader = Column(String, nullable=True)
    dates = Column(String, nullable=True)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    order = Column(Integer, default=0)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=False)

    section = relationship("Section", back_populates="blocks")