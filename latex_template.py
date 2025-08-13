from typing import Any, List
import re
from bs4 import BeautifulSoup, NavigableString, Tag


def common_header() -> str:
    """
    Возвращает общий преамбул LaTeX с макросами и началом документа.
    """
    return r"""\documentclass[letterpaper,11pt]{article}
\usepackage{latexsym}
\usepackage[empty]{fullpage}
\usepackage{titlesec}
\usepackage{marvosym}
\usepackage[usenames,dvipsnames]{color}
\usepackage{verbatim}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage{fancyhdr}
\usepackage{tabularx}
\usepackage[T2A]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[russian,english]{babel}
\input{glyphtounicode}

\pagestyle{fancy}
\fancyhf{} % clear all header and footer fields
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

% Adjust margins
\addtolength{\oddsidemargin}{-0.5in}
\addtolength{\evensidemargin}{-0.5in}
\addtolength{\textwidth}{1in}
\addtolength{\topmargin}{-.5in}
\addtolength{\textheight}{1.0in}

\urlstyle{same}

\raggedbottom   
\raggedright
\setlength{\tabcolsep}{0in}

% Sections formatting
\titleformat{\section}{
  \vspace{-4pt}\scshape\raggedright\large
}{}{0em}{}[\color{black}\titlerule \vspace{-5pt}]

\pdfgentounicode=1

%-------------------------
% Custom commands
\newcommand{\resumeItem}[1]{
  \item\small{
    {#1 \vspace{-2pt}}
  }
}

\newcommand{\resumeSubheading}[4]{%
  \vspace{-2pt}\item
    \begin{tabular*}{0.97\textwidth}[t]{l@{\extracolsep{\fill}}r}
      \textbf{#1} & \textit{\small #4} \\
      \textit{\small #2} & \textit{\small #3} \\
    \end{tabular*}\vspace{-7pt}
}

\renewcommand\labelitemii{$\vcenter{\hbox{\tiny$\bullet$}}$}
\newcommand{\resumeItemListStart}{\begin{itemize}[leftmargin=0.26in, itemsep=2pt,topsep=2pt,parsep=1pt]}
\newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-5pt}}
\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=0.15in, label={}]}
\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}

\newcommand{\resumeSubSubheading}[2]{%
    \item
    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
      \textit{\small#1} & \textit{\small #2} \\
    \end{tabular*}\vspace{-7pt}
}
\newcommand{\resumeProjectHeading}[2]{%
    \item
    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
      \small#1 & #2 \\
    \end{tabular*}\vspace{-7pt}
}
\newcommand{\resumeSubItem}[1]{\resumeItem{#1}\vspace{-4pt}}

\begin{document}
"""


def common_footer() -> str:
    """
    Возвращает окончание документа.
    """
    return r"\end{document}"


def escape(s: str) -> str:
    """
    Элементарное экранирование спецсимволов LaTeX.
    """
    replacements = {
        '\\': r'\textbackslash{}',
        '%': r'\%',
        '$': r'\$',
        '&': r'\&',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\^{}',
    }
    # Build result character by character to avoid re-escaping inserted sequences
    return ''.join(replacements.get(ch, ch) for ch in s)


def safe(val: Any) -> str:
    """
    Безопасно экранирует строковое значение или возвращает пустую строку.
    """
    return escape(str(val)) if val else ""


def html_to_latex(html: str) -> str:
    """
    Convert simple HTML (paragraphs and lists) into LaTeX code.
    """
    soup = BeautifulSoup(html or "", "html.parser")

    def process(node):
        if isinstance(node, NavigableString):
            return escape(str(node))
        if isinstance(node, Tag):
            if node.name in ("strong", "b"):
                inner = "".join(process(c) for c in node.contents)
                return r"\textbf{" + inner + "}"
            if node.name in ("em", "i"):
                inner = "".join(process(c) for c in node.contents)
                return r"\textit{" + inner + "}"
            if node.name == "u":
                inner = "".join(process(c) for c in node.contents)
                return r"\underline{" + inner + "}"
            # Fallback for other tags: process children
            return "".join(process(c) for c in node.contents)
        return ""

    lines = []
    for el in soup.contents:
        if getattr(el, "name", None) == "p":
            tex = process(el)
            if tex.strip():
                lines.append(tex)
        elif getattr(el, "name", None) in ("ul", "ol"):
            for li in el.find_all("li", recursive=False):
                tex = process(li)
                if tex.strip():
                    lines.append(tex)

    return "\n".join(lines)


