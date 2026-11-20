"""Section 0 -- Intro: title slide, the question the video answers, road map.

Beats 0.1 - 0.3 (beats/00_intro.yaml). No section card. Keep this structure in every
video: only the question beat (0.2) is specific to the topic.
"""

from manim import DOWN, LEFT, RIGHT, UP, FadeIn, GrowArrow, LaggedStart, VGroup

from dtak_manim import theme as th
from dtak_manim.diagram import box, link
from dtak_manim.episode import beat
from dtak_manim.table import DbTable
from dtak_manim.text import CodeBlock, markup, title_text
from lorem import EpisodeScene, data


class Intro(EpisodeScene):
    SECTION = 0

    @beat("0.1")
    def title(self):
        self.title_slide()  # long DTAK logo + title + subtitle, from episode.yaml

    @beat("0.2")
    def question(self):
        self.set_title("One input, many questions")
        source = CodeBlock(data.INPUT, language="plain", size=th.SIZE_SMALL)
        engine = box(2.4, 1.6, fill=th.NAVY, stroke=th.NAVY, radius=0.12)
        q = title_text("?", color=th.SOFT_BLUE, size=48).move_to(engine)
        black_box = VGroup(engine, q)
        result = DbTable(None, data.OUTPUT_COLS, data.OUTPUT_ROWS)
        row = VGroup(source, black_box, result).arrange(RIGHT, buff=0.9)
        row.scale_to_fit_width(min(row.width, 13.0)).move_to([0, 0.8, 0])
        a1, a2 = link(source.get_right(), black_box.get_left()), link(black_box.get_right(), result.get_left())
        self.play(FadeIn(source, shift=RIGHT * 0.3))
        self.play(GrowArrow(a1), FadeIn(black_box))
        self.play(GrowArrow(a2), FadeIn(result, shift=RIGHT * 0.3))
        questions = VGroup(*[markup(x) for x in data.QUESTIONS]).arrange(DOWN, aligned_edge=LEFT, buff=0.22).scale(0.9)
        questions.next_to(row, DOWN, buff=0.8).align_to(source, LEFT)
        self.play(LaggedStart(*[FadeIn(x, shift=UP * 0.15) for x in questions], lag_ratio=0.6), run_time=3)
        self.wait(2)
        self.clear_content()

    @beat("0.3")
    def overview(self):
        # groups are optional: [(first section, last section, "label"), ...] draws braces
        self.road_map()


