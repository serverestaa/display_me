from utils import get_current_user

import subprocess
from fastapi import Response, APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session
from database import engine, Base, get_db
from models import User, Section
from latex_template import generate_latex

router = APIRouter()

@router.get("/latex")
def get_resume_latex(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Возвращает итоговый LaTeX текст для текущего пользователя.
    """
    user = current_user  # уже авторизован
    sections = db.query(Section).filter(Section.user_id == user.id).all()

    latex_code = generate_latex(user, sections)
    return latex_code


@router.get("/pdf")
def get_resume_pdf(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = current_user
    sections = db.query(Section).filter(Section.user_id == user.id).all()

    latex_code = generate_latex(user, sections)

    tex_filename = f"resume_{user.id}.tex"
    pdf_filename = f"resume_{user.id}.pdf"

    with open(tex_filename, "w", encoding="utf-8") as f:
        f.write(latex_code)

    # Компилируем pdflatex
    for _ in range(2):
        subprocess.run(["pdflatex", "-interaction=nonstopmode", tex_filename], check=True)

    with open(pdf_filename, "rb") as f:
        pdf_data = f.read()

    return Response(content=pdf_data, media_type="application/pdf")