def _adapter_sections(user: Any, sections: List[Any]) -> str:
    """
    Собирает тело документа из свободных sections/blocks-моделей.
    """
    lines: List[str] = []
    # Заголовок пользователя
    lines.append(r"\begin{center}")
    lines.append(rf"\textbf{{\Huge {escape(user.name)}}} \\\vspace{{1pt}}")
    contacts = [escape(getattr(user, attr)) for attr in ('email', 'phone') if getattr(user, attr, None)]
    if contacts:
        lines.append(rf"\small {' $|$ '.join(contacts)}")
    lines.append(r"\end{center}")

    # Секции и блоки
    active = [s for s in sections if getattr(s, 'is_active', True)]
    sorted_sec = sorted(active, key=lambda s: getattr(s, 'order', 0))
    for sec in sorted_sec:
        blocks = [b for b in getattr(sec, 'blocks', []) if getattr(b, 'is_active', True)]
        if not blocks:
            continue
        lines.append(rf"\section{{{escape(sec.title)}}}")
        lines.append(r"\resumeSubHeadingListStart")
        for b in sorted(blocks, key=lambda b: getattr(b, 'order', 0)):
            header = escape(b.header or "")
            loc = escape(b.location or "")
            sub = escape(b.subheader or "")
            dates = escape(b.dates or "")
            lines.append(rf"\resumeSubheading{{{header}}}{{{sub}}}{{{loc}}}{{{dates}}}")
            desc = getattr(b, 'description', '') or ''
            latex_body = html_to_latex(desc)
            if not latex_body and desc:                  # plain text fallback
                latex_body = "\n".join(
                    escape(line.lstrip("•- ").strip())
                    for line in desc.splitlines()
                    if line.strip()
                )
            if latex_body:
                lines.append(r"\resumeItemListStart")
                for line in latex_body.split("\n"):
                    lines.append(rf"  \resumeItem{{{line}}}")
                lines.append(r"\resumeItemListEnd")
        lines.append(r"\resumeSubHeadingListEnd")

    return "\n".join(lines)


