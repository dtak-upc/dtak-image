"""Optional components for database topics: heap pages, B-trees, hash tables.

They were built for the DTAK video "How does a JOIN work?" and are kept as
worked examples of domain components built on top of ``diagram``. Delete this
module if your video does not need it; add new domain modules alongside it.
"""

from __future__ import annotations

from manim import DOWN, LEFT, PI, RIGHT, UP, Arrow, CurvedArrow, Line, Triangle, VGroup

from dtak_manim import theme as th
from dtak_manim.diagram import box, labeled_box
from dtak_manim.text import body_text, mono_text


# ---------------------------------------------------------------------------
# Heap
# ---------------------------------------------------------------------------
class HeapFile(VGroup):
    """A row of small page squares: 0 1 2 ... n-1 (with an ellipsis)."""

    def __init__(self, n_pages: int, shown: int = 6, size: float = 0.62, label: str | None = None):
        super().__init__()
        self.pages = VGroup()
        numbers = list(range(shown - 1)) + [None, n_pages - 1]
        for n in numbers:
            if n is None:
                p = body_text("…", color=th.MUTED, size=th.SIZE_BODY)
                p.set(width=size * 0.6)
            else:
                p = labeled_box(str(n), size, size, fill=th.WHITE, size=th.SIZE_SMALL, color=th.NAVY)
                p.page_no = n
            self.pages.add(p)
        self.pages.arrange(RIGHT, buff=0.12)
        self.add(self.pages)
        if label:
            self.label = body_text(label, color=th.MUTED, size=th.SIZE_SMALL)
            self.label.next_to(self.pages, DOWN, buff=0.18)
            self.add(self.label)

    def page(self, n: int):
        for p in self.pages:
            if getattr(p, "page_no", None) == n:
                return p
        raise KeyError(n)


class HeapPage(VGroup):
    """One 8 kB slotted page: header + line pointers -> free space <- tuples.

    Attributes: ``frame``, ``header``, ``lps`` (line pointers), ``tuples``,
    ``free`` (free-space label), ``pointers`` (arrows lp_i -> tuple_i).
    """

    def __init__(self, tuple_labels: list[str], width: float = 11.0, height: float = 3.3):
        super().__init__()
        self.frame = box(width, height, fill=th.WHITE, stroke=th.NAVY, stroke_width=3)
        self.add(self.frame)
        band_h = 0.62
        left = self.frame.get_left()[0]
        right = self.frame.get_right()[0]
        top = self.frame.get_top()[1]
        bottom = self.frame.get_bottom()[1]

        self.header = labeled_box("PageHeader · 24 B", 2.3, band_h, fill=th.NAVY_TINT, size=th.SIZE_TINY, color=th.NAVY, bold=True)
        self.header.move_to([left + 1.15, top - band_h / 2, 0])
        self.add(self.header)

        self.lps = VGroup()
        x = left + 2.3
        for i in range(len(tuple_labels)):
            lp = labeled_box(f"lp{i + 1}", 0.62, band_h, fill=th.BLUE_TINT, size=th.SIZE_TINY, color=th.UPC_BLUE, bold=True)
            lp.move_to([x + 0.31, top - band_h / 2, 0])
            x += 0.62
            self.lps.add(lp)
        self.add(self.lps)
        self.lower_x = x

        self.tuples = VGroup()
        tuple_w = (width - 2.6) / max(len(tuple_labels), 1)
        tuple_w = min(tuple_w, 1.65)
        x = right
        for i, lab in enumerate(tuple_labels):
            t = labeled_box(lab, tuple_w, band_h + 0.15, fill=th.WHITE, size=th.SIZE_TINY, color=th.TEXT)
            t.move_to([x - tuple_w / 2, bottom + (band_h + 0.15) / 2, 0])
            x -= tuple_w
            self.tuples.add(t)
        self.add(self.tuples)
        self.upper_x = x

        mid_y = (top - band_h + bottom + band_h + 0.15) / 2
        self.free = body_text("free space", color=th.MUTED, size=th.SIZE_SMALL)
        self.free.move_to([(left + right) / 2, mid_y, 0])
        self.grow_right = Arrow([self.lower_x + 0.05, top - band_h / 2, 0], [self.lower_x + 0.9, top - band_h / 2, 0], buff=0, color=th.UPC_BLUE, stroke_width=3, tip_length=0.15)
        self.grow_left = Arrow([self.upper_x - 0.05, bottom + 0.38, 0], [self.upper_x - 0.9, bottom + 0.38, 0], buff=0, color=th.UPC_BLUE, stroke_width=3, tip_length=0.15)
        self.add(self.free, self.grow_right, self.grow_left)

        self.pointers = VGroup()
        for lp, t in zip(self.lps, self.tuples):
            a = CurvedArrow(
                lp.get_bottom() + DOWN * 0.02, t.get_top() + UP * 0.02,
                angle=-0.35, color=th.EDGE_NAVY, stroke_width=2, tip_length=0.14,
            )
            self.pointers.add(a)
        self.add(self.pointers)

        # byte-offset markers (pd_lower / pd_upper / end of page)
        self.markers = VGroup()
        for xpos, txt, ypos in (
            (self.lower_x, "lower", top + 0.22),
            (self.upper_x, "upper", bottom - 0.22),
            (right, "8192", bottom - 0.22),
        ):
            m = mono_text(txt, color=th.MUTED, size=th.SIZE_TINY)
            m.move_to([xpos, ypos, 0])
            self.markers.add(m)


