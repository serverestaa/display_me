from xmlrpc.client import DateTime

from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Text, DateTime, UniqueConstraint
from datetime import datetime
from sqlalchemy.orm import relationship
from database import Base
import uuid


def gen_token():
    return uuid.uuid4().hex


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    username = Column(String, unique=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True, unique=True)  # сделаем уникальным
    linkedin = Column(String, nullable=True)
    github = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)
    hashed_password = Column(String, nullable=True)

    sections_order = Column(Text, nullable=True)

    # Original relationships
    sections = relationship("Section", back_populates="owner")
    
    # New relationships
    general = relationship("General", back_populates="user", uselist=False)
    work_experiences = relationship("WorkExperience", back_populates="user")
    projects = relationship("Project", back_populates="user")
    education = relationship("Education", back_populates="user")
    achievements = relationship("Achievement", back_populates="user")
    contacts = relationship("Contact", back_populates="user")
    skills = relationship("Skill", back_populates="user")


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


# New models for specific resume sections

class General(Base):
    __tablename__ = "general"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=True)
    fullName = Column(String, nullable=True)
    occupation = Column(String, nullable=True)
    location = Column(String, nullable=True)
    website = Column(String, nullable=True)
    about = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    include_summary = Column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="general")


class WorkExperience(Base):
    __tablename__ = "work_experiences"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=True)
    company = Column(String, nullable=True)
    location = Column(String, nullable=True)
    is_disabled = Column(Boolean, default=False)
    startDate = Column(String, nullable=True)
    endDate = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    url = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    user = relationship("User", back_populates="work_experiences")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    startDate = Column(String, nullable=True)
    endDate = Column(String, nullable=True)
    url = Column(String, nullable=True)
    is_disabled = Column(Boolean, default=False)
    stack = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    user = relationship("User", back_populates="projects")


class Education(Base):
    __tablename__ = "education"

    id = Column(Integer, primary_key=True, index=True)
    startDate = Column(String, nullable=True)
    endDate = Column(String, nullable=True)
    institution = Column(String, nullable=True)
    degree = Column(String, nullable=True)
    location = Column(String, nullable=True)
    is_disabled = Column(Boolean, default=False)
    url = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    user = relationship("User", back_populates="education")


class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    startDate = Column(String, nullable=True)
    is_disabled = Column(Boolean, default=False)
    url = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    user = relationship("User", back_populates="achievements")


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    media = Column(String, nullable=True)
    link = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    user = relationship("User", back_populates="contacts")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=True)
    stack = Column(String, nullable=True)
    is_disabled = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    user = relationship("User", back_populates="skills")



class FeedbackSession(Base):
    __tablename__ = "feedback_sessions"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=True)
    pdf_object = Column(String, nullable=True)
    slug = Column(String, unique=True, index=True)        # short id for url
    token = Column(String, unique=True, index=True, default=gen_token)  # share token
    is_open = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User")
    reviews = relationship("FeedbackReview", back_populates="session", cascade="all,delete")

class FeedbackReview(Base):
    __tablename__ = "feedback_reviews"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("feedback_sessions.id"), nullable=False)
    reviewer_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # optional if logged in
    reviewer_name = Column(String, nullable=True)   # if anonymous
    reviewer_email = Column(String, nullable=True)  # if anonymous
    submitted_at = Column(DateTime, nullable=True)  # null until “Submit feedback” clicked
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("FeedbackSession", back_populates="reviews")
    reviewer_user = relationship("User")
    comments = relationship("FeedbackComment", back_populates="review", cascade="all,delete")

    __table_args__ = (
        UniqueConstraint("session_id", "reviewer_user_id", name="uq_session_reviewer_user"),
    )

class FeedbackComment(Base):
    __tablename__ = "feedback_comments"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("feedback_reviews.id"), nullable=False)
    page = Column(Integer, nullable=False)                 # 1-based page
    quote = Column(Text, nullable=True)                    # exact selected text snapshot
    # bbox list encoded as JSON string: e.g. [{"x":..., "y":..., "w":..., "h":...}, ...] in text layer coords
    rects_json = Column(Text, nullable=False)
    note = Column(Text, nullable=False)                    # comment body
    sentiment = Column(String, nullable=True)              # "positive" | "negative" | "neutral"
    created_at = Column(DateTime, default=datetime.utcnow)

    review = relationship("FeedbackReview", back_populates="comments")


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(String, nullable=False)
    highlight_positions = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)



