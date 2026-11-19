# DTAK slides (PowerPoint and Google Slides)

The same template as `../revealjs/` and `../latex/` (canvas, colors, fonts, footer, slide types), as a PowerPoint theme. The look lives in the slide master, the layouts and the theme, so you only pick a layout and type.

- `dtak.potx`: PowerPoint template. Open it (or *File › New › Personal*) to start a deck.
- `dtak.pptx`: the same template with the example slides. Upload this one to Google Slides.

Both are generated: don't edit them by hand, edit `tools/make_pptx.py` and run, from `dtak-image/`:

```sh
.venv/bin/python -I slides/pptx/tools/make_pptx.py
```

## Layouts

*New slide* (PowerPoint) or *Slide › Apply layout* (Google Slides):

| Layout | reveal.js |
|---|---|
| Title | `<section class="title">` |
| Section (dark) | `<section class="section">` |
| Title and content | `<section>` with `h2`, `h2 small` and a list |
| Two columns | `.cols` with an `h3` per column |
| Title only | for an image, diagram or table |
| Blank, no footer | `class="nochrome"` |

The subtitle placeholders are optional: an empty placeholder doesn't show. The callout (`.box`), quote and code box are not layouts; copy them from the example slides.

## What works out of the box

- **Fonts:** headings are Montserrat Bold, text is Roboto (theme fonts *+Headings* / *+Body*). PowerPoint gets them embedded in the file (Montserrat Bold, Roboto, Roboto Mono), so nothing has to be installed; keep *Embed fonts in the file* on when saving. Google Slides has them natively.
- **Colors:** the palette is the DTAK theme (text, navy, UPC blue, soft blue, muted, edge navy), so new shapes, tables and charts come out in DTAK colors. Shapes default to UPC blue, tables to the DTAK style.
- **Footer:** the UPC mark, the rule, the DTAK logo and the slide number are on the master and can't be moved by accident. The logos are SVG with a PNG fallback (Google Slides uses the PNG).

## Google Slides

1. In Drive, *New › File upload* `dtak.pptx`, open it with Google Slides, then *File › Save as Google Slides*.
2. Delete the example slides and keep that file as the template: *File › Make a copy* for each new deck.
3. To restyle an existing Google Slides deck: *Slide › Change theme › Import theme* and pick that file.

## Rules

The same as for the other two templates: one idea per slide, at most about 6 bullets on 2 levels, no manual colors or fonts, nothing over the footer, and the DTAK logo only in the footer.