# ---------------------------------------------------------------------------
# B-tree
# ---------------------------------------------------------------------------
def entry_box(key, ptr: str, key_w=0.55, ptr_w=0.75, h=0.42, size=th.SIZE_TINY):
    k = labeled_box(str(key), key_w, h, fill=th.BLUE_TINT, size=size, color=th.NAVY, bold=True)
    p = labeled_box(ptr, ptr_w, h, fill=th.WHITE, size=size, color=th.MUTED)
    g = VGroup(k, p).arrange(RIGHT, buff=0)
    g.key, g.ptr = k, p
    return g


class BTreeNode(VGroup):
    """An index page: a titled box holding (key, pointer) entries."""

    def __init__(self, title: str, entries: list[tuple], vertical: bool = False, ellipsis: bool = True, key_w=0.62, ptr_w=0.75):
        super().__init__()
        self.entries = VGroup(*[entry_box(k, p, key_w=key_w, ptr_w=ptr_w) for k, p in entries])
        if ellipsis:
            dots = body_text("…", color=th.MUTED, size=th.SIZE_SMALL)
            self.entries.add(dots)
        self.entries.arrange(DOWN if vertical else RIGHT, buff=0.06 if vertical else 0.1)
        self.frame = box(self.entries.width + 0.25, self.entries.height + 0.25, fill=th.NAVY_TINT, stroke=th.NAVY, stroke_width=2, radius=0.08)
        self.frame.move_to(self.entries)
        self.title = mono_text(title, color=th.NAVY, size=th.SIZE_TINY, bold=True)
        self.title.next_to(self.frame, UP, buff=0.06).align_to(self.frame, LEFT)
        self.add(self.frame, self.entries, self.title)


def sibling_link(a, b) -> Line:
    """Right-sibling pointer between two leaf pages (dashed-looking line)."""
    return Arrow(a.frame.get_right(), b.frame.get_left(), buff=0.04, color=th.EDGE_NAVY, stroke_width=2, tip_length=0.12)




# ---------------------------------------------------------------------------
# Join algorithms
# ---------------------------------------------------------------------------
def cursor(target, side=LEFT, color: str = th.UPC_BLUE, size: float = 0.12) -> Triangle:
    """A small triangle next to ``target`` pointing at it (merge-join style)."""
    tri = Triangle(color=color, fill_color=color, fill_opacity=1).scale(size)
    tri.rotate(-PI / 2 if side is LEFT else PI / 2)
    return tri.next_to(target, side, buff=0.1)


class HashTable(VGroup):
    """``n`` buckets drawn as rows: [bucket number | slot]. ``bucket(i)`` is the slot."""

    def __init__(self, n: int = 4, slot_width: float = 2.4, height: float = 0.48):
        super().__init__()
        for b in range(n):
            lbl = labeled_box(str(b), 0.5, height, fill=th.NAVY_TINT, size=th.SIZE_SMALL, color=th.NAVY, bold=True)
            slot = box(slot_width, height, fill=th.WHITE)
            self.add(VGroup(lbl, slot).arrange(RIGHT, buff=0))
        self.arrange(DOWN, buff=0.08)

    def label(self, i: int):
        return self[i][0]

    def bucket(self, i: int):
        return self[i][1]

    def entry(self, text: str, i: int, width: float = 1.6):
        """A small entry box placed inside bucket ``i`` (not added to the scene)."""
        e = labeled_box(text, width, 0.36, fill=th.BLUE_TINT, size=th.SIZE_TINY, color=th.NAVY)
        return e.move_to(self.bucket(i))
