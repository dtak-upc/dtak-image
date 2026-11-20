"""DTAK visual identity for manim.

Single source of truth for colors, fonts and sizes used by every scene.
Values come from https://github.com/dtak-upc/dtak-image (README, "Color" and
"Typography"). Scenes must never use raw hex values: import names from here.
"""

from __future__ import annotations

from pathlib import Path

import manimpango

ASSETS = Path(__file__).resolve().parent / "assets"  # vendored DTAK/UPC logos and OFL fonts

# ---------------------------------------------------------------------------
# Colors (brand)
# ---------------------------------------------------------------------------
UPC_BLUE = "#0076CF"  # accent: highlights, keywords, active element
NAVY = "#0A2A4F"  # titles, dark (section) backgrounds
SOFT_BLUE = "#66ADE2"  # accent on dark backgrounds; secondary fills
EDGE_NAVY = "#8494A7"  # lines, borders, arrows (graphics only, never text)
WHITE = "#FFFFFF"
TEXT = "#1C2430"  # body text (from the slide templates)
MUTED = "#6B7785"  # secondary text, captions

# Tints (color at a given opacity over white), same recipe as the brand tints.
BG = WHITE  # light background used for most of the video
BLUE_TINT = "#E5F1FA"  # UPC blue at 10 %: header cells, code background
BLUE_TINT_2 = "#CCE4F5"  # UPC blue at 20 %: highlighted cells
NAVY_TINT = "#E7EAED"  # navy at 10 %: neutral panels

# Functional colors (NOT part of the brand). Used only where meaning requires
# it: a constraint violation (error) or a successful match (ok).
ERROR = "#C62828"
ERROR_TINT = "#FBE9E9"
OK = "#2E7D32"
OK_TINT = "#E8F3E9"

# ---------------------------------------------------------------------------
# Fonts (bundled in assets/fonts, SIL OFL)
# ---------------------------------------------------------------------------
TITLE_FONT = "Montserrat"  # Montserrat Bold: first-level titles only
BODY_FONT = "Roboto"  # everything else
MONO_FONT = "Roboto Mono"  # code, table values, EXPLAIN output

for _ttf in sorted((ASSETS / "fonts").glob("*.ttf")):
    manimpango.register_font(str(_ttf))

# Font sizes (manim font_size units; frame is 14.2 x 8 units)
SIZE_TITLE = 40
SIZE_SUBTITLE = 28
SIZE_BODY = 26
SIZE_SMALL = 20
SIZE_TINY = 16
SIZE_CODE = 19

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
FRAME_W = 14.222
FRAME_H = 8.0
ACCENT_BAR_H = 0.08  # thin UPC-blue bar on top of light frames
LOGO_H = 0.42  # footer marks height (UPC and dtak_short: same height, equal footing)
FOOTER_BOTTOM = 0.22  # gap between the frame bottom and the footer marks
FOOTER_GAP = 0.3  # gap between each mark and the rule
MARGIN = 0.45  # outer margin (left/right/bottom)
TITLE_Y = 3.35  # baseline area of the slide title
CONTENT_TOP = 2.75  # content must stay below this y
CONTENT_BOTTOM = -3.2  # ... and above this y (footer area below)

LOGO_LIGHT = ASSETS / "logo" / "dtak_short.svg"
LOGO_DARK = ASSETS / "logo" / "dtak_short_dark.svg"
LOGO_LONG_DARK = ASSETS / "logo" / "dtak_long_dark.svg"
LOGO_LONG = ASSETS / "logo" / "dtak_long.svg"
# UPC mark, copied from dtak-image/slides/revealjs/theme/logos (light / dark frames)
UPC_LOGO = ASSETS / "logo" / "upc-barcelonatech.svg"
UPC_LOGO_DARK = ASSETS / "logo" / "upc-barcelonatech-neg.svg"
