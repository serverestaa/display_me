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
      \textbf{#1} & #2 \\
      \textit{\small#3} & \textit{\small #4} \\
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
            lines.append(rf"\resumeSubheading{{{header}}}{{{loc}}}{{{sub}}}{{{dates}}}")
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


def _adapter_complete(resume: Any) -> str:
    """
    Собирает тело документа из типизированного резюме (CompleteResume).
    """
    lines: List[str] = []
    # General header
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
    # Education
    if getattr(resume, 'education', None):
        lines.append(r"\section{Education}")
        lines.append(r"\resumeSubHeadingListStart")
        for e in resume.education:
            dates = safe(e.startDate)
            if getattr(e, 'endDate', None):
                dates += f" -- {safe(e.endDate)}"
            inst_link = safe(e.institution)
            if getattr(e, 'url', None):
                u = safe(e.url)
                inst_link = r"\href{" + u + "}{" + inst_link + "}"
            lines.append(rf"\resumeSubheading{{{inst_link}}}{{{safe(e.location)}}}{{{safe(e.degree)}}}{{{dates}}}")
            desc = getattr(e, 'description', '') or ''
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

    # Work Experience
    if getattr(resume, 'workExperience', None):
        lines.append(r"\section{Work Experience}")
        lines.append(r"\resumeSubHeadingListStart")
        for w in resume.workExperience:
            dates = safe(w.startDate)
            if getattr(w, 'endDate', None):
                dates += f" -- {safe(w.endDate)}"
            comp_link = safe(w.company)
            if getattr(w, 'url', None):
                u = safe(w.url)
                comp_link = r"\href{" + u + "}{" + comp_link + "}"
            lines.append(rf"\resumeSubheading{{{safe(w.title)}}}{{{comp_link}}}{{{safe(w.location)}}}{{{dates}}}")
            desc = getattr(w, 'description', '') or ''
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

    # Projects
    if getattr(resume, 'projects', None):
        lines.append(r"\section{Projects}")
        lines.append(r"\resumeSubHeadingListStart")
        for p in resume.projects:
            dates = safe(p.startDate)
            if getattr(p, 'endDate', None):
                dates += f" -- {safe(p.endDate)}"
            # Projects heading on one line: title | stack on left, dates on right
            raw_title = safe(p.title)
            bold_title = r"\textbf{" + raw_title + "}"
            if getattr(p, 'url', None):
                u = safe(p.url)
                title_link = r"\href{" + u + "}{" + bold_title + "}"
            else:
                title_link = bold_title
            proj_text = title_link
            if getattr(p, 'stack', None):
                proj_text += " | " + safe(p.stack)
            lines.append(rf"\resumeProjectHeading{{{proj_text}}}{{{dates}}}")
            desc = getattr(p, 'description', '') or ''
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

    # Achievements
    if getattr(resume, 'achievements', None):
        lines.append(r"\section{Achievements}")
        lines.append(r"\resumeSubHeadingListStart")
        for a in resume.achievements:
            dates = safe(a.startDate)
            title_link = safe(a.title)
            if getattr(a, 'url', None):
                u = safe(a.url)
                title_link = r"\href{" + u + "}{" + title_link + "}"
            lines.append(rf"\resumeSubheading{{{title_link}}}{{}}{{}}{{{dates}}}")
            desc = getattr(a, 'description', '') or ''
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

    # Skills
    if getattr(resume, 'skills', None):
        lines.append(r"\section{Skills}")
        lines.append(r"\resumeItemListStart")
        for s in resume.skills:
            parts = []
            if getattr(s, 'category', None):
                parts.append(safe(s.category))
            if getattr(s, 'stack', None):
                parts.append(safe(s.stack))
            line = ", ".join(parts)
            if line:
                lines.append(rf"  \resumeItem{{{line}}}")
        lines.append(r"\resumeItemListEnd")

    return "\n".join(lines)


def generate_latex(user: Any, sections: List[Any]) -> str:
    """
    Генерирует LaTeX из свободных sections/blocks.
    """
    return common_header() + "\n" + _adapter_sections(user, sections) + "\n" + common_footer()


def generate_latex_from_complete_resume(resume: Any) -> str:
    """
    Генерирует LaTeX из типизированного резюме CompleteResume.
    """
    return common_header() + "\n" + _adapter_complete(resume) + "\n" + common_footer()