def _adapter_complete(resume: Any, sections_order: list[str] | None = None) -> str:
    """
    Build body honoring custom sections order.
    Allowed keys: workExperience, education, projects, achievements, skills.
    Header (general) is always first.
    """
    lines: List[str] = []

    def _is_on(x) -> bool:
        # treat missing as enabled
        return not getattr(x, "is_disabled", False)

    # ------- Header (unchanged) -------
    gen = resume.general
    if gen:
        lines.append(r"\begin{center}")
        lines.append(rf"\textbf{{\Huge {safe(gen.fullName)}}} \\")
        parts = []
        for attr in ('email', 'phone', 'website', 'location'):
            val = getattr(gen, attr, None)
            if val:
                parts.append(safe(val))
        if parts:
            lines.append(rf"\small {' $|$ '.join(parts)}")
        extra = []
        for attr in ('github', 'linkedin'):
            val = getattr(gen, attr, None)
            if val:
                extra.append(safe(val))
        if extra:
            lines.append(rf"\small {' $|$ '.join(extra)}")
        if gen.occupation:
            lines.append(rf"\textit{{{safe(gen.occupation)}}}")
        lines.append(r"\end{center}")

    def render_summary():
        if not gen:
            return
        # Default to True when field missing (backward compatible)
        include = getattr(gen, "include_summary", True)
        about = getattr(gen, "about", None)
        if include and (about and about.strip()):
            lines.append(r"\section{Summary}")
            # Convert tiny HTML or plain text to LaTeX
            body = html_to_latex(about)
            if not body and about:
                body = "\n".join(escape(line.strip()) for line in about.splitlines() if line.strip())
            # Paragraph-style summary (no bullets)
            if body:
                # Keep it compact
                lines.append(r"\small " + body + r"\normalsize")

    render_summary()

    # ------- helpers that render a particular section -------
    def render_education():
        items = [e for e in (getattr(resume, 'education', []) or []) if _is_on(e)]
        if not items:
            return
        if not getattr(resume, 'education', None):
            return
        lines.append(r"\section{Education}")
        lines.append(r"\resumeSubHeadingListStart")
        for e in items:
            dates = safe(e.startDate)
            if getattr(e, 'endDate', None):
                dates += f" -- {safe(e.endDate)}"
            inst_link = safe(e.institution)
            if getattr(e, 'url', None):
                u = safe(e.url)
                inst_link = r"\href{" + u + "}{" + inst_link + "}"
            lines.append(rf"\resumeSubheading{{{safe(e.degree)}}}{{{inst_link}}}{{{safe(e.location)}}}{{{dates}}}")
            _render_desc(getattr(e, 'description', ''))
        lines.append(r"\resumeSubHeadingListEnd")

    def render_work():
        items = [w for w in (getattr(resume, 'workExperience', []) or []) if _is_on(w)]
        if not items:
            return
        if not getattr(resume, 'workExperience', None):
            return
        lines.append(r"\section{Work Experience}")
        lines.append(r"\resumeSubHeadingListStart")
        for w in items:
            dates = safe(w.startDate)
            if getattr(w, 'endDate', None):
                dates += f" -- {safe(w.endDate)}"
            comp_link = safe(w.company)
            if getattr(w, 'url', None):
                u = safe(w.url)
                comp_link = r"\href{" + u + "}{" + comp_link + "}"
            lines.append(rf"\resumeSubheading{{{safe(w.title)}}}{{{comp_link}}}{{{safe(w.location)}}}{{{dates}}}")
            _render_desc(getattr(w, 'description', ''))
        lines.append(r"\resumeSubHeadingListEnd")

    def render_projects():
        items = [p for p in (getattr(resume, 'projects', []) or []) if _is_on(p)]
        if not items:
            return

        if not getattr(resume, 'projects', None):
            return
        lines.append(r"\section{Projects}")
        lines.append(r"\resumeSubHeadingListStart")
        for p in items:

            dates = safe(p.startDate)
            if getattr(p, 'endDate', None):
                dates += f" -- {safe(p.endDate)}"
            raw_title = safe(p.title)
            bold_title = r"\textbf{" + raw_title + "}"
            title_link = r"\href{" + safe(p.url) + "}{" + bold_title + "}" if getattr(p, 'url', None) else bold_title
            proj_text = title_link + ((" | " + safe(p.stack)) if getattr(p, 'stack', None) else "")
            lines.append(rf"\resumeProjectHeading{{{proj_text}}}{{{dates}}}")
            _render_desc(getattr(p, 'description', ''))
        lines.append(r"\resumeSubHeadingListEnd")

    def render_achievements():
        items = [a for a in (getattr(resume, 'achievements', []) or []) if _is_on(a)]
        if not items:
            return
        if not getattr(resume, 'achievements', None):
            return
        lines.append(r"\section{Achievements}")
        lines.append(r"\resumeSubHeadingListStart")
        for a in items:

            dates = safe(a.startDate)
            title_link = r"\href{" + safe(a.url) + "}{" + safe(a.title) + "}" if getattr(a, 'url', None) else safe(a.title)
            lines.append(rf"\resumeSubheading{{{title_link}}}{{}}{{}}{{{dates}}}")
            _render_desc(getattr(a, 'description', ''))
        lines.append(r"\resumeSubHeadingListEnd")

    def render_skills():
        items = [s for s in (getattr(resume, 'skills', []) or []) if _is_on(s)]
        if not items:
            return
        if not getattr(resume, 'skills', None):
            return
        lines.append(r"\section{Skills}")
        lines.append(r"\resumeItemListStart")
        for s in items:

            parts = []
            if getattr(s, 'category', None): parts.append(safe(s.category))
            if getattr(s, 'stack', None): parts.append(safe(s.stack))
            if parts:
                lines.append(rf"  \resumeItem{{{', '.join(parts)}}}")
        lines.append(r"\resumeItemListEnd")

    def _render_desc(desc: str):
        desc = desc or ''
        latex_body = html_to_latex(desc)
        if not latex_body and desc:
            latex_body = "\n".join(escape(line.lstrip("•- ").strip()) for line in desc.splitlines() if line.strip())
        if latex_body:
            lines.append(r"\resumeItemListStart")
            for line in latex_body.split("\n"):
                lines.append(rf"  \resumeItem{{{line}}}")
            lines.append(r"\resumeItemListEnd")

    # default order if none provided
    order = sections_order or ["education", "workExperience", "projects", "achievements", "skills"]

    render_map = {
        "education": render_education,
        "workExperience": render_work,
        "projects": render_projects,
        "achievements": render_achievements,
        "skills": render_skills,
    }

    for key in order:
        fn = render_map.get(key)
        if fn:
            fn()

    return "\n".join(lines)


def generate_latex(user: Any, sections: List[Any]) -> str:
    """
    Генерирует LaTeX из свободных sections/blocks.
    """
    return common_header() + "\n" + _adapter_sections(user, sections) + "\n" + common_footer()


def generate_latex_from_complete_resume(resume: Any, sections_order: list[str] | None = None) -> str:
    return common_header() + "\n" + _adapter_complete(resume, sections_order) + "\n" + common_footer()



