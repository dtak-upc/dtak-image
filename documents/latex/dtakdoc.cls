% DTAK document class: printable A4, two-sided. One class for every document type; see AGENTS.md.
%
%   \documentclass{dtakdoc}              % article (default)
%   \documentclass[exam]{dtakdoc}        % exam (exam.cls: questions, points, \gradetable, solutions)
%   \documentclass[exam,answers]{dtakdoc}% exam with the solutions printed
%
% Options: article | exam, logodir=<dir/>; anything else (11pt, 12pt, answers, addpoints, draft, ...) goes to the
% base class. a4paper and twoside are always on.
%
% Header: page 1 = UPC mark left + DTAK logo right (same height: equal footing, UPC identity manual).
%         even (left) pages = UPC mark at the outer (left) edge; odd (right) pages = DTAK logo at the outer (right) edge.
%         A thin navy rule separates the header from the text.
% Footer: the page number at the outer edge.
% Fonts:  the body keeps LaTeX's default font (Latin Modern); only the title and \section are Montserrat Bold.
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{dtakdoc}[2026/11/16 DTAK document class]

\RequirePackage{kvoptions}
\SetupKeyvalOptions{family=dtak, prefix=dtak@}
\DeclareBoolOption{exam}
\DeclareComplementaryOption{article}{exam}
\DeclareStringOption[logos/]{logodir}
\def\dtak@classopts{a4paper,twoside}
\DeclareDefaultOption{\edef\dtak@classopts{\dtak@classopts,\CurrentOption}}
\ProcessKeyvalOptions*

\ifdtak@exam
  \expandafter\LoadClass\expandafter[\dtak@classopts]{exam}
\else
  \expandafter\LoadClass\expandafter[\dtak@classopts]{article}
\fi

\RequirePackage{iftex}
\RequirePackage{xcolor}
\RequirePackage{graphicx}
\RequirePackage{booktabs}
\RequirePackage[a4paper, twoside, inner=25mm, outer=25mm, top=38mm, bottom=28mm,
  headheight=13mm, headsep=9mm, footskip=12mm]{geometry}

% ---------------------------------------------------------------- colors (the same names as the slide templates)
\definecolor{dtakaccent}{HTML}{0076CF}  % UPC blue, Pantone 2195
\definecolor{dtaknavy}{HTML}{0A2A4F}    % titles, header rule
\definecolor{dtakmuted}{HTML}{6B7785}   % page numbers, author/date line
\definecolor{dtakline}{HTML}{DDE3EA}

% ---------------------------------------------------------------- fonts
% Body: LaTeX's default (Latin Modern). Title and \section: Montserrat Bold, from the TeX package `montserrat`.
\ifPDFTeX
  \RequirePackage[T1]{fontenc}
  \RequirePackage{lmodern}
  \def\dtak@titlefont{\fontencoding{T1}\fontfamily{Montserrat-LF}\fontseries{b}\fontshape{n}\selectfont}
  \pdfsuppresswarningpagegroup=1  % the logo PDFs carry page groups; harmless
\else
  \RequirePackage{fontspec}
  \newfontfamily\dtak@titlefont{Montserrat-Bold.otf}[Ligatures=TeX]
\fi

