"""
Axes / NumberPlane codegen — mirrors tools/tex_line_codegen/index.html (axes tab).
Single source of truth for MCP; keep in sync when the HTML generator changes.
"""

from __future__ import annotations

import math
import re
from typing import Any

AXES_GRAPH_COLOR = "#d4a84b"
AXES_POINT_COLOR = "#e55555"
DEFAULT_AXES_PLAY_RT = 1.0
DEFAULT_AXES_WAIT_AFTER = 0.5
DEFAULT_OBJ_PLAY_RT = 1.0
DEFAULT_OBJ_WAIT_AFTER = 0.5


def _format_py_float(x: float) -> str:
    if not math.isfinite(x):
        raise ValueError("non-finite number")
    if abs(x - round(x)) < 1e-12:
        return str(int(round(x)))
    return f"{x:.12g}".rstrip("0").rstrip(".") if "." in f"{x:.12g}" else f"{x:.12g}"


def py_literal_num(n: float | int) -> str:
    if isinstance(n, bool):
        raise TypeError("bool not allowed")
    if isinstance(n, int):
        return str(n)
    if isinstance(n, float):
        if n.is_integer():
            return str(int(n))
        return _format_py_float(n)
    raise TypeError(f"expected number, got {type(n)}")


def parse_axes_range_tuple(s: str) -> tuple[float, float, float] | None:
    parts = [p.strip() for p in str(s).split(",") if p.strip()]
    if len(parts) != 3:
        return None
    nums = []
    for p in parts:
        try:
            nums.append(float(p))
        except ValueError:
            return None
    if any(not math.isfinite(x) for x in nums):
        return None
    return (nums[0], nums[1], nums[2])


def py_list3(arr: tuple[float, float, float]) -> str:
    return f"[{', '.join(py_literal_num(x) for x in arr)}]"


_HEX6 = re.compile(r"^#[0-9A-Fa-f]{6}$")
_HEX3 = re.compile(r"^#[0-9A-Fa-f]{3}$")


def normalize_hex_input(v: str | None) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s.startswith("#"):
        s = "#" + s
    if _HEX6.match(s):
        return s.lower()
    if _HEX3.match(s):
        r, g, b = s[1], s[2], s[3]
        return f"#{r}{r}{g}{g}{b}{b}".lower()
    return None


