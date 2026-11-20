"""Fast consistency checks for every episode (no rendering; `dtak check` does layout).

Episode-specific data checks (e.g. "the numbers on screen match the capture")
go in their own test_<episode>.py next to this file.
"""

import importlib
import re
from pathlib import Path

import pytest
import yaml

from dtak_manim.docs import script, storyboard
from dtak_manim.episode import beat_methods

ROOT = Path(__file__).resolve().parents[1]


def _episodes():
    for d in sorted((ROOT / "episodes").iterdir()):
        if (d / "episode.yaml").exists():
            package = yaml.safe_load((d / "episode.yaml").read_text())["scenes"][0]["module"].split(".")[0]
            yield importlib.import_module(package).EPISODE


EPISODES = list(_episodes())
SECTIONS = [(ep, s) for ep in EPISODES for s in ep.sections]


@pytest.mark.parametrize("ep,section", SECTIONS, ids=lambda x: getattr(x, "scene", getattr(x, "slug", "")))
def test_every_yaml_beat_is_implemented_once(ep, section):
    scene = getattr(importlib.import_module(section.module), section.scene)
    assert scene.SECTION == section.number
    assert sorted(beat_methods(scene)) == sorted(b.id for b in section.beats)


@pytest.mark.parametrize("ep", EPISODES, ids=lambda e: e.slug)
def test_beat_ids_unique_and_numbered_by_section(ep):
    ids = [b.id for s in ep.sections for b in s.beats]
    assert len(ids) == len(set(ids))
    for s in ep.sections:
        assert all(b.id.split(".")[0] == str(s.number) for b in s.beats)


@pytest.mark.parametrize("ep", EPISODES, ids=lambda e: e.slug)
def test_all_placeholders_resolved(ep):
    for s in ep.sections:
        for b in s.beats:
            for text in (b.visual, b.narration):
                assert not re.search(r"\{[a-z_]+\}", text), f"{b.id}: unresolved placeholder in {text!r}"


@pytest.mark.parametrize("ep", EPISODES, ids=lambda e: e.slug)
def test_refs_exist_in_references_md(ep):
    numbered = {int(n) for n in re.findall(r"^(\d+)\. ", (ep.root / "REFERENCES.md").read_text(), flags=re.M)}
    used = {r for s in ep.sections for b in s.beats for r in b.refs}
    assert used <= numbered, f"missing references: {sorted(used - numbered)}"


@pytest.mark.parametrize("ep", EPISODES, ids=lambda e: e.slug)
def test_generated_docs_are_up_to_date(ep):
    assert (ep.root / "STORYBOARD.md").read_text() == storyboard(ep), f"run: uv run dtak docs {ep.slug[:2]}"
    assert (ep.root / "SCRIPT.md").read_text() == script(ep), f"run: uv run dtak docs {ep.slug[:2]}"
