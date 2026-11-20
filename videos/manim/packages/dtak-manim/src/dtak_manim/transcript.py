"""Read a tagged transcript produced by an episode's capture script.

Example of the "real data" pattern: a capture script runs the real tool
(here psql; any CLI works) and saves its output; the episode's data module
parses numbers from it instead of typing them by hand.

The transcript is split into blocks by lines ``### <tag>`` (``\\echo`` in the
queries file). Inside a block we can read psql's aligned result tables, the
lines of an EXPLAIN plan, or an ERROR/DETAIL pair. Episodes build their data
module on top of this, so every number on screen comes from a real run.
"""

from __future__ import annotations

import re
from functools import cached_property
from pathlib import Path

_ROWS = re.compile(r"^\(\d+ rows?\)$")


class Transcript:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.text = self.path.read_text()

    @cached_property
    def blocks(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        current = None
        for line in self.text.splitlines():
            if line.startswith("### "):
                current = line[4:].strip()
                out[current] = []
            elif current is not None:
                out[current].append(line)
        return out

    def block(self, tag: str) -> list[str]:
        try:
            return self.blocks[tag]
        except KeyError:
            raise KeyError(f"no '### {tag}' block in {self.path}") from None

    def tables(self, tag: str) -> list[list[dict[str, str]]]:
        """All aligned result tables in a block, as lists of {column: value}."""
        lines = self.block(tag)
        result = []
        i = 0
        while i < len(lines) - 1:
            if re.match(r"^-+(\+-+)*$", lines[i + 1].strip()) and lines[i].strip():
                header = [h.strip() for h in lines[i].split("|")]
                rows = []
                i += 2
                while i < len(lines) and not _ROWS.match(lines[i].strip()):
                    cells = lines[i].split("|")
                    if len(header) == 1:  # keep indentation (EXPLAIN)
                        cells = [lines[i][1:].rstrip()]
                    else:
                        cells = [c.strip() for c in cells]
                    rows.append(dict(zip(header, cells)))
                    i += 1
                result.append(rows)
            i += 1
        return result

    def table(self, tag: str, index: int = 0) -> list[dict[str, str]]:
        return self.tables(tag)[index]

    def plan(self, tag: str, index: int = 0) -> list[str]:
        """Lines of an EXPLAIN output (column "QUERY PLAN")."""
        return [r["QUERY PLAN"] for r in self.table(tag, index)]

    def error(self, tag: str) -> tuple[str, str]:
        """(ERROR message, DETAIL message) of a failing statement."""
        err = detail = ""
        for line in self.block(tag):
            if line.startswith("ERROR:"):
                err = line[len("ERROR:"):].strip()
            elif line.startswith("DETAIL:"):
                detail = line[len("DETAIL:"):].strip()
        return err, detail


def strip_costs(lines: list[str]) -> list[str]:
    """Drop the '(cost=...)' estimates, keeping '(actual ...)' figures."""
    return [re.sub(r"  \(cost=[^)]*\)", "", line) for line in lines]


def dedent(lines: list[str]) -> list[str]:
    pad = min((len(x) - len(x.lstrip()) for x in lines if x.strip()), default=0)
    return [x[pad:] for x in lines]