def _normalize_objects(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, o in enumerate(raw):
        t = o.get("type")
        if t == "graph":
            expr = (o.get("expr") or "").strip()
            if not expr:
                raise ValueError("graph object requires non-empty expr (e.g. x**2, np.sin(x))")
            raw_hex = o.get("color_hex")
            ch = normalize_hex_input(raw_hex) if raw_hex else None
            if not ch:
                ch = AXES_GRAPH_COLOR
            pr = float(o.get("play_run_time", DEFAULT_OBJ_PLAY_RT))
            wa = float(o.get("wait_after", DEFAULT_OBJ_WAIT_AFTER))
            if not math.isfinite(pr) or pr <= 0:
                pr = DEFAULT_OBJ_PLAY_RT
            if not math.isfinite(wa) or wa < 0:
                wa = DEFAULT_OBJ_WAIT_AFTER
            par = bool(o.get("parallel_with_previous")) and i > 0
            out.append(
                {
                    "type": "graph",
                    "expr": expr,
                    "color_hex": ch,
                    "play_rt": pr,
                    "wait_after": wa,
                    "parallel_with_prev": par,
                }
            )
        elif t == "point":
            x = float(o["x"])
            y = float(o["y"])
            if not math.isfinite(x) or not math.isfinite(y):
                raise ValueError("point requires finite x and y")
            raw_hex = o.get("color_hex")
            ch = normalize_hex_input(raw_hex) if raw_hex else None
            if not ch:
                ch = AXES_POINT_COLOR
            pr = float(o.get("play_run_time", DEFAULT_OBJ_PLAY_RT))
            wa = float(o.get("wait_after", DEFAULT_OBJ_WAIT_AFTER))
            if not math.isfinite(pr) or pr <= 0:
                pr = DEFAULT_OBJ_PLAY_RT
            if not math.isfinite(wa) or wa < 0:
                wa = DEFAULT_OBJ_WAIT_AFTER
            par = bool(o.get("parallel_with_previous")) and i > 0
            out.append(
                {
                    "type": "point",
                    "x_py": py_literal_num(x),
                    "y_py": py_literal_num(y),
                    "color_hex": ch,
                    "play_rt": pr,
                    "wait_after": wa,
                    "parallel_with_prev": par,
                }
            )
        else:
            raise ValueError(f'object type must be "graph" or "point", got {t!r}')
    return out


def _build_axes_objects_snippet(var_name: str, objects: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    lines: list[str] = []
    meta: list[dict[str, Any]] = []
    gi = pi = 0
    for i, o in enumerate(objects):
        pr = o.get("play_rt", DEFAULT_OBJ_PLAY_RT)
        wa = o.get("wait_after", DEFAULT_OBJ_WAIT_AFTER)
        parallel_with_prev = i > 0 and bool(o.get("parallel_with_prev"))
        if o["type"] == "graph":
            col = o.get("color_hex") or AXES_GRAPH_COLOR
            fn = f"f{gi}"
            gn = f"graph{gi}"
            lines.append(f"def {fn}(x):")
            lines.append(f"    return {o['expr']}")
            lines.append(f'{gn} = {var_name}.plot({fn}, color="{col}")')
            meta.append({"name": gn, "play_rt": pr, "wait_after": wa, "parallel_with_prev": parallel_with_prev})
            gi += 1
        else:
            pcol = o.get("color_hex") or AXES_POINT_COLOR
            dn = f"dot{pi}"
            lines.append(
                f'{dn} = Dot({var_name}.c2p({o["x_py"]}, {o["y_py"]}), color="{pcol}", radius=0.08)'
            )
            meta.append({"name": dn, "play_rt": pr, "wait_after": wa, "parallel_with_prev": parallel_with_prev})
            pi += 1

    object_anim_steps: list[dict[str, Any]] = []
    idx = 0
    while idx < len(meta):
        chunk = [meta[idx]]
        idx += 1
        while idx < len(meta) and meta[idx]["parallel_with_prev"]:
            chunk.append(meta[idx])
            idx += 1
        rt = max(c["play_rt"] for c in chunk)
        wait_after = chunk[-1]["wait_after"]
        creates = ", ".join(f"Create({c['name']})" for c in chunk)
        object_anim_steps.append(
            {
                "play_line": f"self.play({creates}, run_time={py_literal_num(rt)})",
                "wait_after": wait_after,
            }
        )

    extra = "\n\n" + "\n".join(lines) if lines else ""
    return extra, object_anim_steps


def generate_axes_scene(params: dict[str, Any]) -> dict[str, str]:
    """
    Build the three copy-paste blocks (same semantics as the HTML tool).

    params keys:
      axes_kind: "Axes" | "NumberPlane"
      x_range, y_range: "min, max, step" strings
      x_length, y_length: positive floats
      include_tip: bool (default True)
      use_hebrew_template: bool (default False)
      axes_play_run_time, axes_wait_after: floats
      objects: list of graph/point dicts
    """
    kind = params.get("axes_kind", "Axes")
    if kind not in ("Axes", "NumberPlane"):
        raise ValueError('axes_kind must be "Axes" or "NumberPlane"')

    xr = parse_axes_range_tuple(str(params.get("x_range", "-7, 7, 1")))
    yr = parse_axes_range_tuple(str(params.get("y_range", "-4, 4, 1")))
    if not xr or not yr:
        raise ValueError("x_range and y_range must be three comma-separated numbers (min, max, step)")

    xl = float(params.get("x_length", 6))
    yl = float(params.get("y_length", 4))
    if not math.isfinite(xl) or xl <= 0 or not math.isfinite(yl) or yl <= 0:
        raise ValueError("x_length and y_length must be positive numbers")

    tips = bool(params.get("include_tip", True))
    use_heb = bool(params.get("use_hebrew_template", False))

    axes_play = float(params.get("axes_play_run_time", DEFAULT_AXES_PLAY_RT))
    axes_wait = float(params.get("axes_wait_after", DEFAULT_AXES_WAIT_AFTER))
    if not math.isfinite(axes_play) or axes_play <= 0:
        axes_play = DEFAULT_AXES_PLAY_RT
    if not math.isfinite(axes_wait) or axes_wait < 0:
        axes_wait = DEFAULT_AXES_WAIT_AFTER

    raw_objects = params.get("objects") or []
    if not isinstance(raw_objects, list):
        raise ValueError("objects must be a list")
    objects = _normalize_objects(raw_objects)

    var_name = "plane" if kind == "NumberPlane" else "axes"
    xr_s = py_list3(xr)
    yr_s = py_list3(yr)
    xl_s = py_literal_num(xl)
    yl_s = py_literal_num(yl)
    tip_py = "True" if tips else "False"

    body_lines = [
        f"{var_name} = {kind}(",
        f"    x_range={xr_s},",
        f"    y_range={yr_s},",
        f"    x_length={xl_s},",
        f"    y_length={yl_s},",
        f'    axis_config={{"include_tip": {tip_py}}},',
        ")",
    ]
    graph_extra, object_anim_steps = _build_axes_objects_snippet(var_name, objects)
    obj_block = "\n".join(body_lines) + graph_extra

    ind8 = "        "
    obj_in_construct = "\n".join(ind8 + ln for ln in body_lines)
    graph_in_construct = ""
    if graph_extra.strip():
        for block in graph_extra.strip().split("\n\n"):
            if not block.strip():
                continue
            graph_in_construct += (
                "\n\n" + "\n".join(ind8 + ln for ln in block.split("\n"))
            )

    anim_parts: list[str] = [
        f"self.play(Create({var_name}), run_time={py_literal_num(axes_play)})"
    ]
    if axes_wait > 0:
        anim_parts.append(f"self.wait({py_literal_num(axes_wait)})")
    for s in object_anim_steps:
        anim_parts.append(s["play_line"])
        wa = s["wait_after"]
        if wa and float(wa) > 0:
            anim_parts.append(f"self.wait({py_literal_num(float(wa))})")
    anim_line = "\n".join(anim_parts)

    has_graph = any(o["type"] == "graph" for o in objects)
    has_point = any(o["type"] == "point" for o in objects)
    manim_names = ["Scene", kind, "Create"]
    if has_point:
        manim_names.append("Dot")
    if use_heb:
        manim_names.append("config")
    manim_import = f"from manim import {', '.join(manim_names)}"
    np_line = "import numpy as np\n\n" if has_graph else ""

    full = manim_import + "\n\n" + np_line
    if use_heb:
        full += "from hebrew_utils import get_hebrew_template\n\n"
        full += "config.tex_template = get_hebrew_template()\n\n\n"
    full += "class AxesScene(Scene):\n"
    full += "    def construct(self):\n"
    full += obj_in_construct
    if graph_in_construct:
        full += graph_in_construct
    full += "\n" + ind8 + anim_line.replace("\n", "\n" + ind8)

    return {
        "snippet_axes_and_objects": obj_block,
        "full_python_module": full,
        "animation_only": anim_line,
    }
