# DTAK slides (Beamer template)

A Beamer theme for DTAK presentations, the LaTeX twin of `../revealjs/`: same canvas, colors, fonts, footer and slide types. The look is fixed, so you only write content. Everything else is plain Beamer: overlays, `columns`, `block`, math, `\note`, bibliographies and any package you need all work as usual.

## Commands
- `latexmk`: builds `main.tex` with LuaLaTeX, writing the PDF to `pdf/main.pdf` and auxiliary files to `build/` (see `latexmkrc`). `latexmk -pvc` rebuilds on every save.
- pdfLaTeX and XeLaTeX work too (`latexmk -pdf`, `latexmk -xelatex`) and give the same result.
- Requirements: a standard TeX Live, MiKTeX or Overleaf install. The fonts come from the TeX packages `roboto` and `montserrat`, so nothing needs to be installed in the system.

## Files
- `main.tex`: the example deck. Copy it and replace its frames.
- `beamerthemedtak.sty`: all the styling. Do not restyle per frame.
- `logos/`: the marks used in the footer. Do not edit, recolor or replace them.
  - `upc-barcelonatech.pdf` / `upc-barcelonatech-neg.pdf`: the UPC mark for light / dark frames, converted 1:1 (cairosvg) from `../revealjs/theme/logos/*.svg`.
  - `dtak.pdf` / `dtak-neg.pdf`: **symlinks** to `../../../logo/pdf/dtak_short{,_dark}.pdf`, which `tools/make_logo.py` generates. Regenerating the logo therefore updates the slides.
- **Using the template outside this repo** (e.g. Overleaf, or another project): copy the folder with symlinks dereferenced, so the logos become real files: `cp -rL slides/latex my-talk`, or `zip -r` (zip follows symlinks by default). Keep `beamerthemedtak.sty` and `logos/` next to your `.tex`, or point to them with `\usetheme[logodir=path/to/logos/]{dtak}`.

## Identity (fixed)
These are the same as in `../revealjs/AGENTS.md`, scaled from 1280×720 px to Beamer's 160×90 mm (1 px = 0.125 mm).
- **Canvas:** 16:9 (`\documentclass[aspectratio=169]{beamer}`; the theme warns if you leave it out), with the default 11 pt body text (30 px).
- **Colors:** accent UPC blue `dtakaccent` `#0076CF`; titles `dtaknavy` `#0A2A4F`; body `dtaktext` `#1C2430`; muted `dtakmuted` `#6B7785`; soft blue `dtaksoft` `#66ADE2`, which replaces the accent on dark frames. Use only these color names, and never raw hex values.
- **Fonts:** Montserrat Bold for the title and frame titles, Roboto for everything else (subtitles are Roboto Medium), Roboto Mono for code. Math keeps Beamer's default math font.
- **Chrome** (added to every frame by the theme; do not add it by hand):
  - a 1.5 mm accent bar at the top (light frames only);
  - a footer with the **UPC mark on the left**, a thin rule, and the **DTAK logo on the right**, both 5.75 mm tall, which switch to their `-neg` files on dark frames;
  - the frame number at the bottom right.

  The two marks are on equal footing at the same height, as the UPC identity manual requires. Do not change one height without the other.
- The bottom 13.75 mm belong to the footer. Content must not overlap it, and Beamer does not stop it from doing so, so check the PDF.

## Slide types
```latex
\title{Title} \subtitle{Subtitle}            % title frame: centred h1, subtitle in the accent,
\author{Name} \institute{Event} \date{2026}   % then "author · institute · date" (empty fields are skipped)
\maketitle

\section{Section title}                       % adds a dark navy section frame automatically

\begin{frame}{Slide title}{Optional subtitle} % normal content frame
  \begin{itemize} \item ... \end{itemize}
\end{frame}

\begin{frame}[dark]{Thank you}{name@upc.edu}  % any dark frame (navy, white title, soft-blue subtitle)
\end{frame}
```
- Frame options added by the theme: `[dark]` (= reveal's `.section`) and `[nochrome]` (no bar or footer logos, number kept; e.g. a full-bleed image). Combine them with Beamer's own options as usual, e.g. `[dark,fragile]`. Use `[nochrome]` sparingly.
- To turn off the automatic section frames, use `\usetheme[nosectionframes]{dtak}`.
- Content is top-aligned (`[c]` centres a single frame).
- Equivalents of the reveal helpers:

  | reveal.js | Beamer |
  |---|---|
  | `.hl` | `\alert{...}` (bold accent) |
  | `.box` | `\begin{block}{}...\end{block}` (with a title: `\begin{block}{Title}`; `alertblock` and `exampleblock` look the same) |
  | `.cols` | `\begin{columns}[T,onlytextwidth]` + two `\begin{column}{0.48\textwidth}` |
  | `h3` | `\heading{...}` |
  | `<blockquote>` | `quote` / `quotation` |
  | `<pre><code>` | `lstlisting` (frame needs `[fragile]`) |
  | inline `<code>` | `\code{...}` |
  | `<table>` | `tabular` with booktabs (`\toprule`, `\midrule`, `\bottomrule`); `\midrule` is drawn in the accent |
  | `.note` | `\muted{...}`, or `\small` / `\footnotesize` |
  | speaker notes | `\note{...}` |

## Consistency rules
1. One idea per frame. Use one frame title per frame, with at most ~6 bullets and ~2 levels.
2. `\maketitle` only once, for the title frame. Use `\framesubtitle` (or the second `{}` argument of the frame) for subtitles and `\heading` for column headings.
3. No inline colors or fonts (`\color{red}`, `\textcolor`, `\fontfamily`, …). If something is missing, add it to `beamerthemedtak.sty`, using the colors above.
4. The DTAK logo appears only in the footer. Do not add it to the frame content.
5. Check the PDF before sharing. No frame may run into the footer.
