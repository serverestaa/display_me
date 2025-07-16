

from utils import get_current_user

from fastapi import APIRouter
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import schemas
from models import User, Section, Block

# ---------------------- SECTIONS endpoints ----------------------

router = APIRouter(prefix="/sections", tags=["sections"])


@router.post("/", response_model=schemas.SectionRead)
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

@router.get("/{section_id}", response_model=schemas.SectionRead)
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

@router.delete("/{section_id}")
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


@router.put("/{section_id}", response_model=schemas.SectionRead)
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


@router.patch("/{section_id}/activate")
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


@router.patch("/order")
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

@router.post("/{section_id}/blocks/", response_model=schemas.BlockRead)
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