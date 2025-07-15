from utils import get_current_user

from fastapi import APIRouter
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from database import engine, Base, get_db
import schemas
from models import User, Section, Block

router = APIRouter(prefix="/blocks", tags=["blocks"])

@router.delete("/{block_id}")
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


@router.put("/{block_id}", response_model=schemas.BlockRead)
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


@router.patch("/{block_id}/activate")
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


@router.patch("/order")
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