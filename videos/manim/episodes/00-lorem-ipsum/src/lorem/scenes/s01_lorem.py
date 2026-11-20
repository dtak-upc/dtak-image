"""Section 1 -- Lorem ipsum. Beats 1.1 - 1.2 (beats/01_lorem.yaml).

The pattern of every scene:
  * one class per section, with SECTION = <number in the beats YAML>;
  * one method per beat, decorated with @beat("<id>"); the default construct()
    shows the section card and runs the beats in YAML order;
  * each beat leaves the screen clean (clear_content) or hands over on purpose.
"""

from manim import DOWN, LEFT, RIGHT, UP, Create, FadeIn, LaggedStart, MathTex, VGroup, Write

from dtak_manim import theme as th
from dtak_manim.diagram import PlanNode, edge
from dtak_manim.episode import beat
from dtak_manim.table import DbTable, outline
from dtak_manim.text import CodeBlock, bullet_list, callout
from lorem import EpisodeScene, data


class LoremIpsum(EpisodeScene):
    SECTION = 1

    @beat("1.1")
    def lorem(self):
        self.set_title("Lorem ipsum dolor sit amet", "consectetur adipiscing elit")
        bullets = bullet_list(data.ITEMS).to_edge(LEFT, buff=th.MARGIN + 0.2).shift(UP * 0.4)
        for item in bullets:
            self.play(FadeIn(item, shift=RIGHT * 0.2), run_time=0.6)
            self.wait(0.6)
        code = CodeBlock(data.CODE, size=th.SIZE_SMALL).move_to([3.4, 1.2, 0])
        self.play(Write(code), run_time=1.5)
        table = DbTable("lorem", data.TABLE_COLS, data.TABLE_ROWS).next_to(code, DOWN, buff=0.6)
        self.play(FadeIn(table, shift=UP * 0.2))
        self.play(Create(outline(table.row(1), th.UPC_BLUE)))
        self.wait(2)  # elastic: stretched to fit the narration
        self.clear_content()  # waits for the narration, then fades out

    @beat("1.2")
    def dolor(self):
        self.set_title("Consectetur adipiscing")
        root = PlanNode("Lorem", "ipsum = dolor").move_to([-3.0, 1.6, 0])
        left = PlanNode("Sit", color=th.NAVY).move_to([-4.6, 0.0, 0])
        right = PlanNode("Amet", color=th.NAVY).move_to([-1.4, 0.0, 0])
        self.play(FadeIn(root, shift=DOWN * 0.2))
        self.play(LaggedStart(*[Create(edge(root, n)) for n in (left, right)], lag_ratio=0.3),
                  FadeIn(VGroup(left, right), shift=DOWN * 0.2))
        formula = MathTex(r"\sum_{i=1}^{n} i = \frac{n(n+1)}{2}", color=th.NAVY, font_size=48).move_to([3.4, 0.8, 0])
        self.play(Write(formula), run_time=1.5)
        self.wait(1.5)
        note = callout(f"Ut enim ad minim veniam: the answer is <b>{data.ANSWER}</b>.", width=9).to_edge(DOWN, buff=0.8)
        self.play(FadeIn(note, shift=UP * 0.2))
        self.wait(2)
        self.clear_content()
