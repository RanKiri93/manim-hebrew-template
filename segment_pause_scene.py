# -*- coding: utf-8 -*-
r"""
Minimal scene: write the first two ``Tex`` segments (Hebrew + ``\sin``), **wait 3 seconds**, then the rest.

Render::

    manim -pql segment_pause_scene.py SegmentPauseDemo

Uses :func:`hebrew_utils.smart_heb_write_segment` so timing works in both partitioned and collapsed SVG layouts.
"""
from manim import *

from hebrew_utils import get_hebrew_template, smart_heb_write_segment

config.tex_template = get_hebrew_template()

PARTS = (
    "משפט ראשון ",
    r"$\sin{(x)}$",
    " משפט שני ",
    r"$\cos{(x)}$",
)


class SegmentPauseDemo(Scene):
    def construct(self):
        tex = Tex(*PARTS)

        # Color some arguments only when Manim kept one submobject per ``Tex`` string.
        if len(tex.submobjects) == len(tex.tex_strings):
            tex[0].set_color(BLUE_A)
            tex[1].set_color(YELLOW)
            tex[2].set_color(GREEN_A)
            tex[3].set_color(ORANGE)

        self.play(smart_heb_write_segment(tex, segment_index=0, tex_strings_source=PARTS))
        self.play(smart_heb_write_segment(tex, segment_index=1, tex_strings_source=PARTS))
        self.wait(3)
        self.play(smart_heb_write_segment(tex, segment_index=2, tex_strings_source=PARTS))
        self.play(smart_heb_write_segment(tex, segment_index=3, tex_strings_source=PARTS))
        self.wait(0.5)
