from typing import Any, List
import re
from bs4 import BeautifulSoup


def common_header() -> str:
    """
    Возвращает общий преамбул LaTeX с макросами и началом документа.
    """
    return r"""\documentclass[letterpaper,11pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T2A]{fontenc}
\usepackage{lmodern}
\usepackage{latexsym}
\usepackage{ifthen}
\usepackage[empty]{fullpage}
\usepackage{titlesec}
\usepackage{marvosym}
\usepackage[usenames,dvipsnames]{color}
\usepackage{verbatim}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage{fancyhdr}
\usepackage[english,russian]{babel}
\usepackage{tabularx}
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

\newcommand{\resumeSubheading}[4]{
  \vspace{-2pt}\item
    \begin{tabular*}{0.97\textwidth}[t]{l@{\extracolsep{\fill}}r}
      \textbf{#1} &
      \ifx&#2&
        \ifx&#4& \\
        \else \textit{\small #4} \\
        \fi
      \else
        #2 \\
      \fi
      \ifx&#3&
        \ifx&#4&
        \else \textit{\small #4} \\
        \fi
      \else
        \textit{\small #3} &
        \ifx&#4& \\
        \else \textit{\small #4} \\
        \fi
      \fi
    \end{tabular*}\vspace{-7pt}
}

\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=0.15in, label={}]}
\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
\newcommand{\resumeItemListStart}{\begin{itemize}}
\newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-5pt}}

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
    for old, new in replacements.items():
        s = s.replace(old, new)
    return s


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
    lines = []
    for el in soup.contents:
        if getattr(el, "name", None) == "p":
            text = el.get_text(strip=True)
            if text:
                lines.append(text)
        elif getattr(el, "name", None) in ("ul", "ol"):
            env = "itemize" if el.name == "ul" else "enumerate"
            lines.append(r"\begin{" + env + "}")
            for li in el.find_all("li", recursive=False):
                inner = li.get_text(strip=True)
                if inner:
                    lines.append(r"\item " + escape(inner))
            lines.append(r"\end{" + env + "}")
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

    # Work Experience
    if getattr(resume, 'workExperience', None):
        lines.append(r"\section{Work Experience}")
        lines.append(r"\resumeSubHeadingListStart")
        for w in resume.workExperience:
            dates = safe(w.startDate)
            if getattr(w, 'endDate', None):
                dates += f" -- {safe(w.endDate)}"
            lines.append(rf"\resumeSubheading{{{safe(w.title)}}}{{{safe(w.company)}}}{{{safe(w.location)}}}{{{dates}}}")
            desc = getattr(w, 'description', '') or ''
            items = [it.strip() for it in re.split(r'[\r\n]+|•', desc) if it.strip()]
            if items:
                lines.append(r"\resumeItemListStart")
                for it in items:
                    lines.append(rf"  \resumeItem{{{escape(it)}}}")
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
            lines.append(rf"\resumeSubheading{{{safe(p.title)}}}{{{safe(p.stack)}}}{{{safe(p.url)}}}{{{dates}}}")
            desc = getattr(p, 'description', '') or ''
            items = [it.strip() for it in re.split(r'[\r\n]+|•', desc) if it.strip()]
            if items:
                lines.append(r"\resumeItemListStart")
                for it in items:
                    lines.append(rf"  \resumeItem{{{escape(it)}}}")
                lines.append(r"\resumeItemListEnd")
        lines.append(r"\resumeSubHeadingListEnd")

    # Education
    if getattr(resume, 'education', None):
        lines.append(r"\section{Education}")
        lines.append(r"\resumeSubHeadingListStart")
        for e in resume.education:
            dates = safe(e.startDate)
            if getattr(e, 'endDate', None):
                dates += f" -- {safe(e.endDate)}"
            lines.append(rf"\resumeSubheading{{{safe(e.institution)}}}{{{safe(e.location)}}}{{{safe(e.degree)}}}{{{dates}}}")
            desc = getattr(e, 'description', '') or ''
            items = [it.strip() for it in re.split(r'[\r\n]+|•', desc) if it.strip()]
            if items:
                lines.append(r"\resumeItemListStart")
                for it in items:
                    lines.append(rf"  \resumeItem{{{escape(it)}}}")
                lines.append(r"\resumeItemListEnd")
        lines.append(r"\resumeSubHeadingListEnd")

    # Achievements
    if getattr(resume, 'achievements', None):
        lines.append(r"\section{Achievements}")
        lines.append(r"\resumeSubHeadingListStart")
        for a in resume.achievements:
            dates = safe(a.startDate)
            lines.append(rf"\resumeSubheading{{{safe(a.title)}}}{{{safe(a.url)}}}{{}}{{{dates}}}")
            desc = getattr(a, 'description', '') or ''
            items = [it.strip() for it in re.split(r'[\r\n]+|•', desc) if it.strip()]
            if items:
                lines.append(r"\resumeItemListStart")
                for it in items:
                    lines.append(rf"  \resumeItem{{{escape(it)}}}")
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

    # Contacts
    if getattr(resume, 'contacts', None):
        lines.append(r"\section{Contacts}")
        lines.append(r"\resumeItemListStart")
        for c in resume.contacts:
            parts = []
            if getattr(c, 'media', None):
                parts.append(safe(c.media))
            if getattr(c, 'link', None):
                parts.append(safe(c.link))
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
