"""Generic diagram building blocks: boxes, labeled boxes, arrows and tree nodes.

Use these for any "boxes and arrows" explanation (pipelines, trees, plans,
architectures). Everything uses the theme colors; never pass raw hex values.
"""

from __future__ import annotations

from manim import DOWN, Arrow, Line, Rectangle, RoundedRectangle, VGroup

from dtak_manim import theme as th
from dtak_manim.text import body_text, mono_text


def box(width, height, fill=th.WHITE, stroke=th.EDGE_NAVY, stroke_width=1.5, radius=0.0):
    if radius:
        return RoundedRectangle(
            corner_radius=radius, width=width, height=height, fill_color=fill,
            fill_opacity=1, stroke_color=stroke, stroke_width=stroke_width,
        )
    return Rectangle(
        width=width, height=height, fill_color=fill, fill_opacity=1,
        stroke_color=stroke, stroke_width=stroke_width,
    )


def labeled_box(label: str, width, height, fill=th.WHITE, size=th.SIZE_TINY, color=th.TEXT, mono=True, bold=False):
    r = box(width, height, fill=fill)
    t = (mono_text if mono else body_text)(label, color=color, size=size, bold=bold)
    if t.width > width - 0.08:
        t.scale_to_fit_width(width - 0.08)
    t.move_to(r)
    g = VGroup(r, t)
    g.rect, g.label = r, t
    return g


def link(a, b, color=th.EDGE_NAVY, buff=0.05, width=2.5, tip=0.16) -> Arrow:
    return Arrow(
        a, b, buff=buff, color=color, stroke_width=width,
        max_tip_length_to_length_ratio=0.25, tip_length=tip,
    )


# ---------------------------------------------------------------------------
# Heap
# ---------------------------------------------------------------------------

class PlanNode(VGroup):
    """A tree/graph node: a rounded box with a bold name (or a MathTex) and an
    optional small monospace detail line. Connect nodes with ``edge``."""

    def __init__(self, name: str, detail: str | None = None, color: str = th.UPC_BLUE, width: float | None = None, math=None):
        super().__init__()
        head = math if math is not None else body_text(name, color=color, size=th.SIZE_SMALL, bold=True)
        parts = [head]
        if detail:
            parts.append(mono_text(detail, color=th.TEXT, size=th.SIZE_TINY - 2))
        content = VGroup(*parts).arrange(DOWN, buff=0.08)
        w = width or content.width + 0.4
        self.frame = box(w, content.height + 0.3, fill=th.WHITE, stroke=color, stroke_width=2.5, radius=0.1)
        self.frame.move_to(content)
        self.head = head
        self.content = content
        self.add(self.frame, content)


def edge(parent, child, color=th.EDGE_NAVY) -> Line:
    return Line(parent.get_bottom(), child.get_top(), color=color, stroke_width=2.5, buff=0.04)


def upward_edge(child, parent, color=th.EDGE_NAVY) -> Arrow:
    """Data flows upward in the executor: child -> parent."""
    return Arrow(child.get_top(), parent.get_bottom(), buff=0.04, color=color, stroke_width=2.5, tip_length=0.14)


__all__ = ["box", "labeled_box", "link", "PlanNode", "edge", "upward_edge"]
