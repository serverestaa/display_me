import os
import subprocess

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Response
from sqlalchemy.orm import Session
from typing import List
import tempfile
import models
import schemas
from latex_template import generate_latex_from_complete_resume
from database import get_db
from utils import get_current_user
from fastapi import Response, UploadFile, File
import tempfile
from import_resume import _pdf_to_text, _ask_gemini_for_json, import_resume_from_json, replace_resume_from_json
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi import Body
from typing import Any

from pydantic import BaseModel
router = APIRouter()

# ----- General Information Endpoints -----

@router.post("/general/", response_model=schemas.GeneralRead)
def create_general(
        general_in: schemas.GeneralCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # Check if general info already exists
    existing = db.query(models.General).filter(models.General.user_id == current_user.id).first()
    if existing:
        # Update existing
        for key, value in general_in.dict().items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing

    # Create new
    general = models.General(**general_in.dict(), user_id=current_user.id)
    db.add(general)
    db.commit()
    db.refresh(general)
    return general


@router.get("/general/", response_model=schemas.GeneralRead)
def get_general(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    general = db.query(models.General).filter(models.General.user_id == current_user.id).first()
    if not general:
        general = models.General(username = current_user.username,
            fullName = None,
            occupation = None,
            location = None,
            website = None,
            about = None,
            user_id = current_user.id)
        db.add(general)
        db.commit()
        db.refresh(general)
    return general


@router.put("/general/", response_model=schemas.GeneralRead)
def update_general(
        general_in: schemas.GeneralUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    general = db.query(models.General).filter(models.General.user_id == current_user.id).first()
    if not general:
        # Create if doesn't exist
        general = models.General(**general_in.dict(), user_id=current_user.id)
        db.add(general)
    else:
        # Update existing
        for key, value in general_in.dict(exclude_unset=True).items():
            setattr(general, key, value)

    db.commit()
    db.refresh(general)
    return general


# ----- Work Experience Endpoints -----

@router.post("/work-experience/", response_model=schemas.WorkExperienceRead)
def create_work_experience(
        work_exp_in: schemas.WorkExperienceCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    work_exp = models.WorkExperience(**work_exp_in.dict(), user_id=current_user.id)
    db.add(work_exp)
    db.commit()
    db.refresh(work_exp)
    return work_exp


@router.get("/work-experience/", response_model=List[schemas.WorkExperienceRead])
def get_work_experiences(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    work_exps = db.query(models.WorkExperience).filter(models.WorkExperience.user_id == current_user.id).all()
    return work_exps


@router.get("/work-experience/{work_exp_id}", response_model=schemas.WorkExperienceRead)
def get_work_experience(
        work_exp_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    work_exp = db.query(models.WorkExperience).filter(
        models.WorkExperience.id == work_exp_id,
        models.WorkExperience.user_id == current_user.id
    ).first()
    if not work_exp:
        raise HTTPException(status_code=404, detail="Work experience not found")
    return work_exp


@router.put("/work-experience/{work_exp_id}", response_model=schemas.WorkExperienceRead)
def update_work_experience(
        work_exp_id: int,
        work_exp_in: schemas.WorkExperienceUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    work_exp = db.query(models.WorkExperience).filter(
        models.WorkExperience.id == work_exp_id,
        models.WorkExperience.user_id == current_user.id
    ).first()
    if not work_exp:
        raise HTTPException(status_code=404, detail="Work experience not found")

    for key, value in work_exp_in.dict(exclude_unset=True).items():
        setattr(work_exp, key, value)

    db.commit()
    db.refresh(work_exp)
    return work_exp

@router.patch("/work-experience/{wid}/disable")
def toggle_we_disable(
        wid: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    work_exp = db.query(models.WorkExperience).filter(
        models.WorkExperience.id == wid,
        models.WorkExperience.user_id == current_user.id
    ).first()
    if not work_exp:
        raise HTTPException(status_code=404, detail="Work experience not found")

    work_exp.is_disabled = not work_exp.is_disabled
    db.commit()
    db.refresh(work_exp)
    return {"message": "Work experience updated", "is_disabled": work_exp.is_disabled}


@router.delete("/work-experience/{work_exp_id}")
def delete_work_experience(
        work_exp_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    work_exp = db.query(models.WorkExperience).filter(
        models.WorkExperience.id == work_exp_id,
        models.WorkExperience.user_id == current_user.id
    ).first()
    if not work_exp:
        raise HTTPException(status_code=404, detail="Work experience not found")

    db.delete(work_exp)
    db.commit()
    return {"message": "Work experience deleted"}


# ----- Project Endpoints -----

@router.post("/projects/", response_model=schemas.ProjectRead)
def create_project(
        project_in: schemas.ProjectCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    project = models.Project(**project_in.dict(), user_id=current_user.id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/projects/", response_model=List[schemas.ProjectRead])
def get_projects(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    projects = db.query(models.Project).filter(models.Project.user_id == current_user.id).all()
    return projects


@router.get("/projects/{project_id}", response_model=schemas.ProjectRead)
def get_project(
        project_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.patch("/projects/{project_id}/disable")
def toggle_project_disable(
        project_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.is_disabled = not project.is_disabled
    db.commit()
    db.refresh(project)
    return {"message": "Project updated", "is_disabled": project.is_disabled}

@router.put("/projects/{project_id}", response_model=schemas.ProjectRead)
def update_project(
        project_id: int,
        project_in: schemas.ProjectUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for key, value in project_in.dict(exclude_unset=True).items():
        setattr(project, key, value)

    db.commit()
    db.refresh(project)
    return project


@router.delete("/projects/{project_id}")
def delete_project(
        project_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()
    return {"message": "Project deleted"}


# ----- Education Endpoints -----

@router.post("/education/", response_model=schemas.EducationRead)
def create_education(
        education_in: schemas.EducationCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    education = models.Education(**education_in.dict(), user_id=current_user.id)
    db.add(education)
    db.commit()
    db.refresh(education)
    return education


@router.get("/education/", response_model=List[schemas.EducationRead])
def get_educations(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    educations = db.query(models.Education).filter(models.Education.user_id == current_user.id).all()
    return educations


@router.get("/education/{education_id}", response_model=schemas.EducationRead)
def get_education(
        education_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    education = db.query(models.Education).filter(
        models.Education.id == education_id,
        models.Education.user_id == current_user.id
    ).first()
    if not education:
        raise HTTPException(status_code=404, detail="Education not found")
    return education


@router.patch("/education/{education_id}/disable")
def toggle_education_disable(
        education_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    education = db.query(models.Education).filter(
        models.Education.id == education_id,
        models.Education.user_id == current_user.id
    ).first()
    if not education:
        raise HTTPException(status_code=404, detail="Education not found")

    education.is_disabled = not education.is_disabled
    db.commit()
    db.refresh(education)
    return {"message": "Education updated", "is_disabled": education.is_disabled}

@router.put("/education/{education_id}", response_model=schemas.EducationRead)
def update_education(
        education_id: int,
        education_in: schemas.EducationUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    education = db.query(models.Education).filter(
        models.Education.id == education_id,
        models.Education.user_id == current_user.id
    ).first()
    if not education:
        raise HTTPException(status_code=404, detail="Education not found")

    for key, value in education_in.dict(exclude_unset=True).items():
        setattr(education, key, value)

    db.commit()
    db.refresh(education)
    return education


@router.delete("/education/{education_id}")
def delete_education(
        education_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    education = db.query(models.Education).filter(
        models.Education.id == education_id,
        models.Education.user_id == current_user.id
    ).first()
    if not education:
        raise HTTPException(status_code=404, detail="Education not found")

    db.delete(education)
    db.commit()
    return {"message": "Education deleted"}


# ----- Achievement Endpoints -----

@router.post("/achievements/", response_model=schemas.AchievementRead)
def create_achievement(
        achievement_in: schemas.AchievementCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    achievement = models.Achievement(**achievement_in.dict(), user_id=current_user.id)
    db.add(achievement)
    db.commit()
    db.refresh(achievement)
    return achievement


@router.get("/achievements/", response_model=List[schemas.AchievementRead])
def get_achievements(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    achievements = db.query(models.Achievement).filter(models.Achievement.user_id == current_user.id).all()
    return achievements


@router.get("/achievements/{achievement_id}", response_model=schemas.AchievementRead)
def get_achievement(
        achievement_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    achievement = db.query(models.Achievement).filter(
        models.Achievement.id == achievement_id,
        models.Achievement.user_id == current_user.id
    ).first()
    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found")
    return achievement


@router.patch("/achievements/{achievement_id}/disable")
def toggle_achievement_disable(
        achievement_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    achievement = db.query(models.Achievement).filter(
        models.Achievement.id == achievement_id,
        models.Achievement.user_id == current_user.id
    ).first()
    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found")

    achievement.is_disabled = not achievement.is_disabled
    db.commit()
    db.refresh(achievement)
    return {"message": "Achievement updated", "is_disabled": achievement.is_disabled}

@router.put("/achievements/{achievement_id}", response_model=schemas.AchievementRead)
def update_achievement(
        achievement_id: int,
        achievement_in: schemas.AchievementUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    achievement = db.query(models.Achievement).filter(
        models.Achievement.id == achievement_id,
        models.Achievement.user_id == current_user.id
    ).first()
    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found")

    for key, value in achievement_in.dict(exclude_unset=True).items():
        setattr(achievement, key, value)

    db.commit()
    db.refresh(achievement)
    return achievement


@router.delete("/achievements/{achievement_id}")
def delete_achievement(
        achievement_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    achievement = db.query(models.Achievement).filter(
        models.Achievement.id == achievement_id,
        models.Achievement.user_id == current_user.id
    ).first()
    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found")

    db.delete(achievement)
    db.commit()
    return {"message": "Achievement deleted"}


# ----- Contact Endpoints -----

@router.post("/contacts/", response_model=schemas.ContactRead)
def create_contact(
        contact_in: schemas.ContactCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    contact = models.Contact(**contact_in.dict(), user_id=current_user.id)
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.get("/contacts/", response_model=List[schemas.ContactRead])
def get_contacts(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    contacts = db.query(models.Contact).filter(models.Contact.user_id == current_user.id).all()
    return contacts


@router.get("/contacts/{contact_id}", response_model=schemas.ContactRead)
def get_contact(
        contact_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    contact = db.query(models.Contact).filter(
        models.Contact.id == contact_id,
        models.Contact.user_id == current_user.id
    ).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.put("/contacts/{contact_id}", response_model=schemas.ContactRead)
def update_contact(
        contact_id: int,
        contact_in: schemas.ContactUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    contact = db.query(models.Contact).filter(
        models.Contact.id == contact_id,
        models.Contact.user_id == current_user.id
    ).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    for key, value in contact_in.dict(exclude_unset=True).items():
        setattr(contact, key, value)

    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/contacts/{contact_id}")
def delete_contact(
        contact_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    contact = db.query(models.Contact).filter(
        models.Contact.id == contact_id,
        models.Contact.user_id == current_user.id
    ).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    db.delete(contact)
    db.commit()
    return {"message": "Contact deleted"}


# ----- Skill Endpoints -----

@router.post("/skills/", response_model=schemas.SkillRead)
def create_skill(
        skill_in: schemas.SkillCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    skill = models.Skill(**skill_in.dict(), user_id=current_user.id)
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


@router.get("/skills/", response_model=List[schemas.SkillRead])
def get_skills(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    skills = db.query(models.Skill).filter(models.Skill.user_id == current_user.id).all()
    return skills


@router.get("/skills/{skill_id}", response_model=schemas.SkillRead)
def get_skill(
        skill_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    skill = db.query(models.Skill).filter(
        models.Skill.id == skill_id,
        models.Skill.user_id == current_user.id
    ).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.patch("/skills/{skill_id}/disable")
def toggle_skill_disable(
        skill_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    skill = db.query(models.Skill).filter(
        models.Skill.id == skill_id,
        models.Skill.user_id == current_user.id
    ).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    skill.is_disabled = not skill.is_disabled
    db.commit()
    db.refresh(skill)
    return {"message": "Skill updated", "is_disabled": skill.is_disabled}

@router.put("/skills/{skill_id}", response_model=schemas.SkillRead)
def update_skill(
        skill_id: int,
        skill_in: schemas.SkillUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    skill = db.query(models.Skill).filter(
        models.Skill.id == skill_id,
        models.Skill.user_id == current_user.id
    ).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    for key, value in skill_in.dict(exclude_unset=True).items():
        setattr(skill, key, value)

    db.commit()
    db.refresh(skill)
    return skill

@router.put("/users/me/username", response_model=schemas.UserRead)
def update_username(
        username_update: schemas.UserUpdateUsername,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # Check if username is already taken
    existing_user = db.query(models.User).filter(
        models.User.username == username_update.username
    ).first()

    if existing_user and existing_user.id != current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Username already taken"
        )

    current_user.username = username_update.username
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/users/me/full", response_model=schemas.CompleteResume)
def get_my_full_info(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    return get_complete_resume(current_user.id, db)


@router.get("/users/{username}/full", response_model=schemas.CompleteResume)
def get_full_info_by_username(
        username: str,
        db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return get_complete_resume(user.id, db)


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

def _render_my_cv(db: Session, current_user: models.User):
    resume_data = get_complete_resume_with_enabled_entities(current_user.id, db)
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

@router.post("/render/latex/me")
@router.get("/render/latex/me")          # <-- new alias
def render_my_latex_cv(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return _render_my_cv(db, current_user)

# --- New endpoint: Render my LaTeX source file ---
@router.post("/render/latex/file/me")
def render_my_latex_source_me(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    resume_data = get_complete_resume(current_user.id, db)
    latex_src = generate_latex_from_complete_resume(resume_data)
    return Response(content=latex_src, media_type="text/plain")


@router.post("/render/latex/public")
async def render_public_latex_cv(resume_data: schemas.CompleteResume):
    # 1. Generate the .tex source
    latex_src = generate_latex_from_complete_resume(resume_data)

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
@router.post("/render/latex/file/public")
def render_public_latex_source(
        resume_data: schemas.CompleteResume
):
    latex_src = generate_latex_from_complete_resume(resume_data)
    return Response(content=latex_src, media_type="text/plain")



@router.post("/import/resume", response_model=schemas.CompleteResume,
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
    

@router.post("/import/resume/preview",
             summary="Upload a PDF and get parsed JSON back (does NOT touch DB)")
async def import_resume_preview(
        file: UploadFile = File(..., description="PDF only"),
        current_user: models.User = Depends(get_current_user)  # only to enforce auth
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    pdf_bytes = await file.read()
    try:
        plain  = _pdf_to_text(pdf_bytes)
        parsed = _ask_gemini_for_json(plain)     # <- Gemini/ChatGPT call
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
@router.post("/import/resume/commit", response_model=schemas.CompleteResume,
             summary="Accept preview JSON and overwrite resume")
def import_resume_commit(
        resume: ResumeImport,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    replace_resume_from_json(current_user, resume.dict(exclude_none=True), db)
    return get_complete_resume(current_user.id, db)
