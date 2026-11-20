"""Numbers and data shown on screen and spoken in the narration.

In a real episode this module parses them from a captured output (see
dtak_manim.transcript) so that screen, voice and reality cannot disagree.
Here they are constants, to keep the template small.
"""

ITEMS = ["Lorem ipsum dolor", "Sit amet consectetur", "Adipiscing elit sed"]
TABLE_COLS = ["id", "lorem", "ipsum"]
TABLE_ROWS = [(1, "dolor", "sit"), (2, "amet", "elit"), (3, "sed", "do")]
CODE = """\
SELECT lorem, ipsum
FROM dolor
WHERE sit = 'amet';"""
ANSWER = 42

# the opening question (beat 0.2) and the closing takeaways (beat 2.1)
INPUT = "lorem ipsum"
OUTPUT_COLS = ["dolor", "sit"]
OUTPUT_ROWS = [("amet", "1"), ("elit", "2")]
QUESTIONS = [
    "What <b>is</b> lorem?",
    "What does <tt>ipsum</tt> <b>mean</b>?",
    "<b>Which algorithm</b> turns one into the other?",
]
TAKEAWAYS = [
    "Lorem ipsum is <b>dolor sit amet</b>.",
    "Consectetur <b>adipiscing</b> elit, sed do eiusmod tempor.",
    f"The answer is <b>{ANSWER}</b>.",
]

# {name} placeholders in beats/*.yaml
FACTS = {
    "n_items": len(ITEMS),
    "answer": ANSWER,
    "n_questions": len(QUESTIONS),
    "n_takeaways": len(TAKEAWAYS),
}
