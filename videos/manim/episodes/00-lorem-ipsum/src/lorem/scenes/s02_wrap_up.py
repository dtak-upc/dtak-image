"""Section 2 -- Wrap-up: takeaways and the closing card. Beats 2.1 - 2.2.

Keep this as the last section of every video.
"""

from dtak_manim.episode import beat
from lorem import EpisodeScene, data


class WrapUp(EpisodeScene):
    SECTION = 2

    @beat("2.1")
    def summary(self):
        self.takeaways(data.TAKEAWAYS)

    @beat("2.2")
    def closing(self):
        self.closing_card()
