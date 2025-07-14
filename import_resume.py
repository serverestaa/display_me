# import_resume.py
import os, json, io, re
from typing import Dict
from pdfminer.high_level import extract_text
import google.generativeai as genai
from google.generativeai import GenerativeModel
from fastapi import File
from sqlalchemy.orm import Session
from fastapi import HTTPException
import models

# one-time SDK init
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))  # gets key from .env by default

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-preview-05-20")

def _pdf_to_text(pdf_bytes: bytes) -> str:
    """Extract raw text from a PDF file."""
    return extract_text(io.BytesIO(pdf_bytes))

def _ask_gemini_for_json(resume_text: str) -> Dict:
    """
    Calls Gemini in JSON-mode and returns a python dict that
    matches your CompleteResume schema.
    """
    prompt = f"""
You are an API that receives *plain text* resumes and must return
**only** valid JSON conforming to exactly this schema (no markdown):

{{
  "general": {{
    "fullName": "", "location": "",
    "occupation": "", "website": "",
  }},
  "workExperience": [
    {{"title": "", "company": "", "location": "", "startDate": "",
      "endDate": "", "description": "", "url": ""}}
  ],
  "projects": [
    {{"title": "", "description": "", "startDate": "", "endDate": "",
      "stack": "", "url": ""}}
  ],
  "education": [
    {{"institution": "", "degree": "", "location": "",
      "startDate": "", "endDate": "", "description": "", "url": ""}}
  ],
  "achievements": [
    {{"title": "", "description": "", "startDate": "", "url": ""}}
  ],
  "skills": [{{"category": "", "stack": ""}}],
  "contacts": [{{"media": "", "link": ""}}]
}}

Return nothing else.
----
RESUME TEXT
{resume_text}
"""
    model = GenerativeModel(model_name=MODEL_NAME)
    resp = model.generate_content(
        prompt, generation_config={"response_mime_type": "application/json"}
    )
    # Gemini sometimes wraps JSON in markdown fences – strip them:
    m = re.search(r"\{.*\}", resp.text, re.S)
    if not m:
        raise ValueError("Could not locate JSON in Gemini response")
    return json.loads(m.group(0))






def import_resume_from_json(user: models.User, data: Dict, db: Session):
    # ----- General -----
    gen = db.query(models.General).filter_by(user_id=user.id).first()
    if not gen:
        gen = models.General(user_id=user.id)
        db.add(gen)
    _upsert_single(gen, data.get("general", {}), [
        "fullName", "occupation", "location", "website", "about"
    ])
    # ----- Collections -----
    _sync_list(models.WorkExperience,  data.get("workExperience", []),
               ["title", "company", "startDate"], user, db)
    _sync_list(models.Project,         data.get("projects", []),
               ["title", "startDate"], user, db)
    _sync_list(models.Education,       data.get("education", []),
               ["institution", "degree", "startDate"], user, db)
    _sync_list(models.Achievement,     data.get("achievements", []),
               ["title", "startDate"], user, db)
    _sync_list(models.Skill,           data.get("skills", []),
               ["category", "stack"], user, db)
    _sync_list(models.Contact,         data.get("contacts", []),
               ["media"], user, db)
    db.commit()



def _upsert_single(instance, data: dict, fields: list[str]):
    for f in fields:
        if f in data and data[f] is not None:
            setattr(instance, f, data[f])

def _sync_list(model_cls, items: list[dict], uniq_keys: list[str],
               user: models.User, db: Session):
    """
    Generic “create-or-update” for list-type resume entities.
    `uniq_keys` – columns that uniquely identify a row (e.g. title+company).
    """
    existing_map = {
        tuple(getattr(rec, k) for k in uniq_keys): rec
        for rec in db.query(model_cls).filter_by(user_id=user.id).all()
    }
    for item in items:
        key = tuple(item.get(k) for k in uniq_keys)
        rec = existing_map.get(key)
        if not rec:          # create
            rec = model_cls(user_id=user.id)
            db.add(rec)
        _upsert_single(rec, item, item.keys())
    db.flush()       # keep ids incremental



def replace_resume_from_json(user: models.User, data: Dict, db: Session):
    """
    Hard-replace ALL resume entities that belong to `user`
    with the ones contained in `data`.
    Every previous row is deleted first.
    """
    # ---------- purge ----------
    for mdl in (
        models.WorkExperience, models.Project, models.Education,
        models.Achievement,  models.Skill,  models.Contact,
        models.General,      # keep this last so FKs aren't broken
    ):
        db.query(mdl).filter(mdl.user_id == user.id).delete(synchronize_session=False)
    db.flush()   # keep ids monotone – optional but tidy

    # ---------- (re-)create ----------
    # 1) general (single)
    gen_data = data.get("general") or {}
    general = models.General(user_id=user.id, **gen_data)
    db.add(general)

    # 2) collections
    def _bulk(mdl, key):
        for row in data.get(key, []):
            db.add(mdl(user_id=user.id, **row))

    _bulk(models.WorkExperience, "workExperience")
    _bulk(models.Project,        "projects")
    _bulk(models.Education,      "education")
    _bulk(models.Achievement,    "achievements")
    _bulk(models.Skill,          "skills")
    _bulk(models.Contact,        "contacts")

    db.commit()
