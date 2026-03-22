from manim import Scene, Tex, config, YELLOW
from hebrew_utils import SmartHebWrite, get_hebrew_template

config.tex_template = get_hebrew_template()


class TestScene(Scene):
    def construct(self):
        line1_parts = (
            "תהא ",
            "$f(x)$",
            " פונקציה רציפה בקטע הסגור ",
            "$[a,b]$",
            " וגזירה בקטע הפתוח ",
            "$(a,b)$",
            ".",
        )
        line1 = Tex(*line1_parts, font_size=36)
        self.play(SmartHebWrite(
            line1,
            tex_strings_source=line1_parts,
            colors={1: YELLOW, 3: YELLOW, 5: YELLOW},
            run_times={2: 1.25},
        ))
        self.wait(1)


# Run with:
#   manim render -pql <filename>.py TestScene
