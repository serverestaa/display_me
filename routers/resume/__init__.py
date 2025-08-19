from fastapi import APIRouter

from routers.resume import generate, achievements, contacts, education, general, projects, render, skills, users, workExp, impoort, feedback, feedback_sessions

router = APIRouter(prefix="/resume")

router.include_router(generate.router, prefix="", tags=["resume-generation"])
router.include_router(achievements.router, prefix="/achievements", tags=["resume-achievements"])
router.include_router(contacts.router, prefix="/contacts", tags=["resume-contacts"])
router.include_router(education.router, prefix="/education", tags=["resume-education"])
router.include_router(general.router, prefix="/general", tags=["resume-general"])
router.include_router(projects.router, prefix="/projects", tags=["resume-projects"])
router.include_router(render.router, prefix="/render", tags=["resume-render"])
router.include_router(skills.router, prefix="/skills", tags=["resume-skills"])
router.include_router(users.router, prefix="/users", tags=["resume-users"])
router.include_router(workExp.router, prefix="/work-experience", tags=["resume-workExp"])
router.include_router(impoort.router, prefix="/import", tags=["resume-import"])
router.include_router(feedback.router, prefix="/feedback", tags=["resume-feedback"])
router.include_router(feedback_sessions.router, prefix="", tags=["resume-feedback-sessions"])

