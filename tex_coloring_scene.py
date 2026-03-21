# -*- coding: utf-8 -*-
r"""
Color **individual** ``Tex`` arguments (Hebrew chunk vs ``$...$`` formula).

Manim's ``tex_to_color_map`` can **crash** (``KeyError``) when XeLaTeX collapses SVG groups — common
with Hebrew. Use :func:`hebrew_utils.set_tex_segment_color` instead; it uses the same segmentation
as :func:`~hebrew_utils.SmartHebWrite`.

**When** ``len(tex.submobjects) == len(tex.tex_strings)`` **you can instead** color ``tex[i]``
directly — a bit faster, same result.

Render::

    manim -pql tex_coloring_scene.py TexColoringDemo
"""
from manim import *

from hebrew_utils import SmartHebWrite, get_hebrew_template, set_tex_segment_color

config.tex_template = get_hebrew_template()

PARTS = (
    "משפט ראשון ",
    r"$\sin{(x)}$",
    " משפט שני ",
    r"$\cos{(x)}$",
)

# One color per segment, same order as PARTS.
SEGMENT_COLORS = [BLUE_A, YELLOW, GREEN_A, ORANGE]


class TexColoringDemo(Scene):
    def construct(self):
        tex = Tex(*PARTS)

        # Robust for collapsed SVG: color by segment index (0 … n-1).
        for i, col in enumerate(SEGMENT_COLORS):
            set_tex_segment_color(
                tex,
                segment_index=i,
                color=col,
                tex_strings_source=PARTS,
            )

        # Optional: equivalent when Manim kept one submobject per argument:
        #   if len(tex.submobjects) == len(tex.tex_strings):
        #       tex[1].set_color(RED)

        self.play(SmartHebWrite(tex, tex_strings_source=PARTS))
        self.wait(1)
