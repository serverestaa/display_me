# tasks/apply.py
import json, asyncio, os, time
from celery import Celery
from browser_use import BrowserSession
from redis import Redis
from .gemini import write_cover_letter
from .scrape import find_easy_apply_jobs, apply_to_job
from sqlalchemy.orm import Session
from database import SessionLocal        # or your helper
from utilsl.crypto import decrypt
import models
from tasks.playwright_helpers import ensure_logged_in

celery_app = Celery("tasks", broker=os.getenv("REDIS_URL"))

redis = Redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)

def _progress(task_id: str, msg: str, pct: int):
    redis.publish(f"progress:{task_id}", json.dumps({"msg": msg, "pct": pct}))

@celery_app.task(name="apply_linkedin_jobs")
def enqueue_apply_task(task_id: str, pdf: str, title: str, user_id: str):
    asyncio.run(run_apply_flow(task_id, pdf, title, user_id))

async def run_apply_flow(task_id, pdf_path, title, user_id):
    # --- fetch user & decrypt creds ---
    db: Session = SessionLocal()
    user = db.query(models.User).get(user_id)
    if not user or not (user.li_email and user.li_pwd_enc):
        raise RuntimeError("LinkedIn credentials not set for user")

    email = user.li_email
    password = decrypt(user.li_pwd_enc)
    db.close()

    session = BrowserSession(                  # ⬅ single object gives you
        user_data_dir=f"linkedin_user_{user_id}",  #   playwright, context & page
        headless=True,
        locale="en-US",
        stealth=True,                          # better anti-bot defaults
        allowed_domains=["https://www.linkedin.com"],
    )
    await session.launch()                     # prepares playwright & opens a tab
    page = session.page

    # ----- NEW: login step -----
    try:
        await ensure_logged_in(page, email, password)
    except RuntimeError as e:
        await session.close()
        _progress(task_id, str(e), 100)
        return

    _progress(task_id, "Searching jobs…", 5)
    jobs = await find_easy_apply_jobs(page, title, limit=30)

    for idx, job in enumerate(jobs, start=1):
        _progress(task_id, f"Applying {idx}/{len(jobs)}: {job['title']}", 5+idx*90//len(jobs))
        cover_letter = await write_cover_letter(job["description"])
        applied = await apply_to_job(page, job, pdf_path, cover_letter)
        if not applied:
            _progress(task_id, f"Skipped (complex form): {job['title']}", 5+idx*90//len(jobs))

    await browser.close()
    await p.stop()
    _progress(task_id, "Done ✔", 100)


async def run_apply_flow(task_id, pdf_path, title, user_id):
    ...
    # ----- launch browser-use session -----
    session = BrowserSession(
        user_data_dir=f"linkedin_user_{user_id}",
        headless=True,
        locale="en-US",
        stealth=True,
        allowed_domains=["https://www.linkedin.com"],
    )
    await session.launch()
    page = session.page

    try:
        await ensure_logged_in(page, email, password)
    except RuntimeError as e:
        await session.close()
        _progress(task_id, str(e), 100)
        return

    _progress(task_id, "Searching jobs…", 5)
    try:
        jobs = await find_easy_apply_jobs(page, title, limit=30)
    except RuntimeError as err:
        await session.close()
        _progress(task_id, str(err), 100)
        return

    for idx, job in enumerate(jobs, start=1):
        ...
    await session.close()
    _progress(task_id, "Done ✔", 100)
