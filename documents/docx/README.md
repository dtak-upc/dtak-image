# DTAK documents (Word and Google Docs)

The same printable A4 article as `../latex/` (`dtakdoc.cls`): page, header, footer, fonts and colors. The look is defined in the styles, theme, numbering and the header/footer parts, so you pick a style and type.

- `dtak.dotx`: Word template. Open it, or put it in your templates folder and use *File › New › Personal*, to start a document.
- `dtak.docx`: the same template with the example article (`../latex/article.tex`). Upload this one to Google Docs.

Both files are generated. Don't edit them by hand: edit `tools/make_docx.py` and run it from `dtak-image/`:

```sh
.venv/bin/python -I documents/docx/tools/make_docx.py
```

The output is byte-identical on every run.

## Styles

| Style | LaTeX | Look |
|---|---|---|
| Title | `\title` | Montserrat Bold 22 pt, navy |
| Subtitle | `\subtitle` | Georgia 13 pt, UPC blue |
| Author line | `\author · \date` | Georgia, muted |
| Abstract heading / Abstract | `abstract` | small, indented |
| Heading 1 | `\section` | Montserrat Bold, navy, numbered 1, 2, … |
| Heading 2, Heading 3 | `\subsection`, `\subsubsection` | Georgia bold, navy, numbered 1.1, 1.1.1 |
| Normal | body | Georgia 11 pt, justified, hyphenated |
| Caption | `\caption` | centred, above the table (*References › Insert Caption*) |
| Equation | `equation` | centre tab for the equation, right tab for the number |
| DTAK Table (default table style) | booktabs | navy top/bottom rules, a UPC-blue rule under the header row |

## Identity (fixed)

- **Page:** A4, mirrored margins (inner = outer = 25 mm), the text starts 38 mm from the top. Print two-sided, flipping on the long edge.
- **Header:** page 1 has the UPC mark on the left and the DTAK logo on the right, both 10 mm tall (equal footing). Even pages have the UPC mark on the left, odd pages the DTAK logo on the right. A thin navy rule runs under the header. The logos are SVG with a PNG fallback. Do not resize or replace them.
- **Footer:** the page number at the outer edge.
- **Fonts:** Montserrat Bold for the title and Heading 1, and Georgia for everything else. Montserrat Bold is embedded in the file (keep *File › Options › Save › Embed fonts in the file* on). Georgia ships with Windows, macOS, Office and Google Docs. On Linux, LibreOffice needs `ttf-mscorefonts-installer`, or it substitutes another serif.
- **Colors:** theme colors only, *Text 2* = navy `#0A2A4F`, *Accent 1* = UPC blue `#0076CF`, *Accent 3* = muted `#6B7785`.

## Google Docs

1. In Drive, *New › File upload* `dtak.docx`, open it with Google Docs, then *File › Save as Google Docs*.
2. Delete the example text, keeping the title block, and keep that file as the template: *File › Make a copy* for each new document. In Google Workspace it can also go in the organisation's template gallery.
3. What changes in the conversion:
   - the logos use the PNG fallback;
   - *Title*, *Subtitle* and *Heading 1–3* stay styles, while the custom styles (author line, abstract, caption, equation) become direct formatting, so copy those paragraphs from the example;
   - the table style becomes direct formatting on the example table, so copy that table instead of inserting a new one;
   - the caption and cross-reference fields keep their text but no longer update;
   - check *Format › Headers & footers*: *Different first page* and *Different odd & even* should both be ticked.

## Rules

The same as for `../latex/`: no manual colors or fonts (use the styles), the logos only in the header, one title block at the start, and check the odd/even headers before printing.
