# routers/cv_analyzer.py
"""
Analyse a résumé with Gemini, add highlights to the PDF and return
structured scores + notes.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import List

import fitz  # PyMuPDF
import google.generativeai as genai
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from google.generativeai import GenerativeModel

from import_resume import _pdf_to_text
from schemas import CVAnalysisOut, Highlight

# ─── Gemini setup ─────────────────────────────────────────────────────────
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-preview-05-20")

# ─── Router ───────────────────────────────────────────────────────────────
router = APIRouter(prefix="/ai/cv", tags=["cv‑analysis"])


@router.post(
    "/analyze",
    response_model=CVAnalysisOut,
    summary="Analyse résumé for Big‑Tech standards and return annotated PDF",
)
async def analyze_cv(
    target_company: str = Form("Generic‑BigTech"),
    role_title: str = Form("Software Engineer"),
    cv: UploadFile = File(...),
):
    # ── basic validation ──────────────────────────────────────────────────
    if cv.content_type != "application/pdf":
        raise HTTPException(400, "Only PDF files supported")

    pdf_bytes: bytes = await cv.read()
    plain_text: str = _pdf_to_text(pdf_bytes)[:8500]  # keep prompt size sane

    # ── build prompt ──────────────────────────────────────────────────────
    prompt = f"""
You are a top‑tier technical recruiter for {target_company}.
Score the résumé (plain‑text below) for: tech skills, culture/values fit,
leadership/x‑functional impact, and ATS‑readiness.  Produce:
1. Numeric scores (0‑100) for each dimension plus an overall average.
2. **6–8 positive bullet notes (✅)** that spotlight the candidate's strongest phrases or data points.
3. **6–8 improvement bullet notes (❌)** – each must include a **specific, actionable recommendation**.
4. For **every** bullet note include the exact **phrase** from the CV that justifies it. (This will be used to highlight the PDF later.)
5. Up to 4 fresh working, checked, valid updated and curated resources (URLs) that will help the candidate improve, prioritising authoritative best‑practice guides for big‑tech résumés.

Return **only** valid JSON matching this schema:

{{"overall": int,
  "scores": {{"culture_fit": int, "tech_skills": int,
             "leadership": int, "ats": int}},
  "positives": [{{"note": str, "phrase": str}}],
  "negatives": [{{"note": str, "phrase": str}}],
  "resources": [str]     # at most 5 URLs
}}
––––
ROLE : {role_title}
CV  :
{plain_text}
"""

    # ── Gemini call ───────────────────────────────────────────────────────
    model = GenerativeModel(MODEL_NAME)
    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.2,
            "response_mime_type": "application/json",
        },
    )
    raw = response.text

    # ── robust JSON parse ─────────────────────────────────────────────────
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        block = re.search(r"\{.*\}", raw, re.S)
        if not block:
            raise HTTPException(500, "Gemini returned no JSON")
        try:
            parsed = json.loads(block.group(0))
        except json.JSONDecodeError as exc:
            raise HTTPException(500, f"Gemini JSON malformed: {exc}")

    # ── annotate PDF ─────────────────────────────────────────────────────
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    MAX_PAGES = min(doc.page_count, 20)

    highlights: List[Highlight] = []

    for bucket, polarity in (("positives", "positive"), ("negatives", "negative")):
        for item in parsed.get(bucket, []):
            phrase = item["phrase"][:64]  # safety limit
            note = item["note"]

            for page_num in range(MAX_PAGES):
                page = doc[page_num]
                for bbox in page.search_for(phrase):
                    annot = page.add_highlight_annot(bbox)
                    annot.set_colors(
                        stroke=(0, 1, 0) if polarity == "positive" else (1, 0, 0)
                    )
                    annot.set_info(content=note)

                    highlights.append(
                        Highlight(
                            page=page_num + 1,
                            phrase=phrase,
                            bbox=tuple(bbox),
                            note=note,
                            sentiment=polarity,
                        )
                    )

    # ── save annotated PDF ───────────────────────────────────────────────
    Path("static").mkdir(exist_ok=True)
    out_name = cv.filename.replace(".pdf", "_annotated.pdf")
    out_path = f"static/{out_name}"
    doc.save(out_path)

    # ── helper to grab the first note string safely ──────────────────────
    def first_note(bucket: str) -> str:
        try:
            return parsed[bucket][0]["note"]
        except (KeyError, IndexError, TypeError):
            return ""

    recruiter_note = "; ".join(
        n for n in (first_note("negatives"), first_note("positives")) if n
    )

    # ── build API response ───────────────────────────────────────────────
    return CVAnalysisOut(
        overall=parsed["overall"],
        culture_fit=parsed["scores"]["culture_fit"],
        tech_skills=parsed["scores"]["tech_skills"],
        leadership=parsed["scores"]["leadership"],
        ats=parsed["scores"]["ats"],
        positives=[p["note"] for p in parsed["positives"]],
        negatives=[n["note"] for n in parsed["negatives"]],
        recruiter_note=recruiter_note,
        highlights=highlights,
        resources=parsed.get("resources", [])
        + [
            "https://www.amazon.jobs/content/our-workplace/leadership-principles",
            "https://www.techinterviewhandbook.org/resume/",
        ],
    )
