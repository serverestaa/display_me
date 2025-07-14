from fastapi import APIRouter

from routers.resume import generate, achievements, contacts, education, general, projects, render, skills, users, workExp, impoort

router = APIRouter(prefix="/resume", tags=["resume"])

router.include_router(generate.router, prefix="/", tags=["resume-generation"])
router.include_router(achievements.router, prefix="/achievements", tags=["achievements"])
router.include_router(contacts.router, prefix="/contacts", tags=["contacts"])
router.include_router(education.router, prefix="/education", tags=["education"])
router.include_router(general.router, prefix="/general", tags=["general"])
router.include_router(projects.router, prefix="/projects", tags=["projects"])
router.include_router(render.router, prefix="/render", tags=["render"])
router.include_router(skills.router, prefix="/skills", tags=["skills"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(workExp.router, prefix="/work-experience", tags=["workExp"])
router.include_router(impoort.router, prefix="/import", tags=["import"])


