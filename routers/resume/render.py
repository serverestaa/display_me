# routers/resume/render.py
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from helpers.resume import get_complete_resume, get_complete_resume_with_enabled_entities
from helpers.sort_resume import sort_resume_inplace
from latex_template import generate_latex_from_complete_resume
from utils import get_current_user

router = APIRouter(prefix="", tags=["render"])

DEFAULT_ORDER = ["education", "workExperience", "projects", "achievements", "skills"]
ALLOWED_ORDER = set(DEFAULT_ORDER)


# ------------------------------ helpers ------------------------------

def _resolve_saved_order(user: models.User) -> List[str]:
    if not user.sections_order:
        return DEFAULT_ORDER
    try:
        data = json.loads(user.sections_order)
        clean = [k for k in data if k in ALLOWED_ORDER]
        return clean or DEFAULT_ORDER
    except Exception:
        return DEFAULT_ORDER


def _compile_tex_to_pdf_bytes(latex_src: str) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "resume.tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(latex_src)

        # Run pdflatex twice for stable refs
        for _ in range(2):
            proc = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "resume.tex"],
                cwd=tmpdir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if proc.returncode != 0:
                log = proc.stdout.decode("utf-8", errors="ignore") + "\n" + proc.stderr.decode("utf-8", errors="ignore")
                raise HTTPException(status_code=500, detail=f"LaTeX compilation failed:\n{log}")

        pdf_path = os.path.join(tmpdir, "resume.pdf")
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=500, detail="PDF not found after compilation.")

        with open(pdf_path, "rb") as pdf_file:
            return pdf_file.read()


def _build_resume_from_body(body: Dict[str, Any]) -> schemas.CompleteResume:
    """
    Строит CompleteResume из произвольного JSON тела (как у превью).
    Отсутствующие поля подставляются как пустые списки.
    """
    return schemas.CompleteResume(
        general=body.get("general"),
        workExperience=body.get("workExperience", []),
        projects=body.get("projects", []),
        education=body.get("education", []),
        achievements=body.get("achievements", []),
        skills=body.get("skills", []),
        contacts=body.get("contacts", []),
    )



# ------------------------------ order endpoints ------------------------------

@router.get("/sections-order", response_model=schemas.SectionsOrderRead)
def get_sections_order(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return {"sections": _resolve_saved_order(current_user)}


@router.put("/sections-order", response_model=schemas.SectionsOrderRead)
def put_sections_order(
    payload: schemas.SectionsOrderUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    clean = [k for k in payload.sections if k in ALLOWED_ORDER]
    if not clean:
        clean = DEFAULT_ORDER
    current_user.sections_order = json.dumps(clean)
    db.add(current_user)
    db.commit()
    return {"sections": clean}


# ------------------------------ me (PDF) ------------------------------

@router.post("/latex/me")
@router.get("/latex/me")  # alias
def render_my_latex_cv(
    body: Optional[Dict[str, Any]] = Body(default=None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    POST: принимает body с полями резюме и optional sectionsOrder для live-превью.
    GET: рендерит по данным из БД и сохранённому порядку.
    """
    # determine order
    saved_order = _resolve_saved_order(current_user)
    sections_order = None

    resume_data: schemas.CompleteResume
    if body:
        # client preview payload
        so = body.get("sectionsOrder")
        if isinstance(so, list):
            sections_order = [k for k in so if k in ALLOWED_ORDER] or saved_order
        else:
            sections_order = saved_order

        resume_data = _build_resume_from_body(body)
    else:
        # from DB with enabled entities
        sections_order = saved_order
        resume_data = get_complete_resume_with_enabled_entities(current_user.id, db)

    sort_resume_inplace(resume_data)

    latex_src = generate_latex_from_complete_resume(resume_data, sections_order)
    pdf_bytes = _compile_tex_to_pdf_bytes(latex_src)

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=resume_{current_user.id}.pdf"},
    )




# ------------------------------ me (TEX) ------------------------------

@router.post("/latex/file/me")
def render_my_latex_source_me(
    body: Optional[Dict[str, Any]] = Body(default=None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Возвращает исходник LaTeX. Принимает те же поля что и /latex/me.
    """
    saved_order = _resolve_saved_order(current_user)

    if body:
        sections_order = [k for k in body.get("sectionsOrder", []) if k in ALLOWED_ORDER] or saved_order
        resume_data = _build_resume_from_body(body)
    else:
        sections_order = saved_order
        resume_data = get_complete_resume(current_user.id, db)

    sort_resume_inplace(resume_data)

    latex_src = generate_latex_from_complete_resume(resume_data, sections_order)
    return Response(content=latex_src, media_type="text/plain")


# ------------------------------ public (PDF) ------------------------------

@router.post("/latex/public")
def render_public_latex_cv(
    resume_data: schemas.CompleteResume,
):
    # Публичная версия — фиксированный порядок.
    latex_src = generate_latex_from_complete_resume(resume_data, DEFAULT_ORDER)
    pdf_bytes = _compile_tex_to_pdf_bytes(latex_src)
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=resume_public.pdf"},
    )


# ------------------------------ public (TEX) ------------------------------

@router.post("/latex/file/public")
def render_public_latex_source(
    resume_data: schemas.CompleteResume,
):
    latex_src = generate_latex_from_complete_resume(resume_data, DEFAULT_ORDER)
    return Response(content=latex_src, media_type="text/plain")
