import os
import subprocess

from sqlalchemy.orm import Session
import models
import schemas
from latex_template import generate_latex_from_complete_resume
import tempfile
from fastapi.responses import StreamingResponse
from helpers.sort_resume import sort_resume_inplace

def get_complete_resume_with_enabled_entities(user_id: int, db: Session):
    general = db.query(models.General).filter(models.General.user_id == user_id).first()
    work_experiences = db.query(models.WorkExperience).filter(
        models.WorkExperience.user_id == user_id,
        models.WorkExperience.is_disabled == False
    ).all()
    projects = db.query(models.Project).filter(
        models.Project.user_id == user_id,
        models.Project.is_disabled == False
    ).all()
    education = db.query(models.Education).filter(
        models.Education.user_id == user_id,
        models.Education.is_disabled == False
    ).all()
    achievements = db.query(models.Achievement).filter(
        models.Achievement.user_id == user_id,
        models.Achievement.is_disabled == False
    ).all()
    skills = db.query(models.Skill).filter(
        models.Skill.user_id == user_id,
        models.Skill.is_disabled == False
    ).all()
    contacts = db.query(models.Contact).filter(models.Contact.user_id == user_id).all()

    return schemas.CompleteResume(
        general=schemas.GeneralRead.from_orm(general) if general else None,
        workExperience=[schemas.WorkExperienceRead.from_orm(w) for w in work_experiences],
        projects=[schemas.ProjectRead.from_orm(p) for p in projects],
        education=[schemas.EducationRead.from_orm(e) for e in education],
        achievements=[schemas.AchievementRead.from_orm(a) for a in achievements],
        skills=[schemas.SkillRead.from_orm(s) for s in skills],
        contacts=[schemas.ContactRead.from_orm(c) for c in contacts],
    )

def get_complete_resume(user_id: int, db: Session):
    general = db.query(models.General).filter(models.General.user_id == user_id).first()
    work_experiences = db.query(models.WorkExperience).filter(models.WorkExperience.user_id == user_id).all()
    projects = db.query(models.Project).filter(models.Project.user_id == user_id).all()
    education = db.query(models.Education).filter(models.Education.user_id == user_id).all()
    achievements = db.query(models.Achievement).filter(models.Achievement.user_id == user_id).all()
    skills = db.query(models.Skill).filter(models.Skill.user_id == user_id).all()
    contacts = db.query(models.Contact).filter(models.Contact.user_id == user_id).all()

    return schemas.CompleteResume(
        general=schemas.GeneralRead.from_orm(general) if general else None,
        workExperience=[schemas.WorkExperienceRead.from_orm(w) for w in work_experiences],
        projects=[schemas.ProjectRead.from_orm(p) for p in projects],
        education=[schemas.EducationRead.from_orm(e) for e in education],
        achievements=[schemas.AchievementRead.from_orm(a) for a in achievements],
        skills=[schemas.SkillRead.from_orm(s) for s in skills],
        contacts=[schemas.ContactRead.from_orm(c) for c in contacts],
    )



def render_my_cv(db: Session, current_user: models.User):
    resume_data = get_complete_resume_with_enabled_entities(current_user.id, db)
    sort_resume_inplace(resume_data)

    latex_output = generate_latex_from_complete_resume(resume_data)

    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "resume.tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(latex_output)

        for _ in range(2):
            subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "resume.tex"],
                cwd=tmpdir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )

        pdf_path = os.path.join(tmpdir, "resume.pdf")
        return StreamingResponse(
            open(pdf_path, "rb"),
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename=resume_{current_user.id}.pdf"},
        )
