# DTAK slides (reveal.js template)

A reveal.js template for DTAK presentations. The look is fixed: write content, not styles.

## Commands
- `npm install`: run once.
- `npm start`: live-reload server at http://localhost:8000/ (reloads on `index.html` and `theme/`).
- `npm run pdf` (or `npm run pdf -- out.pdf`): exports `index.html` to `pdf/slides.pdf`, one 1280×720 page per slide. Needs Chrome/Chromium (`CHROME_PATH` if it is not on PATH).

## Files
- `index.html`: the deck. Replace its `<section>`s with your slides.
- `theme/dtak.css`: all styling. `theme/deck.js`: chrome and `Reveal.initialize`. Do not restyle per slide.
- `theme/logos/`: the marks used in the footer. Do not edit, recolor or replace them.
  - `upc-barcelonatech.svg` / `upc-barcelonatech-neg.svg`: the UPC mark, for light / dark slides.
  - `dtak.svg` / `dtak-neg.svg`: the DTAK logo, for light / dark slides.
- `img/`: create it for your own images.

## Identity (fixed)
- **Canvas:** 16:9, 1280×720.
- **Accent: UPC blue `#0076CF`** (`--accent`), used for subtitles, bullets, links, inline code, callout boxes and the top bar. Dark slides use soft blue `#66ADE2` (`--soft`) instead, because UPC blue is too dark on navy.
- **Fonts:** **Montserrat Bold for titles** (`h1`, `h2`). **Roboto for everything else**: subtitles (`h2 small`, `.subtitle`), `h3`/`h4`, body, tables. Do not add other fonts.
- **Colors:** titles navy `#0A2A4F`, body `#1C2430`, muted `#6B7785`. Use only these, the accent and soft blue. Do not invent new colors.
- **Section slides:** navy background **`#0A2A4F`**, white title, soft-blue subtitle.
- **Chrome** (added to every slide by `deck.js`; do not add it by hand):
  - a 12 px accent bar at the top (light slides only);
  - a footer with the **UPC mark on the left**, a thin rule, and the **DTAK logo on the right**, both **46 px tall**. On dark slides both switch to their `-neg` files;
  - the slide number (`h` or `h.v`) at the bottom right.

  The two marks are on equal footing at the same height, as the UPC identity manual requires. Do not change one height without the other, and do not make the UPC mark narrower than 160 px.
- The bottom 110 px belong to the footer. Content must not overlap it.

## Slide types
```html
<section class="title">                     <!-- centred title slide -->
  <h1>Title</h1>
  <p class="subtitle">Subtitle</p>
  <p class="author">Name · Event · Date</p>
</section>

<section class="section">                   <!-- dark navy divider -->
  <h2>Section title<small>optional subtitle</small></h2>
</section>

<section>                                   <!-- normal content slide -->
  <h2>Slide title<small>optional subtitle</small></h2>
  <ul><li>…</li></ul>
</section>
```
- Vertical stacks are allowed (`<section><section>…</section>…</section>`). They are numbered `h.v`.
- `class="nochrome"` hides the bar and the footer (e.g. for a full-bleed image). Use it sparingly.
- Helpers: `.cols` (two columns; `style="--cols: 2fr 1fr"` sets the ratio), `.box` (accent callout), `.hl` (accent highlight), `.note` / `.small` (smaller text), `<blockquote>`, `<pre><code>`, `<table>`.
- Speaker notes: `<aside class="notes">…</aside>` (press `S`).

## Consistency rules
1. One idea per slide. Use one `h2` per content slide, with at most ~6 bullets and ~2 levels.
2. Use `h1` only on the title slide. Use `h2` for slide titles, `h2 small` for subtitles, and `h3` for column headings.
3. No inline colors or fonts. If something is missing, add a class to `theme/dtak.css`.
4. The DTAK logo appears only in the footer. Do not add it to slide content.
5. Check the PDF (`npm run pdf`) before sharing. Every slide must fit 1280×720 without overflowing into the footer.
