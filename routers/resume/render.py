import os
import subprocess
from typing import Optional

from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session
import models
import schemas
from latex_template import generate_latex_from_complete_resume
from database import get_db
from utils import get_current_user
from fastapi import Response, UploadFile, File
import tempfile
from helpers.resume import get_complete_resume, _render_my_cv
from pydantic import BaseModel
from fastapi import APIRouter

router = APIRouter()


@router.post("/latex/me")
@router.get("/latex/me")  # <-- new alias
def render_my_latex_cv(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user),
):
    return _render_my_cv(db, current_user)


# --- New endpoint: Render my LaTeX source file ---
@router.post("/latex/file/me")
def render_my_latex_source_me(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    resume_data = get_complete_resume(current_user.id, db)
    latex_src = generate_latex_from_complete_resume(resume_data)
    return Response(content=latex_src, media_type="text/plain")


@router.post("/latex/public")
async def render_public_latex_cv(resume_data: schemas.CompleteResume,
                                 section_order: Optional[str] = Query(None, description="Comma-separated list of sections: education,work,projects,achievements,skills")
                                 ):


    sections = None
    if section_order:
        sections = [s.strip() for s in section_order.split(",") if s.strip()]
    # 1. Generate the .tex source
    latex_src = generate_latex_from_complete_resume(resume_data, section_order=sections)

    # 2. Create a temp dir and write resume.tex
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "resume.tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(latex_src)

        # 3. Run pdflatex (twice is often needed for refs/toc, but once is enough for simple CVs)
        cmd = ["pdflatex", "-interaction=nonstopmode", "resume.tex"]
        proc = subprocess.run(cmd, cwd=tmpdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            log = proc.stdout.decode("utf-8", errors="ignore") + "\n" + proc.stderr.decode("utf-8", errors="ignore")
            raise HTTPException(status_code=500, detail=f"LaTeX compilation failed:\n{log}")

        # 4. Read out the PDF
        pdf_path = os.path.join(tmpdir, "resume.pdf")
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=500, detail="PDF not found after compilation.")

        with open(pdf_path, "rb") as pdf_file:
            pdf_bytes = pdf_file.read()

    # 5. Return the PDF bytes
    return Response(content=pdf_bytes, media_type="application/pdf")


# --- New endpoint: Render public LaTeX source file ---
@router.post("/latex/file/public")
def render_public_latex_source(
        resume_data: schemas.CompleteResume
):
    latex_src = generate_latex_from_complete_resume(resume_data)
    return Response(content=latex_src, media_type="text/plain")

