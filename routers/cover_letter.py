# routers/cover_letter.py
from typing import Literal, Optional

import os, re, io, json
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from utils import get_current_user        # same helper you already use
import models

# ─── Gemini / OpenAI setup ───────────────────────────────────────────────
import google.generativeai as genai
from google.generativeai import GenerativeModel

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-preview-05-20")

# ─── Re‑use the pdf → text helper from import_resume.py ──────────────────
from import_resume import _pdf_to_text    # already written earlier

router = APIRouter(prefix="/ai/cover-letter", tags=["cover‑letter"])


class CoverLetterOut(BaseModel):
    letter: str


@router.post("/generate", response_model=CoverLetterOut,
             summary="Generate a tailored cover letter via Gemini")
async def generate_cover_letter(
    jobDescription: str = Form(...),
    jobTitle: str       = Form(...),
    companyName: str    = Form(...),
    template: Literal["skills", "creative", "stanford", "mit", "harvard"] = Form(...),
    tone: Literal["professional", "casual", "enthusiastic", "informational"] = Form(...),
    length: Literal["short", "medium", "long"] = Form(...),
    wordCount: int | None = Form(None),
    language: str       = Form("English"),
    additionalContext:  str = Form(""),
    resume: Optional[UploadFile] = File(None),

    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Uses Gemini to craft a cover‑letter.  
    – If a PDF résumé is supplied, its plain text is injected as extra context.  
    – The response is *plain text* returned as JSON → `{ \"letter\": \"…\" }`.
    """
    resume_text = ""
    if resume:
        if resume.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Only PDF résumés are accepted")
        pdf_bytes = await resume.read()
        resume_text = _pdf_to_text(pdf_bytes)


    # Minimal template instructions – the FE’s big placeholders are *examples*
    template_directives = {
        "skills":   "Follow the Skills‑Focused structure (5 paragraphs as in UI).",
        "creative": "Follow the Creative structure (5 paragraphs as in UI).",
        "stanford": "Follow the Stanford University 4‑paragraph guidance in UI.",
        "mit":      "Follow the MIT 3‑paragraph guidance in UI.",
        "harvard":  "Follow the Harvard 3‑paragraph guidance in UI.",
    }[template]

    prompt = f"""
You are an elite career‑coach and persuasive business writer.  Craft a
flawless *cover letter* that makes the reader eager to interview the
candidate.

=== OUTPUT GUIDELINES ===
1. Language  : {language}
2. Tone      : {tone}
3. Structure : follow the {template_directives} outline.
4. Salutation: open with “Dear {companyName} hiring team,” (or similar).
5. Paragraphs: 4–5, each ≤ 4 sentences.  Use *first‑person* (“I” / “my”)
   naturally, vary sentence openers, and avoid jargon.
6. Content   :
   • First   : state the role and hook the reader with enthusiasm +
     1 standout qualification.
   • Middle  : weave 2‑3 achievements *quantified* with metrics that
     perfectly match the job requirements & ATS keywords.
   • Penult. : show specific knowledge of {companyName}’s products,
     values or recent news and explain cultural fit.
   • Final   : confident call‑to‑action + polite thanks.
7. Keywords  : echo terminology from the job description below.
8. Style    : professional yet warm; no headings, lists, code fences or
   bullet points.  Plain text only.

=== POSITION ===
Job Title : {jobTitle}

=== COMPANY ===
{companyName}

=== JOB DESCRIPTION ===
{jobDescription.strip()}

=== CANDIDATE RESUME (plain‑text) ===
{resume_text.strip()[:6000] or '— none provided —'}

=== ADDITIONAL USER NOTES ===
{additionalContext.strip() or '— none —'}
"""

    
    if wordCount:
        prompt += f"\n\nThe letter should be around {wordCount} words."

    model = GenerativeModel(MODEL_NAME)
    resp = model.generate_content(prompt)

    # Gemini often returns exactly what we want; still strip accidental markdown fences
    letter = re.sub(r"^```.*?\\n|\\n```$", "", resp.text, flags=re.S).strip()

    if not letter:
        raise HTTPException(status_code=500, detail="Failed to generate cover letter")

    return {"letter": letter}
