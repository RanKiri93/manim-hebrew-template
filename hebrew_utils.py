"""
SmartHebWrite — Write animation for mixed Hebrew + inline-math ``Tex`` lines.

Animates each ``tex_strings`` segment in **source order** (0, 1, 2, …):
  - Hebrew / text segments → glyphs drawn **Right-to-Left**
  - Math ``$...$`` segments → glyphs drawn **Left-to-Right**

Works even when XeLaTeX collapses SVG groups (common with Hebrew) by using
**spatial fingerprinting**: each ``$...$`` formula is compiled as a standalone
``MathTex`` to obtain a reference glyph count + relative spacing, then the
best-matching window of glyphs in the full ``Tex`` is identified.  Everything
left over is Hebrew text, partitioned among text segments by the largest
x-gaps (RTL reading order).

Usage::

    tex_parts = ("תהא ", r"$f(x)$", " פונקציה")
    text = Tex(*tex_parts, tex_template=get_hebrew_template())
    self.play(SmartHebWrite(text, tex_strings_source=tex_parts))
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from manim import (
    AnimationGroup,
    MathTex,
    Tex,
    TexTemplate,
    VGroup,
    Wait,
    Write,
    config,
)

# ---------------------------------------------------------------------------
#  Hebrew TeX template
# ---------------------------------------------------------------------------

_template_cache: TexTemplate | None = None


def get_hebrew_template(font_name: str = "David Libre") -> TexTemplate:
    """XeLaTeX + Polyglossia Hebrew template (mirrors the project's working setup)."""
    global _template_cache
    if _template_cache is not None:
        return _template_cache

    tpl = TexTemplate(tex_compiler="xelatex", output_format=".pdf")
    tpl.add_to_preamble(r"\usepackage{polyglossia}")
    tpl.add_to_preamble(r"\setdefaultlanguage{hebrew}")
    tpl.add_to_preamble(r"\setotherlanguage{english}")
    tpl.add_to_preamble(rf"\newfontfamily\hebrewfont[Script=Hebrew]{{{font_name}}}")
    tpl.add_to_preamble(rf"\setmainfont{{{font_name}}}")
    tpl.add_to_preamble(
        "\\AtBeginDocument{%\n"
        "\\everymath{\\textstyle}%\n"
        "\\DeclareMathSizes{10}{8}{6}{5}\n"
        "}"
    )
    _template_cache = tpl
    return tpl


# ---------------------------------------------------------------------------
#  Detection helpers
# ---------------------------------------------------------------------------

_INLINE_MATH = re.compile(r"^\s*\$(.+)\$\s*$", re.DOTALL)


def _is_math(s: str) -> bool:
    return _INLINE_MATH.match(s) is not None


def _math_inner(s: str) -> str | None:
    m = _INLINE_MATH.match(s)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
#  Spatial fingerprinting — match math glyphs inside the combined Tex
# ---------------------------------------------------------------------------

def _norm_gaps(xs: list[float]) -> list[float]:
    if len(xs) < 2:
        return []
    gaps = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
    total = sum(abs(g) for g in gaps) or 1.0
    return [g / total for g in gaps]


def _best_window(candidates: list, ref_leaves: list) -> list:
    """
    Find a contiguous window of ``len(ref_leaves)`` glyphs within *candidates*
    (sorted by x) whose normalized inter-glyph gaps best match those of the
    standalone ``MathTex`` reference.
    """
    n = len(ref_leaves)
    if n == 0:
        return []
    if len(candidates) < n:
        return []

    if n == 1:
        ref = ref_leaves[0]
        rw = float(ref.get_width() or 0.01)
        rh = float(ref.get_height() or 0.01)
        return [min(candidates, key=lambda g: abs(
            (float(g.get_width() or 0.01) / float(g.get_height() or 0.01))
            - rw / rh
        ))]

    ref_xs = [m.get_center()[0] for m in ref_leaves]
    ref_g = _norm_gaps(ref_xs)

    best_score = float("inf")
    best: list = []
    for start in range(len(candidates) - n + 1):
        window = candidates[start : start + n]
        w_xs = [m.get_center()[0] for m in window]
        w_g = _norm_gaps(w_xs)
        if len(w_g) != len(ref_g):
            continue
        score = sum((a - b) ** 2 for a, b in zip(ref_g, w_g))
        if score < best_score:
            best_score = score
            best = window
    return best


# ---------------------------------------------------------------------------
#  Glyph partitioning (the hard part)
# ---------------------------------------------------------------------------

def _split_rtl(leaves: list, k: int) -> list[list]:
    """
    Split *leaves* into *k* groups by the largest x-gaps, ordered from
    rightmost cluster to leftmost (RTL reading order).
    """
    if k <= 0:
        return []
    if not leaves:
        return [[] for _ in range(k)]
    ordered = sorted(leaves, key=lambda m: m.get_center()[0], reverse=True)
    if k == 1:
        return [ordered]
    if len(ordered) <= k:
        out = [[g] for g in ordered]
        while len(out) < k:
            out.append([])
        return out
    gaps = [
        (ordered[i].get_center()[0] - ordered[i + 1].get_center()[0], i)
        for i in range(len(ordered) - 1)
    ]
    gaps.sort(key=lambda t: t[0], reverse=True)
    cuts = sorted(g[1] for g in gaps[: k - 1])
    groups: list[list] = []
    start = 0
    for cut in cuts:
        groups.append(ordered[start : cut + 1])
        start = cut + 1
    groups.append(ordered[start:])
    return groups


def _fix_invisible_glyph(glyph) -> None:
    """XeLaTeX SVG paths sometimes arrive with fill=0, stroke=0 → invisible."""
    try:
        if len(glyph.get_points()) < 2:
            return
    except Exception:
        return
    fo = float(glyph.get_fill_opacity() or 0)
    sw = float(glyph.get_stroke_width() or 0)
    if fo < 1e-6 and sw < 1e-6:
        if float(glyph.get_height() or 0) <= 1e-5:
            glyph.set_stroke(color=glyph.get_color(), width=2.0)
        else:
            glyph.set_fill(color=glyph.get_color(), opacity=1.0)


def partition_segments(
    tex: Tex,
    strings: list[str],
    tex_template: TexTemplate | None = None,
) -> dict[int, VGroup]:
    """
    Returns ``{segment_index: VGroup}``.

    Math segments' glyphs are sorted LTR (ascending x).
    Text segments' glyphs are sorted RTL (descending x).

    The VGroups are used as animation targets for ``Write``.
    """
    n = len(strings)
    math_ixs = [i for i in range(n) if _is_math(strings[i])]
    text_ixs = [i for i in range(n) if not _is_math(strings[i])]

    # --- Easy path: Manim preserved per-argument submobjects ---
    if len(tex.submobjects) == n:
        result: dict[int, VGroup] = {}
        for i in range(n):
            sub = tex[i]
            glyphs = sub.family_members_with_points()
            for g in glyphs:
                _fix_invisible_glyph(g)
            if _is_math(strings[i]):
                glyphs.sort(key=lambda m: m.get_center()[0])
            else:
                glyphs.sort(key=lambda m: m.get_center()[0], reverse=True)
                for g in glyphs:
                    g.reverse_direction()
            vg = VGroup(*glyphs)
            result[i] = vg
        return result

    # --- Hard path: collapsed SVG — fingerprint each math formula ---
    tpl = tex_template or getattr(tex, "tex_template", None) or get_hebrew_template()
    all_leaves = tex.family_members_with_points()
    all_sorted = sorted(all_leaves, key=lambda m: m.get_center()[0])

    math_ids: set[int] = set()
    math_glyphs: dict[int, list] = {}

    def _ref_glyph_count(i: int) -> int:
        inner = _math_inner(strings[i])
        ref = MathTex(inner, tex_template=tpl)
        return len(ref.family_members_with_points())

    for i in sorted(math_ixs, key=_ref_glyph_count, reverse=True):
        inner = _math_inner(strings[i])
        ref = MathTex(inner, tex_template=tpl)
        ref_leaves = sorted(
            ref.family_members_with_points(), key=lambda m: m.get_center()[0]
        )
        available = [g for g in all_sorted if id(g) not in math_ids]
        matched = _best_window(available, ref_leaves)
        matched.sort(key=lambda m: m.get_center()[0])
        math_glyphs[i] = matched
        math_ids.update(id(g) for g in matched)

    hebrew_leaves = [g for g in all_leaves if id(g) not in math_ids]
    groups = _split_rtl(hebrew_leaves, len(text_ixs))

    result: dict[int, VGroup] = {}
    for j, idx in enumerate(sorted(text_ixs)):
        glyphs = groups[j] if j < len(groups) else []
        glyphs.sort(key=lambda m: m.get_center()[0], reverse=True)
        for g in glyphs:
            _fix_invisible_glyph(g)
            g.reverse_direction()
        result[idx] = VGroup(*glyphs)

    for i in math_ixs:
        for g in math_glyphs[i]:
            _fix_invisible_glyph(g)
        result[i] = VGroup(*math_glyphs[i])

    return result


# ---------------------------------------------------------------------------
#  The animation
# ---------------------------------------------------------------------------

_MIN_RUN_TIME = 0.07


def _resolve_per_segment(
    spec: Sequence | dict | None,
    n: int,
) -> dict:
    """Normalize a per-segment spec (sequence or dict) into ``{index: value}``."""
    if spec is None:
        return {}
    if isinstance(spec, dict):
        return spec
    return {i: v for i, v in enumerate(spec) if v is not None}


def SmartHebWrite(
    tex: Tex,
    *,
    tex_strings_source: Sequence[str] | None = None,
    tex_template: TexTemplate | None = None,
    segment_lag: float = 0.85,
    hebrew_letter_lag: float = 0.55,
    math_glyph_lag: float = 0.09,
    colors: Sequence | dict | None = None,
    run_times: Sequence[float | None] | dict[int, float] | None = None,
    **write_kwargs,
) -> AnimationGroup:
    """
    Composite Write animation for a mixed Hebrew + math ``Tex`` line.

    Each ``tex_strings`` segment is animated in **source order** (0 → n-1).
    Hebrew/text segments draw RTL; math segments draw LTR.

    Parameters
    ----------
    tex : Tex
        The compiled ``Tex(...)`` mobject.
    tex_strings_source : sequence of str, optional
        The same tuple you passed to ``Tex(*parts)``. Falls back to
        ``tex.tex_strings`` if not given.
    segment_lag : float
        ``lag_ratio`` between consecutive segments (< 1 means slight overlap).
    hebrew_letter_lag : float
        ``lag_ratio`` between Hebrew letters within one segment.
    math_glyph_lag : float
        ``lag_ratio`` between math glyphs within one formula.
    colors : sequence or dict, optional
        Per-segment color overrides.  Either a positional sequence matching
        ``tex_strings_source`` (use ``None`` to keep the default) or a
        ``{segment_index: color}`` dict.  Applied before the animation starts.
    run_times : sequence or dict, optional
        Per-segment ``run_time`` overrides.  Same format as *colors*.
    **write_kwargs
        Forwarded to each inner ``Write`` animation.
    """
    strings = (
        list(tex_strings_source) if tex_strings_source is not None
        else list(tex.tex_strings)
    )
    n = len(strings)
    segments = partition_segments(tex, strings, tex_template)
    color_map = _resolve_per_segment(colors, n)
    time_map = _resolve_per_segment(run_times, n)

    for i, color in color_map.items():
        vg = segments.get(i)
        if vg is not None:
            vg.set_color(color)

    segment_anims: list = []
    for i in range(n):
        vg = segments.get(i)
        if vg is None or len(vg) == 0:
            continue

        lag = math_glyph_lag if _is_math(strings[i]) else hebrew_letter_lag
        kw = dict(write_kwargs)
        if i in time_map:
            kw["run_time"] = time_map[i]
        anim = Write(vg, lag_ratio=lag, **kw)
        segment_anims.append(anim)

    if not segment_anims:
        return Wait(run_time=_MIN_RUN_TIME)

    return AnimationGroup(*segment_anims, lag_ratio=segment_lag)
