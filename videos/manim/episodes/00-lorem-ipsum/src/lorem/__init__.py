"""Template episode: Lorem ipsum."""

from pathlib import Path

from dtak_manim.chrome import DtakScene
from dtak_manim.episode import Episode
from lorem import data

EPISODE_DIR = Path(__file__).resolve().parents[2]
EPISODE = Episode.load(EPISODE_DIR, facts=data.FACTS)


class EpisodeScene(DtakScene):
    """Base class of every scene in this episode."""

    episode = EPISODE
