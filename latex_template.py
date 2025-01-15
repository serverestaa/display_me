def generate_latex(user, sections) -> str:
    """
    Генерирует LaTeX, подчиняясь формату Jake Gutierrez.
    Предполагаем, что поля user и sections уже есть.
    """
    latex_header = r"""\documentclass[letterpaper,11pt]{article}

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
\usepackage[english]{babel}
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
      % Печатаем heading
      \textbf{#1} & 
      % Если есть location, печатаем его справа
      \ifx&#2& 
        % Если location пусто, проверяем дату
        \ifx&#4& \\ % Если date тоже пусто, ничего не делаем
        \else \textit{\small #4} \\ % Если date есть, выводим его справа
        \fi
      \else
        #2 \\ % Если location есть, выводим его
      \fi
      % Печатаем subheading и дату
      \ifx&#3& % Если subheading пусто
        \ifx&#4& % Если date пусто
        \else \textit{\small #4} \\ % Если есть только date
        \fi
      \else
        \textit{\small #3} & 
        % Проверяем, есть ли date
        \ifx&#4& \\ % Если date пусто, ничего не выводим
        \else \textit{\small #4} \\ % Если date есть, выводим
        \fi
      \fi
    \end{tabular*}\vspace{-7pt}
}

\newcommand{\resumeSubSubheading}[2]{
    \item
    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
      \textit{\small#1} & \textit{\small #2} \\
    \end{tabular*}\vspace{-7pt}
}

\newcommand{\resumeProjectHeading}[2]{
    \item
    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
      \small#1 & #2 \\
    \end{tabular*}\vspace{-7pt}
}

\newcommand{\resumeSubItem}[1]{\resumeItem{#1}\vspace{-4pt}}

\renewcommand\labelitemii{$\vcenter{\hbox{\tiny$\bullet$}}$}

\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=0.15in, label={}]}
\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
\newcommand{\resumeItemListStart}{\begin{itemize}}
\newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-5pt}}

\begin{document}
"""

    # Пример: выводим шапку
    heading = (
        r"\begin{center}" + "\n"
        + rf"\textbf{{\Huge {escape(user.name)}}} \\ \vspace{{1pt}}" + "\n"
        + rf"\small {escape(user.email)} $|$ {escape(user.linkedin)} $|$ {escape(user.github)}" + "\n"
        + r"\end{center}" + "\n\n"
    )

    body = ""
    active_sections = [s for s in sections if s.is_active]
    sorted_sections = sorted(active_sections, key=lambda s: s.order)
    for section in sorted_sections:
        # Например, "Education"
        if not section.blocks:
            continue
        body += f"\\section{{{escape(section.title)}}}\n"
        body += "\\resumeSubHeadingListStart\n"

        active_blocks = [b for b in section.blocks if b.is_active]
        sorted_blocks = sorted(active_blocks, key=lambda b: b.order)

        # Для каждого блока внутри секции
        for block in sorted_blocks:
            # \resumeSubheading{header}{location}{subheader}{dates}
            # ВНИМАНИЕ: порядок аргументов см. в шаблоне!
            # #1=header, #2=location, #3=subheader, #4=dates
            header     = escape(block.header or "")
            location   = escape(block.location or "")
            subheader  = escape(block.subheader or "")
            dates      = escape(block.dates or "")

            if not location and not subheader:
                # Если нет location и subheader
                body += f"\\resumeSubheading{{{header}}}{{{dates}}}{{}}{{}}\n"
            elif not subheader:
                # Если нет subheader
                body += f"\\resumeSubheading{{{header}}}{{{location}}}{{}}{{{dates}}}\n"
            elif not location:
                # Если нет location
                body += f"\\resumeSubheading{{{header}}}{{{dates}}}{{{subheader}}}{{}}\n"
            else:
                # Все параметры присутствуют
                body += f"\\resumeSubheading{{{header}}}{{{location}}}{{{subheader}}}{{{dates}}}\n"

            # Если есть какое-то описание (bullets), добавляем \resumeItemListStart...\resumeItemListEnd
            # Допустим, вы храните все «буллеты» в block.description, разделяя «•» (или '\n')
            if block.description:
                bullets = [b.strip() for b in block.description.split("•") if b.strip()]
                body += "\\resumeItemListStart\n"
                for bul in bullets:
                    body += f"  \\resumeItem{{{escape(bul)}}}\n"
                body += "\\resumeItemListEnd\n"

        body += "\\resumeSubHeadingListEnd\n\n"

    latex_footer = r"\end{document}"

    return latex_header + heading + body + latex_footer


def escape(s: str) -> str:
    """
    Элементарное экранирование спецсимволов LaTeX
    (%, _, $, &, {, }, ~, ^, \ и т.п.)
    чтобы пользовательский ввод не ломал компиляцию.
    """
    replacements = {
        '\\': r'\\textbackslash{}',
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