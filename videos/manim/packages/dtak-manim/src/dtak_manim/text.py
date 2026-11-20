"""Text helpers: themed Text factories and a line-addressable code block."""

from __future__ import annotations

import html
import re

from manim import (
    BOLD,
    DOWN,
    LEFT,
    RIGHT,
    UP,
    MarkupText,
    Rectangle,
    RoundedRectangle,
    Text,
    VGroup,
)

from dtak_manim import theme as th


def title_text(text: str, color: str = th.NAVY, size: float = th.SIZE_TITLE) -> Text:
    """First-level title: Montserrat Bold (brand rule)."""
    return Text(text, font=th.TITLE_FONT, weight=BOLD, font_size=size, color=color)


def body_text(
    text: str,
    color: str = th.TEXT,
    size: float = th.SIZE_BODY,
    bold: bool = False,
    **kwargs,
) -> Text:
    return Text(
        text,
        font=th.BODY_FONT,
        weight=BOLD if bold else "NORMAL",
        font_size=size,
        color=color,
        **kwargs,
    )


def mono_text(text: str, color: str = th.TEXT, size: float = th.SIZE_CODE, bold: bool = False) -> Text:
    return Text(
        text,
        font=th.MONO_FONT,
        weight=BOLD if bold else "NORMAL",
        font_size=size,
        color=color,
        disable_ligatures=True,
    )


def markup(text: str, color: str = th.TEXT, size: float = th.SIZE_BODY, font: str = th.BODY_FONT) -> MarkupText:
    """Pango markup, e.g. 'a <b>bold</b> <span fgcolor="#0076CF">word</span>'."""
    return MarkupText(text, font=font, font_size=size, color=color, disable_ligatures=True)


def accent(s: str, color: str = th.UPC_BLUE) -> str:
    """Wrap a fragment for `markup()` in bold accent color."""
    return f'<span foreground="{color}"><b>{s}</b></span>'


def bullet_list(items: list[str], size: float = th.SIZE_BODY, buff: float = 0.28) -> VGroup:
    """Vertical list of markup items, each with an accent bullet."""
    rows = []
    for item in items:
        dot = Text("•", font=th.BODY_FONT, font_size=size, color=th.UPC_BLUE)
        row = VGroup(dot, markup(item, size=size)).arrange(RIGHT, buff=0.18)
        rows.append(row)
    return VGroup(*rows).arrange(DOWN, aligned_edge=LEFT, buff=buff)


# ---------------------------------------------------------------------------
# Syntax highlighting (tiny, purpose-built: SQL and EXPLAIN output)
# ---------------------------------------------------------------------------
SQL_KEYWORDS = {
    "SELECT", "FROM", "WHERE", "JOIN", "ON", "AND", "OR", "NOT", "NULL",
    "CREATE", "TABLE", "PRIMARY", "KEY", "REFERENCES", "INSERT", "INTO",
    "VALUES", "DELETE", "UPDATE", "SET", "ORDER", "BY", "EXPLAIN", "ANALYZE",
    "INDEX", "AS", "CASCADE", "RESTRICT", "integer", "text", "numeric",
    "FOREIGN", "LIMIT", "BUFFERS",
}
PLAN_NODES = re.compile(
    r"^(\s*(?:->\s+)?)(Hash Join|Nested Loop|Merge Join|Seq Scan|Index Scan|"
    r"Index Only Scan|Bitmap Heap Scan|Bitmap Index Scan|Hash|Sort)\b"
)
_TOKEN = re.compile(r"('[^']*')|(--.*$)|([A-Za-z_][A-Za-z_0-9]*)|(\d+(?:\.\d+)?)|(\s+)|(.)")


def _span(s: str, color: str, bold: bool = False, italic: bool = False) -> str:
    s = html.escape(s, quote=False)
    if bold:
        s = f"<b>{s}</b>"
    if italic:
        s = f"<i>{s}</i>"
    return f'<span foreground="{color}">{s}</span>'


def highlight_sql(line: str) -> str:
    out = []
    for m in _TOKEN.finditer(line):
        string, comment, word, number, space, other = m.groups()
        if string:
            out.append(_span(string, th.NAVY, italic=True))
        elif comment:
            out.append(_span(comment, th.MUTED, italic=True))
        elif word:
            if word in SQL_KEYWORDS:
                out.append(_span(word, th.UPC_BLUE, bold=True))
            else:
                out.append(_span(word, th.TEXT))
        elif number:
            out.append(_span(number, th.NAVY))
        else:
            out.append(html.escape(m.group(0), quote=False))
    return "".join(out)


