"""Episodes and beats: the single source of truth for storyboard + narration.

An episode folder contains::

    episode.yaml        title, scene order
    beats/NN_*.yaml     one file per section: card title/subtitle and its beats
    REFERENCES.md       numbered sources, cited by the beats' ``refs``

Each beat has ``id``, ``title``, ``visual`` (what is on screen), ``narration``
(what is said) and ``refs``. Narration and visuals may contain ``{name}``
placeholders filled from the episode's *facts* (numbers measured by the
capture script), so the voice never contradicts the screen.

Scenes mark the code of each beat with the ``@beat("3.2")`` decorator; see
``dtak_manim.chrome.DtakScene``.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from dtak_manim.voice import estimate_seconds, spoken_text


class _Facts(dict):
    def __missing__(self, key):  # leave unknown placeholders visible
        return "{" + key + "}"


@dataclass
class Beat:
    id: str
    title: str
    visual: str
    narration: str
    refs: list[int] = field(default_factory=list)

    @property
    def spoken(self) -> str:
        return spoken_text(self.narration)

    def seconds(self, wpm: float) -> float:
        return estimate_seconds(self.narration, wpm)


@dataclass
class Section:
    number: int
    title: str
    subtitle: str
    module: str  # python module with the scene
    scene: str  # scene class name
    beats: list[Beat]
    card: bool = True  # open with a navy section card


@dataclass
class Episode:
    root: Path
    slug: str
    title: str
    wpm: float
    sections: list[Section]
    subtitle: str = ""
    author: str = ""
    institute: str = ""
    date: str = ""

    @property
    def byline(self) -> str:
        """'author · institute · date', skipping empty fields (as in the slide templates)."""
        return " · ".join(x for x in (self.author, self.institute, self.date) if x)

    @classmethod
    def load(cls, root: Path, facts: dict | None = None) -> "Episode":
        root = Path(root)
        meta = yaml.safe_load((root / "episode.yaml").read_text())
        facts = _Facts(facts or {})
        sections = []
        for entry in meta["scenes"]:
            data = yaml.safe_load((root / entry["beats"]).read_text())
            beats = [
                Beat(
                    id=str(b["id"]),
                    title=b["title"],
                    visual=b["visual"].strip().format_map(facts),
                    narration=b["narration"].strip().format_map(facts),
                    refs=list(b.get("refs", [])),
                )
                for b in data["beats"]
            ]
            sections.append(Section(
                number=int(data["section"]), title=data["title"], subtitle=data.get("subtitle", ""),
                module=entry["module"], scene=entry["scene"], beats=beats, card=data.get("card", True),
            ))
        return cls(
            root=root, slug=meta["slug"], title=meta["title"], wpm=float(meta.get("words_per_minute", 140)),
            sections=sections, subtitle=str(meta.get("subtitle", "")), author=str(meta.get("author", "")),
            institute=str(meta.get("institute", "")), date=str(meta.get("date", "")),
        )

    def beat(self, beat_id: str) -> Beat:
        for s in self.sections:
            for b in s.beats:
                if b.id == beat_id:
                    return b
        raise KeyError(f"beat {beat_id!r} is not in {self.slug}/beats/*.yaml")

    def section(self, number: int) -> Section:
        for s in self.sections:
            if s.number == number:
                return s
        raise KeyError(number)


def beat(beat_id: str):
    """Decorator for a scene method that implements one beat.

    The method runs inside a voiceover of the beat's narration: the beat lasts
    max(animations, narration), and its clip is a manim section named after it.
    """

    def deco(fn):
        @functools.wraps(fn)
        def wrapper(self, *args, **kwargs):
            with self.beat_context(beat_id):
                return fn(self, *args, **kwargs)

        wrapper.beat_id = beat_id
        return wrapper

    return deco


def beat_methods(scene_cls) -> list[str]:
    """Beat ids implemented by a scene class, in definition order."""
    return [m.beat_id for m in vars(scene_cls).values() if callable(m) and hasattr(m, "beat_id")]
