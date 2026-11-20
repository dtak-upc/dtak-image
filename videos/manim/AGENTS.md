# DTAK videos (manim template)

A template for educational videos made with [Manim Community](https://docs.manim.community/) and
[manim-voiceover](https://voiceover.manim.community/) in the DTAK identity. It is the video twin of
`../../slides/`: the same canvas, colors, fonts, footer and section dividers. It adds a workflow
in which **what is shown** and **what is said** are written together, beat by beat, in YAML, and
the video is timed by its narration.

It was extracted from the DTAK video "How does a JOIN work? A journey inside PostgreSQL"
(8 sections, 36 beats, ~20 min). `episodes/00-lorem-ipsum/` is a short demo of every piece, with the same opening and ending as
that video.

## ⚠️ Render low-resolution previews only

Rendering is **slow**. `dtak render` defaults to **480p15 (`-q l`)**, which already takes
roughly as long as the video lasts (~20 min for a 20-minute episode). 1080p60 (`-q h`) draws
about 20× more pixels per second of video: expect hours.
- While working, use `dtak check` (no video at all) and `dtak render NN --only <section>`.
- Render `-q m` (720p30) or `-q h` (1080p60) **once**, for the final version, and only when
  the author asks for it. Never render high resolution to "check" something: a 480p frame
  shows the same layout.
- Agents: never start a high-resolution render on your own.

## Commands

Requirements: [uv](https://docs.astral.sh/uv/), a LaTeX distribution (for `MathTex`), `ffmpeg`
and `sox`. Run everything from this folder.

```sh
uv sync --group dev                 # once
uv run dtak list                    # episodes
uv run dtak new 01-my-topic         # new episode, copied from 00-lorem-ipsum (adds it to the workspace)
uv sync                             # after `dtak new`
uv run dtak docs 01                 # STORYBOARD.md + SCRIPT.md from beats/*.yaml
uv run dtak check 01                # every beat implemented, layout checks, beat timing (fast, no video)
uv run --group dev pytest           # YAML ↔ code ↔ references ↔ generated docs
uv run dtak render 01               # 480p preview → media/01-my-topic/01-my-topic_480p15.mp4 (+ .srt)
uv run dtak render 01 --only 2      # one section
uv run dtak sheet media/01-my-topic/01-my-topic_480p15.mp4   # contact sheet (PNG) to review frames
uv run manim -pql episodes/01-my-topic/src/mytopic/scenes/s01_lorem.py LoremIpsum   # one scene, plain manim
```

`dtak render --voice gtts` uses Google TTS (needs `uv sync --extra gtts`, internet, and sends the
narration to Google); `--voice recorder` records your own voice beat by beat. The default voice is
a **silent draft**: no speech, but each beat lasts as long as its narration read at 140 words/min.

**Using the template outside this repo:** the fonts and logos in
`packages/dtak-manim/src/dtak_manim/assets/` are **symlinks** to `../../fonts`, `../../logo` and
the reveal.js UPC marks, so the identity has a single source of truth. Copy the folder with
symlinks dereferenced: `cp -rL videos/manim my-video` (or `zip -r`), then delete
`my-video/media` and `my-video/.venv` if present.

## Files

```
pyproject.toml              uv workspace: the library + one member per episode
packages/dtak-manim/        the shared library (do not fork it per episode: improve it here)
  src/dtak_manim/
    theme.py                colors, fonts, sizes, layout zones: the ONLY place with hex values
    chrome.py               DtakScene: bar, footer, titles, section cards, beats, voiceover,
                            elastic timing, layout checks
    episode.py              Episode / Section / Beat loaded from YAML; the @beat decorator
    voice.py                speech services: silent draft (default), gtts, recorder
    text.py                 title/body/mono text, markup, bullets, callouts, tags, CodeBlock
    table.py                DbTable (addressable rows, columns, cells), outline, row_labels
    diagram.py              box, labeled_box, link (arrow), PlanNode + edge (trees, pipelines)
    db.py                   optional domain components (heap pages, B-trees, hash tables):
                            examples of components built on diagram.py
    transcript.py           parser for captured tool output ("### tag" blocks, psql tables)
    docs.py cli.py          the STORYBOARD/SCRIPT generator and the `dtak` command
    assets/                 symlinked DTAK + UPC marks and OFL fonts
episodes/NN-name/           one episode = one video (a uv workspace member)
  episode.yaml              slug, title slide (title, subtitle, author, institute, date),
                            words per minute, scene order
  beats/NN_section.yaml     THE SOURCE: per beat, visual + narration + refs
  src/<package>/__init__.py loads EPISODE and defines EpisodeScene(DtakScene)
  src/<package>/data.py     every number/row shown on screen, and FACTS for the narration
  src/<package>/scenes/     one module per section, one class per section, one method per beat
  REFERENCES.md             numbered sources; beats cite them in `refs:`
  STORYBOARD.md SCRIPT.md   GENERATED by `dtak docs` (do not edit)
  (optional) capture.sh     runs the real tool and saves its output for data.py to parse
tests/test_episodes.py      generic consistency tests, run for every episode
media/                      renders, voice cache, timing.json (git-ignored)
```

## How it works

0. **Every video has the same frame** (the one of the JOIN video; `dtak new` copies it):
   - section 0 `Intro` (`card: false`): **0.1** `title_slide()`, **0.2** the question the video
     answers (a running example going into a "?" box, then 3–4 questions, one per part of the
     video: the only topic-specific beat), **0.3** `road_map(groups)` (built from the YAML);
   - content sections 1…N, each opening with a navy section card;
   - a last `Wrap-up` section: `takeaways(items)` and `closing_card()`.
1. **Beats are the unit.** A beat is one idea: 10–60 s of narration with the visuals that go
   with it. Each beat has an ID `section.n` (`3.2`) shared by the YAML, the generated docs, the
   scene method (`@beat("3.2")`) and the clip name of `dtak render --sections`.
2. **The YAML is the single source of truth.** `beats/NN_*.yaml` holds, per beat, `title`,
   `visual` (what is on screen, for whoever implements or reviews it), `narration` (what is said,
   Markdown allowed: `**bold**` and `` `code` `` are stripped before speech) and `refs`. The section
   file also holds the section-card `title` / `subtitle` and `card: false` for intros.
   `STORYBOARD.md` and `SCRIPT.md` are generated from it; a test fails if they are stale.
3. **Scenes implement beats.** One scene class per section, with `SECTION = n`, inheriting the
   episode's `EpisodeScene`. Each beat is a method decorated with `@beat("n.m")`. Do not write
   `construct()`: the default one shows the section card and runs the beats in YAML order, and it
   fails if the code and the YAML disagree.
4. **Narration drives timing (elastic beats).** Each beat runs inside a voiceover of its
   narration, so it lasts at least as long as the voice. `dtak check` measures each beat's
   animation time and pauses (`media/<ep>/timing.json`); on render, a beat whose narration is
   longer stretches its own `self.wait()` calls proportionally, and `clear_content()` waits for
   the voice before clearing. The picture never freezes or goes blank while the narrator talks.
   So: put `self.wait(…)` where a viewer needs time to look, and let the stretch do the rest.
   For exact sync with a recorded voice, use manim-voiceover bookmarks (`<bookmark mark="A"/>` in
   the narration and `self.wait_until_bookmark("A")`).
5. **Numbers are never typed twice.** Everything shown comes from `data.py`. If the video shows
   output of a real tool (a database, a compiler, a benchmark), a `capture.sh` saves that output
   and `data.py` parses it (see `dtak_manim/transcript.py`). Narration and visuals use
   `{placeholders}` filled from `data.FACTS`, so the voice cannot contradict the screen. Add a
   `tests/test_<episode>.py` that checks the numbers against each other (e.g. a cost formula).
6. **Every claim has a source.** Non-trivial statements cite an entry of `REFERENCES.md` in
   the beat's `refs:`. Prefer official documentation and source code over blog posts.
7. **Subtitles for free.** manim-voiceover writes an `.srt` per scene; `dtak render` merges
   them next to the episode video.

## Identity (fixed, in `theme.py` and `chrome.py`)

- **Canvas:** 16:9 (14.22 × 8 manim units). White background for content frames.
- **Colors:** titles navy `NAVY`, body `TEXT`, secondary `MUTED`, accent `UPC_BLUE`,
  lines/borders `EDGE_NAVY`, `SOFT_BLUE` for flowing data and as the accent on navy, tints
  `BLUE_TINT`, `BLUE_TINT_2`, `NAVY_TINT`. `ERROR` (red) and `OK` (green) are **not** brand
  colors: use them only for an error/violation and a success/match. Never write hex values in
  a scene.
- **Fonts:** Montserrat Bold for titles only (`title_text`), Roboto for everything else
  (`body_text`, `markup`), Roboto Mono for code, values and tool output (`mono_text`,
  `CodeBlock`). Use the helpers: a raw manim `Text` is white by default and uses the wrong font.
- **Chrome** (added by `DtakScene`; never add logos by hand):
  - a thin UPC-blue bar at the top of light frames;
  - the footer of the slide templates: **UPC mark (left) · thin UPC-blue rule · `dtak_short`
    (right)**, both marks the same height (UPC coexistence rule);
  - **section cards**: full navy frame, section number in soft blue, white Montserrat title,
    soft-blue subtitle, negative marks and a 50 % white rule.
- **Layout zones:** content stays inside the frame, below the slide title (title at the top-left)
  and above the footer (`theme.CONTENT_TOP`, `theme.CONTENT_BOTTOM`). `dtak check` enforces it.
- **Title slide** (`self.title_slide()`, beat 0.1): the opening of the JOIN video. Light frame with
  bar and footer; the long DTAK logo fades in, centred high; the Montserrat title is written below
  it and the subtitle (UPC blue) fades in; an optional muted "author · institute · date" line
  if `episode.yaml` fills those fields. All text comes from `episode.yaml`.
- **Closing card** (`self.closing_card()`, last beat): navy frame, long dark DTAK logo,
  "Thanks for watching" and a pointer to the references in soft blue.
- **Titles fade, never morph:** `set_title()` fades the old title out and the new one in.

## Writing a scene

```python
class LoremIpsum(EpisodeScene):
    SECTION = 1

    @beat("1.1")
    def lorem(self):
        self.set_title("Title", "optional subtitle")
        table = DbTable("name", cols, rows).move_to([3, 0, 0])
        self.play(FadeIn(table))
        self.wait(2)               # elastic pause
        self.clear_content()       # waits for the narration, then fades everything but the chrome
```

- Frame: `title_slide()`, `road_map(groups)`, `takeaways(items)`, `closing_card()`; content:
  `set_title(text, subtitle)`, `clear_content(keep_title=False)`, `section_card(...)` (automatic),
  `self.tracker` (current voiceover tracker), `self.episode`.
- Text: `title_text`, `body_text`, `mono_text`, `markup` (Pango markup: `<b>`, `<i>`,
  `<span foreground=…>`; escape `<` as `&lt;`), `accent()`, `bullet_list`, `callout(text, color)`,
  `tag("PK")`. Code and tool output: `CodeBlock(code, language="sql"|"plan"|"plain")`, whose
  `.lines[i]` are the glyphs of line `i` and `.line_slot(i)` a highlight rectangle (add it with
  `set_z_index(-1)`).
- Tables: `DbTable(name, columns, rows, pk=…, fk=…)` with `.row(i)`, `.column(name)`,
  `.cell(i, j)`, `.column_labels(j)`, `.new_row(values)`; `outline(mob)` to frame something.
  Flash text with `Indicate(row_labels(row))`, not the whole row (it repaints the cells).
- Diagrams: `box`, `labeled_box`, `link(a, b)` (arrow), `PlanNode(name, detail, math=MathTex)`
  with `edge(parent, child)`. Math: `MathTex(..., color=th.NAVY)`.
- New reusable components go into the library (`diagram.py`, or a new domain module like
  `db.py`), never copied between episodes.

## Pedagogy and consistency rules

1. **One idea per beat**, one running example for the whole video (the same small dataset on
   every frame), real outputs instead of invented ones.
2. Visuals and narration are complementary: the screen shows the structure and the key terms
   (the words in **bold** in the narration appear on screen as they are said); the voice
   explains. Avoid putting whole sentences on screen.
3. Every beat starts from a known state and leaves a clean one (`clear_content`, or a deliberate
   hand-over to the next beat).
4. Prefer standard, readable transitions: `FadeIn/FadeOut`, `Create`, `Write`, `GrowArrow`,
   `Indicate`, `ReplacementTransform` for "this becomes that". Do not morph unrelated texts.
5. Workflow: write the YAML first → `dtak docs` → read SCRIPT.md aloud → implement the beats →
   `dtak check` → `pytest` → 480p `dtak render --only N` → `dtak sheet` and look at the frames.
   `dtak check` catches content outside the frame, over the footer or over the title, but **not
   two pieces of content overlapping each other**: that needs a look at the contact sheet.
6. Section numbering in YAML, code and the road map comes from the YAML: renumbering a section
   means renaming its beat IDs and its `@beat` decorators together (tests catch mismatches).
7. Do not recolor, redraw or resize the logos, and do not restyle the chrome per scene. If
   something is missing, add it to `theme.py` / the library.

## Known manim pitfalls (already handled by the library)

- SVG stroke widths are not scaled with the viewBox: `make_logo` rescales the DTAK icon edges.
- `MarkupText` drops whitespace glyphs: `CodeBlock` maps glyphs back to lines by counting
  non-space characters (keep `disable_ligatures=True`).
- Animations add sub-mobjects one by one: `set_title` re-registers the title group so that
  `clear_content(keep_title=True)` can keep it.
- `Indicate` on a table row recolors the cell fills too; use `row_labels`.
- `fade()`/`set_opacity()` on arrows also changes their fill: use `save_state()` + `Restore`.