def highlight_plan(line: str) -> str:
    """EXPLAIN output: node names in accent, costs muted."""
    m = PLAN_NODES.match(line)
    if not m:
        # detail lines such as "Hash Cond: (...)"
        km = re.match(r"^(\s*)([A-Za-z ]+:)(.*)$", line)
        if km:
            return html.escape(km.group(1)) + _span(km.group(2), th.NAVY, bold=True) + _span(km.group(3), th.TEXT)
        return _span(line, th.TEXT)
    prefix, node = m.group(1), m.group(2)
    rest = line[m.end():]
    cost = re.search(r"\s*\(cost=.*$", rest)
    middle, tail = (rest[: cost.start()], rest[cost.start():]) if cost else (rest, "")
    return (
        _span(prefix, th.EDGE_NAVY, bold=True)
        + _span(node, th.UPC_BLUE, bold=True)
        + _span(middle, th.TEXT)
        + _span(tail, th.MUTED)
    )


class CodeBlock(VGroup):
    """A monospace block whose lines can be addressed individually.

    The whole block is laid out as ONE MarkupText (so baselines and indentation
    are exact) and then split into per-line glyph groups: `block.lines[i]`.
    """

    def __init__(
        self,
        code: str,
        language: str = "sql",  # "sql" | "plan" | "plain"
        size: float = th.SIZE_CODE,
        background: bool = True,
        pad: float = 0.22,
        max_width: float | None = None,
    ):
        super().__init__()
        self.raw_lines = code.strip("\n").split("\n")
        hl = {"sql": highlight_sql, "plan": highlight_plan}.get(
            language, lambda s: _span(s, th.TEXT)
        )
        body = "\n".join(hl(line) if line.strip() else " " for line in self.raw_lines)
        self.text = MarkupText(body, font=th.MONO_FONT, font_size=size, color=th.TEXT, disable_ligatures=True)
        if max_width and self.text.width > max_width:
            self.text.scale_to_fit_width(max_width)

        # split glyphs per line (whitespace has no glyph)
        self.lines = VGroup()
        i = 0
        glyphs = self.text.submobjects
        for line in self.raw_lines:
            n = len(re.sub(r"\s", "", line))
            self.lines.add(VGroup(*glyphs[i : i + n]))
            i += n
        n_lines = len(self.raw_lines)
        self.line_h = self.text.height / max(n_lines, 1)

        if background:
            self.bg = RoundedRectangle(
                corner_radius=0.08,
                width=self.text.width + 2 * pad,
                height=self.text.height + 2 * pad,
                fill_color=th.BLUE_TINT,
                fill_opacity=1,
                stroke_width=0,
            ).move_to(self.text)
            stripe = Rectangle(
                width=0.06, height=self.bg.height, fill_color=th.UPC_BLUE,
                fill_opacity=1, stroke_width=0,
            ).align_to(self.bg, LEFT).align_to(self.bg, UP)
            self.bg_group = VGroup(self.bg, stripe)
            self.add(self.bg_group)
        self.add(self.text)

    def line_slot(self, i: int, color: str = th.BLUE_TINT_2, opacity: float = 1.0) -> Rectangle:
        """A rectangle behind line i (for highlighting). Add it with z_index below the text."""
        top = self.text.get_top()[1]
        y = top - (i + 0.5) * self.line_h
        width = (self.bg.width - 0.1) if hasattr(self, "bg") else self.text.width + 0.2
        rect = Rectangle(
            width=width, height=self.line_h * 1.02, fill_color=color,
            fill_opacity=opacity, stroke_width=0,
        )
        rect.move_to([self.text.get_center()[0] + (0.03 if hasattr(self, "bg") else 0), y, 0])
        return rect


def tag(text: str, color: str = th.UPC_BLUE, text_color: str = th.WHITE, size: float = th.SIZE_TINY) -> VGroup:
    """Small rounded label, e.g. PK / FK badges or section numbers."""
    t = Text(text, font=th.BODY_FONT, weight=BOLD, font_size=size, color=text_color)
    box = RoundedRectangle(
        corner_radius=0.06, width=t.width + 0.16, height=t.height + 0.12,
        fill_color=color, fill_opacity=1, stroke_width=0,
    ).move_to(t)
    return VGroup(box, t)


def callout(text: str, color: str = th.UPC_BLUE, size: float = th.SIZE_SMALL, width: float | None = None) -> VGroup:
    """A tinted panel with a colored left border holding a short markup text."""
    t = markup(text, size=size)
    if width and t.width > width:
        t.scale_to_fit_width(width)
    tint = {th.ERROR: th.ERROR_TINT, th.OK: th.OK_TINT}.get(color, th.BLUE_TINT)
    box = Rectangle(
        width=t.width + 0.5, height=t.height + 0.32, fill_color=tint,
        fill_opacity=1, stroke_width=0,
    ).move_to(t)
    bar = Rectangle(width=0.07, height=box.height, fill_color=color, fill_opacity=1, stroke_width=0)
    bar.next_to(box, LEFT, buff=0)
    return VGroup(box, bar, t)


__all__ = [
    "title_text", "body_text", "mono_text", "markup", "accent", "bullet_list",
    "CodeBlock", "tag", "callout", "highlight_sql", "highlight_plan",
]
