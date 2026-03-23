"""
MCP server for Manim code generation.

Exposes tools for generating Hebrew text lines (SmartHebWrite) and
graph/axes scenes, plus resources with API guides.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

PROJECT_ROOT = Path(__file__).resolve().parent.parent

mcp = FastMCP("manim-assistant")

# ---------------------------------------------------------------------------
#  Resources
# ---------------------------------------------------------------------------

@mcp.resource("manim://hebrew-guide")
def hebrew_guide() -> str:
    """SmartHebWrite API patterns for mixed Hebrew + math text in Manim."""
    path = PROJECT_ROOT / ".cursor" / "rules" / "hebrew-paragraph-wrap.mdc"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return _HEBREW_GUIDE_FALLBACK


@mcp.resource("manim://graph-guide")
def graph_guide() -> str:
    """Axes, graph, and point code patterns for Manim."""
    path = PROJECT_ROOT / ".cursor" / "rules" / "manim-graphs.mdc"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return _GRAPH_GUIDE_FALLBACK


# ---------------------------------------------------------------------------
#  Tool: parse_hebrew_text
# ---------------------------------------------------------------------------

@mcp.tool()
def parse_hebrew_text(text: str) -> str:
    """Parse a mixed Hebrew + inline-math string into typed segments.

    Input: a string like 'תהא $f(x)$ פונקציה רציפה בקטע $[a,b]$.'
    Returns: JSON array of {text, type, index} objects where type is
    'text' or 'math'.  Math segments keep their $...$ delimiters.
    """
    segments: list[dict[str, Any]] = []
    last = 0
    for m in re.finditer(r"\$[^$]+\$", text):
        if m.start() > last:
            segments.append({"text": text[last : m.start()], "type": "text", "index": len(segments)})
        segments.append({"text": m.group(), "type": "math", "index": len(segments)})
        last = m.end()
    if last < len(text):
        segments.append({"text": text[last:], "type": "text", "index": len(segments)})
    return json.dumps(segments, ensure_ascii=False)


# ---------------------------------------------------------------------------
#  Tool: generate_hebrew_line
# ---------------------------------------------------------------------------

@mcp.tool()
def generate_hebrew_line(
    segments: list[dict[str, Any]],
    obj_name: str = "line1",
    font_size: int = 48,
    full_scene: bool = True,
) -> str:
    """Generate Manim Python code for a SmartHebWrite animated line.

    `segments` is an array of objects, each with:
      - text (str): the raw content, e.g. 'תהא ' or '$f(x)$'
      - type (str): 'text' or 'math'
      - color (str, optional): Manim color name, e.g. 'RED'
      - bold (bool, optional)
      - italic (bool, optional)
      - underline (bool, optional)
      - run_time (float, optional): per-segment animation duration

    Returns ready-to-paste Python code.
    """
    parts = [_format_part(seg) for seg in segments]
    color_entries = [(i, s["color"]) for i, s in enumerate(segments) if s.get("color")]
    time_entries = [(i, s["run_time"]) for i, s in enumerate(segments) if s.get("run_time")]
    used_colors = sorted({c for _, c in color_entries})

    def fmt(p: str, indent: str) -> str:
        needs_r = "\\" in p
        q = "'" if '"' in p else '"'
        return f"{indent}{'r' if needs_r else ''}{q}{p}{q},"

    colors_kw = "{" + ", ".join(f"{i}: {c}" for i, c in color_entries) + "}" if color_entries else ""
    times_kw = "{" + ", ".join(f"{i}: {t}" for i, t in time_entries) + "}" if time_entries else ""
    fs_arg = f", font_size={font_size}" if font_size != 48 else ""

    if full_scene:
        mi = "Scene, Tex, config"
        if used_colors:
            mi += ", " + ", ".join(used_colors)
        lines = [
            f"from manim import {mi}",
            "from hebrew_utils import SmartHebWrite, get_hebrew_template",
            "",
            "config.tex_template = get_hebrew_template()",
            "",
            "",
            "class TestScene(Scene):",
            "    def construct(self):",
            f"        {obj_name}_parts = (",
        ]
        for p in parts:
            lines.append(fmt(p, "            "))
        lines.append("        )")
        lines.append(f"        {obj_name} = Tex(*{obj_name}_parts{fs_arg})")
        lines.append(f"        self.play(SmartHebWrite(")
        lines.append(f"            {obj_name},")
        lines.append(f"            tex_strings_source={obj_name}_parts,")
        if colors_kw:
            lines.append(f"            colors={colors_kw},")
        if times_kw:
            lines.append(f"            run_times={times_kw},")
        lines.append("        ))")
        lines.append("        self.wait(1)")
        lines.append("")
        lines.append("")
        lines.append("# Run with:")
        lines.append("#   manim render -pql <filename>.py TestScene")
    else:
        mi = "Scene, Tex, config"
        if used_colors:
            mi += ", " + ", ".join(used_colors)
        lines = [
            f"from manim import {mi}",
            "from hebrew_utils import SmartHebWrite, get_hebrew_template",
            "",
            "config.tex_template = get_hebrew_template()",
            "",
            f"{obj_name}_parts = (",
        ]
        for p in parts:
            lines.append(fmt(p, "    "))
        lines.append(")")
        lines.append(f"{obj_name} = Tex(*{obj_name}_parts{fs_arg})")
        lines.append(f"self.play(SmartHebWrite(")
        lines.append(f"    {obj_name},")
        lines.append(f"    tex_strings_source={obj_name}_parts,")
        if colors_kw:
            lines.append(f"    colors={colors_kw},")
        if times_kw:
            lines.append(f"    run_times={times_kw},")
        lines.append("))")

    return "\n".join(lines)


def _format_part(seg: dict[str, Any]) -> str:
    if seg["type"] == "math":
        inner = seg["text"][1:-1]
        if seg.get("bold"):
            inner = f"\\mathbf{{{inner}}}"
        if seg.get("underline"):
            return f"\\underline{{${inner}$}}"
        return f"${inner}$"
    t = seg["text"]
    if seg.get("bold"):
        t = f"\\textbf{{{t}}}"
    if seg.get("italic"):
        t = f"\\textit{{{t}}}"
    if seg.get("underline"):
        t = f"\\underline{{{t}}}"
    return t


# ---------------------------------------------------------------------------
#  Tool: generate_graph_scene
# ---------------------------------------------------------------------------

@mcp.tool()
def generate_graph_scene(axes: list[dict[str, Any]]) -> str:
    """Generate a complete Manim scene with Axes, plotted functions, and points.

    `axes` is an array of objects, each with:
      - name (str): variable name, e.g. 'axes1'
      - x_range (list): [min, max, step], e.g. [-5, 5, 1]
      - y_range (list): [min, max, step]
      - x_length (float): width in manim units
      - y_length (float): height in manim units
      - position (list, optional): [x, y] shift from origin, default [0, 0]
      - include_numbers (bool, optional): default True
      - include_tip (bool, optional): default True
      - x_label (str, optional): default 'x'
      - y_label (str, optional): default 'y'
      - animation (str, optional): 'Create', 'Write', or 'FadeIn', default 'Create'
      - run_time (float, optional): animation duration
      - functions (list, optional): [{expr, color, x_min, x_max}]
      - points (list, optional): [{x, y, color, label}]

    Returns a full runnable Manim scene.
    """
    I = "        "
    code_lines = [
        "from manim import *",
        "import numpy as np",
        "",
        "",
        "class GraphScene(Scene):",
        "    def construct(self):",
    ]

    for ai, a in enumerate(axes):
        nm = a.get("name") or f"axes{ai + 1}"
        xr = a.get("x_range", [-5, 5, 1])
        yr = a.get("y_range", [-3, 3, 1])
        xl = a.get("x_length", 8)
        yl = a.get("y_length", 5)
        pos = a.get("position", [0, 0])
        nums = a.get("include_numbers", True)
        tips = a.get("include_tip", True)
        x_label = a.get("x_label", "x")
        y_label = a.get("y_label", "y")
        anim = a.get("animation", "Create")
        rt = a.get("run_time")
        funcs = a.get("functions", [])
        pts = a.get("points", [])

        code_lines.append(f"{I}{nm} = Axes(")
        code_lines.append(f"{I}    x_range=[{xr[0]}, {xr[1]}, {xr[2]}],")
        code_lines.append(f"{I}    y_range=[{yr[0]}, {yr[1]}, {yr[2]}],")
        code_lines.append(f"{I}    x_length={xl},")
        code_lines.append(f"{I}    y_length={yl},")
        cfg = []
        if nums:
            cfg.append('"include_numbers": True')
        if tips:
            cfg.append('"include_tip": True')
        if cfg:
            code_lines.append(f'{I}    axis_config={{{", ".join(cfg)}}},')
        shift = _fmt_shift(pos[0], pos[1]) if (pos[0] or pos[1]) else ""
        code_lines.append(f"{I}){shift}")

        if x_label or y_label:
            xl_s = f'"{x_label}"' if x_label else '""'
            yl_s = f'"{y_label}"' if y_label else '""'
            code_lines.append(f"{I}{nm}_labels = {nm}.get_axis_labels(x_label={xl_s}, y_label={yl_s})")

        for fi, f in enumerate(funcs):
            fname = f"{nm}_f{fi + 1}"
            expr = f.get("expr", "x**2")
            color = f.get("color", "BLUE")
            x_min, x_max = f.get("x_min"), f.get("x_max")
            xr_arg = f", x_range=[{x_min if x_min is not None else xr[0]}, {x_max if x_max is not None else xr[1]}]" if x_min is not None or x_max is not None else ""
            code_lines.append(f"{I}{fname} = {nm}.plot(lambda x: {expr}{xr_arg}, color={color})")

        for pi, p in enumerate(pts):
            pname = f"{nm}_p{pi + 1}"
            px, py = p.get("x", 0), p.get("y", 0)
            color = p.get("color", "RED")
            code_lines.append(f"{I}{pname} = Dot({nm}.c2p({px}, {py}), color={color})")
            label = p.get("label", "")
            if label:
                code_lines.append(f'{I}{pname}_label = MathTex("{label}").scale(0.6).next_to({pname}, UR, buff=0.1)')

        code_lines.append("")

    # Animations
    for ai, a in enumerate(axes):
        nm = a.get("name") or f"axes{ai + 1}"
        anim = a.get("animation", "Create")
        rt = a.get("run_time")
        x_label = a.get("x_label", "x")
        y_label = a.get("y_label", "y")
        funcs = a.get("functions", [])
        pts = a.get("points", [])

        play_args = f"{anim}({nm})"
        if x_label or y_label:
            play_args += f", Write({nm}_labels)"
        rt_arg = f", run_time={rt}" if rt else ""
        code_lines.append(f"{I}self.play({play_args}{rt_arg})")

        for fi in range(len(funcs)):
            code_lines.append(f"{I}self.play(Create({nm}_f{fi + 1}), run_time=2)")

        for pi, p in enumerate(pts):
            pname = f"{nm}_p{pi + 1}"
            if p.get("label"):
                code_lines.append(f"{I}self.play(FadeIn({pname}), Write({pname}_label))")
            else:
                code_lines.append(f"{I}self.play(FadeIn({pname}))")

    code_lines.append(f"{I}self.wait(1)")
    return "\n".join(code_lines)


def _fmt_shift(cx: float, cy: float) -> str:
    parts = []
    if cx > 0:
        parts.append(f"RIGHT * {cx}")
    elif cx < 0:
        parts.append(f"LEFT * {abs(cx)}")
    if cy > 0:
        parts.append(f"UP * {cy}")
    elif cy < 0:
        parts.append(f"DOWN * {abs(cy)}")
    return f".shift({' + '.join(parts)})" if parts else ""


# ---------------------------------------------------------------------------
#  Fallback resource content (used if rule files are missing)
# ---------------------------------------------------------------------------

_HEBREW_GUIDE_FALLBACK = """\
# Hebrew + Math — SmartHebWrite

