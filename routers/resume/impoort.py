from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
import models
import schemas
from database import get_db
from utils import get_current_user
from fastapi import  UploadFile, File
from import_resume import _pdf_to_text, _ask_gemini_for_json, import_resume_from_json, replace_resume_from_json
from fastapi.responses import JSONResponse

from pydantic import BaseModel
from fastapi import APIRouter

router = APIRouter()


@router.post("/resume", response_model=schemas.CompleteResume,
             summary="Upload a PDF résumé and populate DB using Gemini")
async def import_resume(
        file: UploadFile = File(..., description="PDF only"),
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    pdf_bytes = await file.read()
    try:
        plain = _pdf_to_text(pdf_bytes)
        parsed = _ask_gemini_for_json(plain)
    except Exception as exc:
        raise HTTPException(status_code=500,
                            detail=f"Gemini parsing failed: {exc!s}")
    import_resume_from_json(current_user, parsed, db)
    # send the freshly imported data back so the client UI can refresh
    return get_complete_resume(current_user.id, db)


@router.post("/resume/preview",
             summary="Upload a PDF and get parsed JSON back (does NOT touch DB)")
async def import_resume_preview(
        file: UploadFile = File(..., description="PDF only"),
        current_user: models.User = Depends(get_current_user)  # only to enforce auth
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    pdf_bytes = await file.read()
    try:
        plain = _pdf_to_text(pdf_bytes)
        parsed = _ask_gemini_for_json(plain)  # <- Gemini/ChatGPT call
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gemini parsing failed: {exc}")

    return JSONResponse(content=parsed)


class ResumeImport(BaseModel):
    general: dict | None = None
    workExperience: list[dict] = []
    projects: list[dict] = []
    education: list[dict] = []
    achievements: list[dict] = []
    skills: list[dict] = []
    contacts: list[dict] = []


# ---- STEP 2  User pressed “Accept” -> wipe & insert ----
@router.post("/resume/commit", response_model=schemas.CompleteResume,
             summary="Accept preview JSON and overwrite resume")
def import_resume_commit(
        resume: ResumeImport,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    replace_resume_from_json(current_user, resume.dict(exclude_none=True), db)
    return get_complete_resume(current_user.id, db)