% ---------------------------------------------------------------- page styles
% Both marks are 10 mm tall (dtak_long's minimum print size; the UPC mark is then 45.7 mm wide, above its 30 mm
% minimum). The logo files have no padding, so the same height = equal footing.
\newcommand\dtak@upc{\includegraphics[height=10mm]{\dtak@logodir upc-barcelonatech.pdf}}
\newcommand\dtak@dtak{\includegraphics[height=10mm]{\dtak@logodir dtak.pdf}}
\newcommand\dtak@head[1]{\vbox{\hbox to\textwidth{#1}\vskip 2.5mm{\color{dtaknavy}\hrule height 0.4pt}}}
\newcommand\dtak@pagenum{{\small\color{dtakmuted}\thepage}}
\def\ps@dtak{%
  \def\@evenhead{\dtak@head{\dtak@upc\hfil}}%
  \def\@oddhead{\dtak@head{\hfil\dtak@dtak}}%
  \def\@evenfoot{\dtak@pagenum\hfil}%
  \def\@oddfoot{\hfil\dtak@pagenum}%
  \let\@mkboth\@gobbletwo}
\def\ps@dtakfirst{%
  \ps@dtak
  \def\@oddhead{\dtak@head{\dtak@upc\hfil\dtak@dtak}}%
  \let\@evenhead\@oddhead}
\let\ps@plain\ps@dtakfirst   % chapter-less classes use plain for title pages
\pagestyle{dtak}
\AtBeginDocument{\pagestyle{dtak}\thispagestyle{dtakfirst}}  % after exam.cls' own \pagestyle{headandfoot}

% ---------------------------------------------------------------- title
% \title{} (required), \subtitle{}, \course{} (above the title), \author{}, \date{} (default \today), \duration{}.
% All work in both types; empty fields are skipped. In exam mode \maketitle adds the name / ID lines.
\def\@subtitle{}\def\@course{}\def\@duration{}\def\@author{}
\newcommand\subtitle[1]{\def\@subtitle{#1}}
\newcommand\course[1]{\def\@course{#1}}
\newcommand\duration[1]{\def\@duration{#1}}
\newif\ifdtak@any
\def\dtak@field#1{%
  \setbox0\hbox{#1}\ifdim\wd0>\z@ \ifdtak@any\quad\textperiodcentered\quad\fi #1\dtak@anytrue\fi}
\renewcommand\maketitle{%
  \thispagestyle{dtakfirst}%
  \begingroup\raggedright\parindent\z@
  \ifx\@course\@empty\else{\normalsize\bfseries\color{dtakaccent}\@course\par}\vskip 2mm\fi
  {\dtak@titlefont\fontsize{22}{26}\selectfont\color{dtaknavy}\@title\par}%
  \ifx\@subtitle\@empty\else\vskip 2mm{\large\color{dtakaccent}\@subtitle\par}\fi
  \vskip 4mm
  {\color{dtakmuted}\dtak@anyfalse\dtak@field{\@author}\dtak@field{\@date}\dtak@field{\@duration}\par}%
  \ifdtak@exam
    \vskip 7mm
    \hbox to\linewidth{Name:\ \hrulefill\quad ID:\ \hbox to 40mm{\hrulefill}}%
  \fi
  \par\endgroup
  \vskip 8mm
  \global\let\maketitle\relax}

% ---------------------------------------------------------------- headings
% \section: Montserrat Bold, navy (like the slide titles). \subsection and below: the body font, bold, navy.
\renewcommand\section{\@startsection{section}{1}{\z@}{-3.5ex \@plus -1ex \@minus -.2ex}{2ex \@plus .2ex}%
  {\dtak@titlefont\Large\color{dtaknavy}}}
\renewcommand\subsection{\@startsection{subsection}{2}{\z@}{-3.25ex \@plus -1ex \@minus -.2ex}{1.5ex \@plus .2ex}%
  {\normalfont\large\bfseries\color{dtaknavy}}}
\renewcommand\subsubsection{\@startsection{subsubsection}{3}{\z@}{-3.25ex \@plus -1ex \@minus -.2ex}{1.5ex \@plus .2ex}%
  {\normalfont\normalsize\bfseries\color{dtaknavy}}}

% ---------------------------------------------------------------- content
% Tables with booktabs: top/bottom rules in navy, the header rule (\midrule) in the accent, like the slides.
\RequirePackage{colortbl}
\let\dtak@toprule\toprule \def\toprule{\arrayrulecolor{dtaknavy}\dtak@toprule}
\let\dtak@bottomrule\bottomrule \def\bottomrule{\arrayrulecolor{dtaknavy}\dtak@bottomrule}
\let\dtak@midrule\midrule \def\midrule{\arrayrulecolor{dtakaccent}\dtak@midrule}

% Exam: solutions on a light accent tint (only printed with the `answers` option).
\ifdtak@exam
  \shadedsolutions
  \colorlet{SolutionColor}{dtakaccent!6}
\fi

\RequirePackage{hyperref}
\hypersetup{colorlinks=true, linkcolor=., citecolor=., filecolor=dtakaccent, urlcolor=dtakaccent,
  pdfcreator={dtakdoc.cls}}
\AtBeginDocument{\hypersetup{pdftitle={\@title}}}
