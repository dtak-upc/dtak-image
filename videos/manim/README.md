# DTAK videos (manim)

Template for DTAK educational videos with [manim](https://docs.manim.community/) and
[manim-voiceover](https://voiceover.manim.community/): the DTAK identity (colors, fonts, the
UPC · rule · DTAK footer, navy section cards), a beat-by-beat workflow where storyboard and
narration live together in YAML, narration-driven timing, layout checks and subtitles.

```sh
uv sync --group dev
uv run dtak check 00 && uv run dtak render 00    # the Lorem Ipsum demo, 480p preview
uv run dtak new 01-my-topic && uv sync           # start your own video
```

Read **[AGENTS.md](AGENTS.md)** before starting (and only render low-resolution previews:
high resolution is very slow). To use it outside this repository: `cp -rL videos/manim my-video`.
