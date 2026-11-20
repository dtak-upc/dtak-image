"""`DbTable`: a relation drawn as a table, with addressable rows/columns/cells."""

from __future__ import annotations

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Rectangle,
    VGroup,
)

from dtak_manim import theme as th
from dtak_manim.text import mono_text, tag


class Cell(VGroup):
    def __init__(self, value, width: float, height: float, header: bool = False, size: float = th.SIZE_SMALL):
        super().__init__()
        self.value = value
        self.rect = Rectangle(
            width=width, height=height,
            stroke_color=th.EDGE_NAVY, stroke_width=1.5,
            fill_color=th.BLUE_TINT if header else th.WHITE, fill_opacity=1,
        )
        self.label = mono_text(str(value), color=th.NAVY if header else th.TEXT, size=size, bold=header)
        if self.label.width > width - 0.12:
            self.label.scale_to_fit_width(width - 0.12)
        self.label.move_to(self.rect)
        self.add(self.rect, self.label)


class DbTable(VGroup):
    """A relation drawn as a grid.

    Attributes: ``name_label``, ``header`` (VGroup of Cells), ``body`` (VGroup
    of rows, each a VGroup of Cells), ``badges`` (PK/FK tags above columns).
    """

    def __init__(
        self,
        name: str | None,
        columns: list[str],
        rows: list[tuple],
        pk: tuple[str, ...] = (),
        fk: tuple[str, ...] = (),
        col_widths: list[float] | None = None,
        cell_h: float = 0.46,
        size: float = th.SIZE_SMALL,
    ):
        super().__init__()
        self.columns = list(columns)
        self.cell_h = cell_h
        self.size = size
        if col_widths is None:
            col_widths = []
            for j, c in enumerate(columns):
                texts = [str(c)] + [str(r[j]) for r in rows]
                longest = max(len(t) for t in texts)
                col_widths.append(max(0.9, 0.16 * longest * size / th.SIZE_SMALL + 0.4))
        self.col_widths = col_widths

        self.header = self._make_row(columns, header=True)
        self.body = VGroup(*[self._make_row(r) for r in rows])
        grid = VGroup(self.header, *self.body).arrange(DOWN, buff=0)
        self.add(grid)
        self.grid = grid

        self.badges = VGroup()
        for j, c in enumerate(columns):
            labels = []
            if c in pk:
                labels.append(tag("PK", th.UPC_BLUE))
            if c in fk:
                labels.append(tag("FK", th.NAVY))
            if labels:
                b = VGroup(*labels).arrange(RIGHT, buff=0.05)
                b.next_to(self.header[j], UP, buff=0.06)
                self.badges.add(b)
        self.add(self.badges)

        self.name_label = None
        if name:
            self.name_label = mono_text(name, color=th.NAVY, size=size + 4, bold=True)
            anchor = VGroup(self.header, self.badges) if len(self.badges) else self.header
            self.name_label.next_to(anchor, UP, buff=0.12).align_to(self.header, LEFT)
            self.add(self.name_label)

    # -- construction --------------------------------------------------------
    def _make_row(self, values, header: bool = False) -> VGroup:
        cells = [
            Cell(v, w, self.cell_h, header=header, size=self.size)
            for v, w in zip(values, self.col_widths)
        ]
        return VGroup(*cells).arrange(RIGHT, buff=0)

    def new_row(self, values) -> VGroup:
        """A detached row with this table's geometry, placed under the last row."""
        row = self._make_row(values)
        last = self.body[-1] if len(self.body) else self.header
        row.next_to(last, DOWN, buff=0).align_to(self.header, LEFT)
        return row

    # -- access --------------------------------------------------------------
    def row(self, i: int) -> VGroup:
        return self.body[i]

    def cell(self, i: int, j: int | str) -> Cell:
        return self.body[i][self._col(j)]

    def column(self, j: int | str, with_header: bool = False) -> VGroup:
        j = self._col(j)
        cells = [r[j] for r in self.body]
        if with_header:
            cells = [self.header[j]] + cells
        return VGroup(*cells)

    def column_labels(self, j: int | str) -> VGroup:
        """Only the text of a column (to recolor values without their cells)."""
        return VGroup(*[c.label for c in self.column(j)])

    def header_cell(self, j: int | str) -> Cell:
        return self.header[self._col(j)]

    def _col(self, j):
        return self.columns.index(j) if isinstance(j, str) else j

    # -- styling helpers (return mobjects to animate with .animate) ---------
    @staticmethod
    def fill(cells, color: str):
        """Animation-friendly: ``self.play(DbTable.fill(cells, color))``."""
        group = cells if isinstance(cells, VGroup) else VGroup(*cells)
        rects = VGroup(*[c.rect for c in _cells_of(group)])
        return rects.animate.set_fill(color, opacity=1)


def _cells_of(group):
    if isinstance(group, Cell):
        return [group]
    out = []
    for m in group.submobjects:
        out.extend(_cells_of(m))
    return out


def outline(mob, color: str = th.UPC_BLUE, buff: float = 0.04, width: float = 4) -> Rectangle:
    """A rectangle surrounding `mob` (used to highlight rows/columns)."""
    r = Rectangle(
        width=mob.width + 2 * buff, height=mob.height + 2 * buff,
        stroke_color=color, stroke_width=width, fill_opacity=0,
    ).move_to(mob)
    return r



def row_labels(row) -> VGroup:
    """The texts of a DbTable row: flash these (``Indicate(row_labels(r))``)
    instead of the whole row, so the cell backgrounds are not repainted."""
    return VGroup(*[cell.label for cell in row])


__all__ = ["DbTable", "Cell", "outline", "row_labels"]