## Stack
- Manim Community (Tex, MathTex), XeLaTeX + Hebrew template from hebrew_utils.get_hebrew_template().
- At the top of every scene module: config.tex_template = get_hebrew_template().

## Mixed Hebrew + inline math in one Tex
- Pass one Python argument per segment. Each formula must be a single standalone "$...$" string.
- Pass the same tuple into SmartHebWrite as tex_strings_source=parts.

## Animations (hebrew_utils)
- Full line: SmartHebWrite(tex, tex_strings_source=parts)
- Per-segment colors: colors={1: RED, 3: BLUE}
- Per-segment timing: run_times={1: 2.0}
- Lower-level: partition_segments(tex, list(parts)) returns {index: VGroup}

## Multi-line layout
1. Each line is a separate Tex(...) + SmartHebWrite(...).
2. VGroup(*lines).arrange(DOWN, aligned_edge=RIGHT)
"""

_GRAPH_GUIDE_FALLBACK = """\
# Manim Graphs & Axes

## Creating Axes
axes1 = Axes(x_range=[-5,5,1], y_range=[-3,3,1], x_length=8, y_length=5,
             axis_config={"include_numbers": True, "include_tip": True})
axes1_labels = axes1.get_axis_labels(x_label="x", y_label="y")

## Functions and points
graph = axes1.plot(lambda x: np.sin(x), color=BLUE)
dot = Dot(axes1.c2p(2, 1), color=RED)

## Animation order
1. self.play(Create(axes), Write(axes_labels))
2. self.play(Create(graph), run_time=2)
3. self.play(FadeIn(dot))
"""

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run()
