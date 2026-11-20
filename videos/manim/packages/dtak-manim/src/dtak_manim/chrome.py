"""Scene "chrome": background, accent bar, footer, titles, section cards, beats.

Every scene inherits from `DtakScene`, so the identity, the voiceover and the
layout checks are applied in one place. Scenes only implement beats.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    AnimationGroup,
    Brace,
    FadeIn,
    FadeOut,
    Indicate,
    LaggedStart,
    Line,
    Rectangle,
    SVGMobject,
    VGroup,
    VMobject,
    Write,
    config,
)
from manim_voiceover import VoiceoverScene

from dtak_manim import theme as th
from dtak_manim.episode import Episode, beat_methods
from dtak_manim.text import body_text, markup, tag, title_text
from dtak_manim.voice import make_speech_service

# z-index layers
Z_CONTENT = 0
Z_CHROME = 10
Z_CARD = 20


def make_logo(dark: bool = False, long: bool = False, height: float = th.LOGO_H) -> SVGMobject:
    if long:
        path = th.LOGO_LONG_DARK if dark else th.LOGO_LONG
    else:
        path = th.LOGO_DARK if dark else th.LOGO_LIGHT
    logo = SVGMobject(str(path), height=height)
    # manim keeps SVG stroke widths in its own units, ignoring the viewBox
    # scale; rescale the icon edges (22.94 units in a 994-unit-tall viewBox,
    # see dtak-image/tools/make_logo.py) so they keep the logo's proportions.
    edge_w = 22.94 / 994.0 * height * 100
    for m in logo.family_members_with_points():
        if isinstance(m, Line):
            m.set_stroke(width=edge_w).set_fill(opacity=0)
    return logo


def make_upc_logo(dark: bool = False, height: float = th.LOGO_H) -> SVGMobject:
    """The UPC mark, as shipped with the DTAK slide templates (never recolored)."""
    return SVGMobject(str(th.UPC_LOGO_DARK if dark else th.UPC_LOGO), height=height)


def make_footer(dark: bool = False) -> VGroup:
    """Footer of the DTAK slide templates: UPC mark · thin rule · DTAK short logo.

    Both marks share the same height (UPC coexistence rule: equal footing,
    UPC on the left). The rule is UPC blue on light frames and 50 % white on
    dark ones, as in dtak-image/slides/revealjs/theme/dtak.css.
    """
    y = -th.FRAME_H / 2 + th.FOOTER_BOTTOM + th.LOGO_H / 2
    upc = make_upc_logo(dark=dark)
    upc.move_to([-th.FRAME_W / 2 + th.MARGIN + upc.width / 2, y, 0])
    dtak = make_logo(dark=dark)
    dtak.move_to([th.FRAME_W / 2 - th.MARGIN - dtak.width / 2, y, 0])
    rule = Line(
        [upc.get_right()[0] + th.FOOTER_GAP, y, 0],
        [dtak.get_left()[0] - th.FOOTER_GAP, y, 0],
        stroke_width=2,
    )
    if dark:
        rule.set_stroke(th.WHITE, opacity=0.5)
    else:
        rule.set_stroke(th.UPC_BLUE, opacity=1)
    footer = VGroup(upc, rule, dtak)
    footer.upc, footer.rule, footer.dtak = upc, rule, dtak
    return footer


class LayoutError(AssertionError):
    pass


class DtakScene(VoiceoverScene):
    """Base scene: light background, top accent bar, footer (UPC · rule · DTAK).

    Subclasses set ``episode`` (an :class:`Episode`) and ``SECTION`` and
    implement one method per beat, decorated with ``@beat("3.2")``. The default
    ``construct`` shows the section card (title/subtitle from the beats YAML)
    and runs the beats in the order of the YAML file.

    Helpers for beats:
      * ``self.set_title(text, subtitle)`` -- slide title (fade out / fade in)
      * ``self.clear_content()``           -- fade out everything but the chrome
      * ``self.tracker``                   -- the current voiceover tracker

    With ``DTAK_CHECK=1`` every ``play`` verifies that content stays inside
    the frame, below the slide title and above the footer (see ``dtak check``).
    """

    episode: Episode | None = None
    SECTION: int | None = None

    def setup(self):
        config.background_color = th.BG
        self.camera.background_color = th.BG
        self.accent_bar = Rectangle(
            width=th.FRAME_W + 0.1, height=th.ACCENT_BAR_H,
            fill_color=th.UPC_BLUE, fill_opacity=1, stroke_width=0,
        ).to_edge(UP, buff=0)
        self.footer = make_footer(dark=False)
        self.chrome = VGroup(self.accent_bar, self.footer)
        self.chrome.set_z_index(Z_CHROME)
        self.add(self.chrome)
        self.title_mob = None
        self.current_beat = None
        self.tracker = None
        self.layout_issues: list[str] = []
        self.checking = os.environ.get("DTAK_CHECK") == "1"
        # elastic beats: per-beat animation/pause times measured by `dtak check`
        self.timing_path = Path(os.environ.get("DTAK_TIMING", Path(config.media_dir) / "timing.json"))
        self.timing = {}
        if not self.checking and self.timing_path.exists():
            self.timing = json.loads(self.timing_path.read_text())
        self.measured: dict[str, dict] = {}
        self._stretch = 1.0
        self._beat_waits = 0.0
        self._voice_waits = 0.0
        slug = self.episode.slug if self.episode else "default"
        self.set_speech_service(make_speech_service(Path(config.media_dir) / "voiceovers" / slug))

    # -- structure -----------------------------------------------------------
    def construct(self):
        section = self.episode.section(self.SECTION)
        implemented = {bid: getattr(self, name) for name, m in vars(type(self)).items() if hasattr(m, "beat_id") for bid in [m.beat_id]}
        expected = [b.id for b in section.beats]
        if sorted(implemented) != sorted(expected):
            raise LayoutError(
                f"{type(self).__name__}: beats in code {beat_methods(type(self))} "
                f"!= beats in YAML {expected}"
            )
        if section.card:
            self.section_card(section.number, section.title, section.subtitle)
        for beat_id in expected:
            implemented[beat_id]()

    @contextmanager
    def beat_context(self, beat_id: str):
        """Run a beat inside the voiceover of its narration.

        Elastic timing: if the narration is longer than the beat's animations
        plus pauses (as measured by `dtak check`), every ``self.wait()`` of the
        beat is stretched by the same factor, so visuals and voice end together
        instead of freezing on the last frame.
        """
        b = self.episode.beat(beat_id)
        self.next_section(f"{b.id} {b.title}")
        self.current_beat = b.id
        t0 = self.renderer.time
        self._beat_waits = self._voice_waits = 0.0
        with self.voiceover(text=b.spoken) as tracker:
            self.tracker = tracker
            self._stretch = self._stretch_for(b.id, tracker.duration)
            yield tracker
            elapsed = self.renderer.time - t0 - self._voice_waits
            self.measured[b.id] = {"anim": round(elapsed - self._beat_waits, 3), "wait": round(self._beat_waits, 3)}
            self._stretch = 1.0
        self.tracker = None

    def _stretch_for(self, beat_id: str, narration: float) -> float:
        t = self.timing.get(beat_id)
        if not t or t["wait"] <= 0:
            return 1.0
        return max(1.0, (narration - t["anim"]) / t["wait"])

    def wait(self, duration: float = 1.0, *args, **kwargs):
        if self._stretch != 1.0:
            duration *= self._stretch
        self._beat_waits += duration / self._stretch
        super().wait(duration, *args, **kwargs)

    def wait_for_voiceover(self):
        """Wait for the rest of the narration (never stretched)."""
        if self.tracker is None:
            return
        remaining = self.tracker.get_remaining_duration()
        if remaining > 1 / config.frame_rate:
            stretch, self._stretch = self._stretch, 1.0
            before = self._beat_waits
            super().wait(remaining)
            self._beat_waits = before
            self._voice_waits += remaining
            self._stretch = stretch

    def tear_down(self):
        super().tear_down()
        if self.checking and self.measured:
            timing = json.loads(self.timing_path.read_text()) if self.timing_path.exists() else {}
            timing.update(self.measured)
            self.timing_path.parent.mkdir(parents=True, exist_ok=True)
            self.timing_path.write_text(json.dumps(timing, indent=1, sort_keys=True))
        for issue in dict.fromkeys(self.layout_issues):  # read by `dtak check`
            print("LAYOUT:", issue, flush=True)

    # -- layout checks ---------------------------------------------------------
    def play(self, *args, **kwargs):
        super().play(*args, **kwargs)
        if self.checking:
            self.check_layout()

    def check_layout(self, tol: float = 0.03):
        footer_top = -th.FRAME_H / 2 + th.FOOTER_BOTTOM + th.LOGO_H
        t = self.title_mob
        title_box = (t.get_left()[0], t.get_right()[0], t.get_bottom()[1]) if t is not None else None
        for m in self.content_mobjects():
            if m.z_index >= Z_CARD or m is self.title_mob or not m.has_points() and not m.submobjects:
                continue
            if isinstance(m, VMobject) and m.get_fill_opacity() == 0 and m.get_stroke_opacity() == 0 and not m.submobjects:
                continue
            left, right = m.get_left()[0], m.get_right()[0]
            top, bottom = m.get_top()[1], m.get_bottom()[1]
            name = type(m).__name__
            where = f"beat {self.current_beat}: {name} at ({m.get_x():.2f}, {m.get_y():.2f})"
            if left < -th.FRAME_W / 2 - tol or right > th.FRAME_W / 2 + tol:
                self.layout_issues.append(f"{where} leaves the frame horizontally [{left:.2f}, {right:.2f}]")
            if bottom < footer_top - tol and top > -th.FRAME_H / 2:
                self.layout_issues.append(f"{where} overlaps the footer (bottom {bottom:.2f} < {footer_top:.2f})")
            if title_box and top > title_box[2] + tol and right > title_box[0] and left < title_box[1]:
                self.layout_issues.append(f"{where} overlaps the title (top {top:.2f} > {title_box[2]:.2f})")

    # -- titles --------------------------------------------------------------
    def set_title(self, text: str, subtitle: str | None = None, run_time: float = 0.8):
        """Slide title. A new title never morphs from the old one: fade out, fade in."""
        new = title_text(text)
        group = VGroup(new)
        if subtitle:
            sub = body_text(subtitle, color=th.UPC_BLUE, size=th.SIZE_SMALL)
            sub.next_to(new, DOWN, buff=0.12, aligned_edge=LEFT)
            group.add(sub)
        group.to_corner(UP + LEFT, buff=0).shift(RIGHT * th.MARGIN + DOWN * 0.35)
        if self.title_mob is None:
            self.play(Write(new), *[FadeIn(m) for m in group[1:]], run_time=run_time)
            # the animations added the parts one by one: register the group
            # itself so that clear_content(keep_title=True) can recognise it
            self.remove(*group)
            self.add(group)
        else:
            old = self.title_mob
            self.title_mob = None  # not a title while both are on screen
            self.play(
                FadeOut(old, shift=UP * 0.15),
                FadeIn(group, shift=UP * 0.15),
                run_time=run_time,
            )
        self.title_mob = group
        return group

    # -- clearing ------------------------------------------------------------
    def content_mobjects(self):
        keep = {self.chrome}
        return [m for m in self.mobjects if m not in keep]

    def clear_content(self, run_time: float = 0.8, keep_title: bool = False):
        """Fade out the content. A full clear (end of a beat) first lets the
        narration finish, so the voice never talks over an empty slide."""
        if not keep_title:
            self.wait_for_voiceover()
        mobs = [m for m in self.content_mobjects() if not (keep_title and m is self.title_mob)]
        if mobs:
            self.play(*[FadeOut(m) for m in mobs], run_time=run_time)
        if not keep_title:
            self.title_mob = None

    # -- title slide ---------------------------------------------------------
    def title_slide(self, title: str | None = None, subtitle: str | None = None, byline: str | None = None,
                    hold: float = 2.0):
        """The opening frame of every video (the one of "How does a JOIN work?").

        Light frame with the usual bar and footer. The long DTAK logo fades in, centred
        high; the Montserrat title is written below it, with the subtitle in UPC blue and,
        if the episode has one, a muted "author · institute · date" line. Text defaults
        come from episode.yaml.
        """
        ep = self.episode
        title = title if title is not None else ep.title
        subtitle = subtitle if subtitle is not None else ep.subtitle
        byline = byline if byline is not None else ep.byline
        logo = make_logo(long=True, height=0.7).shift(UP * 1.6)
        head = title_text(title, size=54)
        if head.width > th.FRAME_W - 2 * th.MARGIN - 1:
            head.scale_to_fit_width(th.FRAME_W - 2 * th.MARGIN - 1)
        parts = [head]
        if subtitle:
            parts.append(body_text(subtitle, color=th.UPC_BLUE, size=th.SIZE_SUBTITLE))
        if byline:
            parts.append(body_text(byline, color=th.MUTED, size=th.SIZE_SMALL))
        VGroup(*parts).arrange(DOWN, buff=0.3).next_to(logo, DOWN, buff=0.7)
        self.play(FadeIn(logo, shift=DOWN * 0.2), run_time=1)
        self.play(Write(head), *[FadeIn(p, shift=UP * 0.2) for p in parts[1:]], run_time=1.5)
        self.wait(hold)
        self.clear_content()

    # -- road map --------------------------------------------------------------
    def road_map(self, groups: list[tuple[int, int, str]] | None = None, title: str = "Road map"):
        """Numbered list of the episode's sections (from the YAML), optionally with braces
        grouping consecutive sections: ``groups=[(1, 2, "logical: what it means"), ...]``."""
        self.set_title(title)
        sections = [s for s in self.episode.sections if s.number > 0]
        items = VGroup(*[
            VGroup(tag(str(s.number), th.UPC_BLUE, size=th.SIZE_SMALL), body_text(s.title, size=th.SIZE_BODY)).arrange(RIGHT, buff=0.3)
            for s in sections
        ])
        items.arrange(DOWN, aligned_edge=LEFT, buff=0.28).move_to([-1.5 if groups else 0, -0.3, 0])
        self.play(LaggedStart(*[FadeIn(it, shift=RIGHT * 0.2) for it in items], lag_ratio=0.25), run_time=max(1.5, 0.5 * len(items)))
        index = {s.number: i for i, s in enumerate(sections)}
        for first, last, label in groups or []:
            grp = items[index[first] : index[last] + 1]
            b = Brace(grp, RIGHT, color=th.EDGE_NAVY)
            lbl = body_text(label, color=th.UPC_BLUE, size=th.SIZE_SMALL).next_to(b, RIGHT, buff=0.15)
            self.play(FadeIn(b), FadeIn(lbl, shift=LEFT * 0.1), run_time=0.8)
            self.wait(0.8)
        self.wait(2)
        self.clear_content()

    # -- takeaways --------------------------------------------------------------
    def takeaways(self, items: list[str], title: str = "Takeaways"):
        """Numbered takeaways (Pango markup allowed: ``<b>key term</b>``), one at a time."""
        self.set_title(title)
        rows = VGroup(*[
            VGroup(tag(str(i), th.UPC_BLUE, size=th.SIZE_SMALL), markup(txt, size=th.SIZE_SMALL)).arrange(RIGHT, buff=0.3)
            for i, txt in enumerate(items, start=1)
        ])
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.3).move_to([0, -0.1, 0])
        for r in rows:
            self.play(FadeIn(r, shift=RIGHT * 0.2), run_time=0.6)
            self.wait(1.4)
        self.wait(2)
        self.play(Indicate(rows, color=th.UPC_BLUE, scale_factor=1.02))
        self.clear_content()

    # -- closing card --------------------------------------------------------
    def closing_card(self, text: str = "Thanks for watching",
                     subtitle: str = "Sources and further reading: see REFERENCES.md", hold: float = 4.0):
        """Last frame of every video: navy, long dark DTAK logo, a thank-you line.
        Call it on a clean screen (the previous beat ends with clear_content)."""
        bg = Rectangle(width=th.FRAME_W + 0.2, height=th.FRAME_H + 0.2, fill_color=th.NAVY,
                       fill_opacity=1, stroke_width=0).set_z_index(Z_CARD)
        logo = make_logo(dark=True, long=True, height=0.9).move_to([0, 0.9, 0]).set_z_index(Z_CARD + 1)
        thanks = title_text(text, color=th.WHITE, size=40).next_to(logo, DOWN, buff=0.8).set_z_index(Z_CARD + 1)
        parts = [thanks]
        if subtitle:
            parts.append(body_text(subtitle, color=th.SOFT_BLUE, size=th.SIZE_SMALL).next_to(thanks, DOWN, buff=0.3).set_z_index(Z_CARD + 1))
        self.play(FadeIn(bg))
        self.play(FadeIn(logo, shift=DOWN * 0.2), Write(thanks), *[FadeIn(p) for p in parts[1:]], run_time=1.5)
        self.wait(hold)

    # -- section card --------------------------------------------------------
    def section_card(self, number: int | str, title: str, subtitle: str = "", hold: float = 2.0):
        """Full-screen navy card (brand: section slides are navy)."""
        self.clear_content(run_time=0.5)
        bg = Rectangle(
            width=th.FRAME_W + 0.2, height=th.FRAME_H + 0.2,
            fill_color=th.NAVY, fill_opacity=1, stroke_width=0,
        ).set_z_index(Z_CARD)
        num = title_text(f"{number}", color=th.SOFT_BLUE, size=96)
        ttl = title_text(title, color=th.WHITE, size=46)
        parts = [num, ttl]
        if subtitle:
            parts.append(body_text(subtitle, color=th.SOFT_BLUE, size=th.SIZE_SUBTITLE))
        text = VGroup(*parts).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        if text.width > th.FRAME_W - 2:
            text.scale_to_fit_width(th.FRAME_W - 2)
        text.to_edge(LEFT, buff=1.2)
        footer = make_footer(dark=True)
        card = VGroup(text, footer).set_z_index(Z_CARD + 1)
        self.play(FadeIn(bg), run_time=0.6)
        self.play(
            AnimationGroup(FadeIn(num, shift=RIGHT * 0.3), Write(ttl), lag_ratio=0.3),
            *[FadeIn(p, shift=UP * 0.2) for p in parts[2:]],
            FadeIn(footer),
            run_time=1.4,
        )
        self.wait(hold)
        self.play(FadeOut(VGroup(bg, card)), run_time=0.8)
