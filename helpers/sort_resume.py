# helpers/sort_resume.py
from __future__ import annotations
from datetime import datetime
import re
from typing import Any, Optional

# month maps
_MONTHS = {
    # EN
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
    # RU short
    "янв": 1, "фев": 2, "мар": 3, "апр": 4, "май": 5, "июн": 6,
    "июл": 7, "авг": 8, "сен": 9, "сент": 9, "окт": 10, "ноя": 11, "дек": 12,
    # RU full
    "январь": 1, "февраль": 2, "март": 3, "апрель": 4, "июнь": 6,
    "июль": 7, "август": 8, "сентябрь": 9, "октябрь": 10, "ноябрь": 11, "декабрь": 12,
}

_PRESENT_SENTINELS = (
    "present", "current", "now", "по наст", "по настоящее", "настоящее время",
    "наст.время", "настоящее", "текущее",
)

_PRESENT_DT = datetime(9999, 1, 1)
_MIN_DT = datetime(1, 1, 1)

_year_re = re.compile(r"\b(19|20)\d{2}\b")
_year_month_re = re.compile(r"\b((19|20)\d{2})[-/. ](0?[1-9]|1[0-2])\b")


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    s = str(value).strip().lower()

    if any(tok in s for tok in _PRESENT_SENTINELS):
        return _PRESENT_DT

    m = _year_month_re.search(s)
    if m:
        year = int(m.group(1))
        month = int(m.group(3))
        return datetime(year, month, 1)

    parts = re.split(r"[,\s]+", s)
    if len(parts) >= 2:
        y = None
        mon = None
        for p in parts:
            if p in _MONTHS and mon is None:
                mon = _MONTHS[p]
            elif _year_re.fullmatch(p) and y is None:
                y = int(p)
        if y and mon:
            return datetime(y, mon, 1)

    y = _year_re.search(s)
    if y:
        return datetime(int(y.group(0)), 1, 1)

    return None


def _key_work_like(item: Any) -> tuple[datetime, datetime]:
    ed = _parse_date(getattr(item, "endDate", None))
    sd = _parse_date(getattr(item, "startDate", None))
    primary = ed or sd or _MIN_DT
    secondary = sd or _MIN_DT
    return (primary, secondary)


def _key_achievement(item: Any) -> tuple[datetime]:
    sd = _parse_date(getattr(item, "startDate", None))
    return (sd or _MIN_DT,)


def sort_resume_inplace(resume: Any) -> None:
    """
    Sorts lists inside CompleteResume in place, newest first.
    Sections: workExperience, projects, education, achievements.
    """
    if getattr(resume, "workExperience", None):
        resume.workExperience = sorted(resume.workExperience, key=_key_work_like, reverse=True)

    if getattr(resume, "projects", None):
        resume.projects = sorted(resume.projects, key=_key_work_like, reverse=True)

    if getattr(resume, "education", None):
        resume.education = sorted(resume.education, key=_key_work_like, reverse=True)

    if getattr(resume, "achievements", None):
        resume.achievements = sorted(resume.achievements, key=_key_achievement, reverse=True)
