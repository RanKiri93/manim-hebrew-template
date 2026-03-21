"""
Scene used by the glyph-index preview server. Reads LaTeX from the environment
(see ``server.py``) and draws yellow numeric labels on each leaf path in **LTR**
order (sorted by ``x``), matching how ``MathTex`` / ``resolve_tex_inline_math_glyphs``
order glyphs for animation.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from manim import *

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

expr = os.environ.get("GLYPH_DEBUG_LATEX", r"x")
use_hebrew = os.environ.get("GLYPH_DEBUG_HEBREW") == "1"

if use_hebrew:
    from hebrew_utils import get_hebrew_template

    config.tex_template = get_hebrew_template()

config.background_color = "#1e1e1e"


class GlyphDebugScene(Scene):
    def construct(self):
        mt = MathTex(expr)
        self.add(mt)
        leaves = sorted(
            mt.family_members_with_points(),
            key=lambda m: m.get_center()[0],
        )
        for i, leaf in enumerate(leaves):
            label = Text(str(i), font_size=32, color=YELLOW)
            label.move_to(leaf.get_center() + UP * 0.35)
            self.add(label)
