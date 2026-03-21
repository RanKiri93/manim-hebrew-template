import re
from collections.abc import Sequence

from manim import (
    TexTemplate,
    config,
    Write,
    AnimationGroup,
    VGroup,
    Tex,
    MathTex,
    Text,
    FadeIn,
    Wait,
    YELLOW,
    LEFT,
    DOWN,
)

# Whole argument is exactly one $...$ inline math segment (e.g. middle arg of Tex(..., "$E=mc^2$", ...))
_TEX_ARG_INLINE_MATH = re.compile(r"^\s*\$(.+)\$\s*$", re.DOTALL)

# Optional zero-width hook (see :func:`tex_extra_kwargs_for_isolated_math_marker`). Must match preamble in
# :func:`get_hebrew_template`.
MANIM_MATH_MARK = r"\manimmathmark"

# Horizontal fraction-bar / underline glyphs (degenerate bbox height): stroke we add for ``Write``
# visibility. Same issue as fraction bars for ``\\underline{...}`` in Hebrew text segments.
# Tweak if the rule looks too thin vs LaTeX; previous stable value was 1.5.
_FLAT_MATH_RULE_STROKE_WIDTH = 2.05

# Manim raises if ``Scene.play`` gets animations whose total run_time is <= 0.
# Use at least ~1 frame at 15 FPS to avoid "run_time too short" warnings.
_MIN_PLAYABLE_RUN_TIME = 0.07

# Between consecutive ``tex_strings`` segments in :func:`SmartHebWrite` (outer ``AnimationGroup``).
# ``1`` = fully sequential; slightly below ``1`` lets the next segment start a touch earlier (less
# “dead weight” at Hebrew ↔ math boundaries).
_SMART_HEB_WRITE_SEGMENT_LAG_RATIO = 0.6


def tex_arg_is_inline_math(s: str) -> bool:
    """True if this Tex argument is a single inline math fragment ``$...$`` (quotes may be stripped)."""
    return _TEX_ARG_INLINE_MATH.match(s) is not None


def inline_math_inner(s: str) -> str | None:
    """Return the math inside ``$...$`` for a single-arg inline math string, else None."""
    m = _TEX_ARG_INLINE_MATH.match(s)
    return m.group(1) if m else None


def indices_of_inline_math_tex_args(tex_strings: Sequence[str]) -> list[int]:
    """Indices of each Tex() argument that is a standalone ``$...$`` block."""
    return [i for i, t in enumerate(tex_strings) if tex_arg_is_inline_math(t)]


def tex_extra_kwargs_for_isolated_math_marker() -> dict:
    """
    Pass as ``Tex(..., **tex_extra_kwargs_for_isolated_math_marker())`` when you append
    :data:`MANIM_MATH_MARK` inside ``$...$``. Manim then wraps that substring in its
    own ``dvisvgm`` group (``...substring`` id), which can help recover the math region
    when plain argument groups fail — without visible ink (the macro is ``\\mkern0mu``).

    Example::

        Tex("היי ", r"$E=mc^2\\manimmathmark$", " סוף", **tex_extra_kwargs_for_isolated_math_marker())

    The ``$`` characters are still present in Python ``tex.tex_strings``; they are never
    “drawn” by LaTeX. This hook is for **extra** anchoring in the SVG / Manim metadata.
    """
    return {"substrings_to_isolate": [MANIM_MATH_MARK]}


def _norm_gap_vector(xs: list[float]) -> list[float]:
    if len(xs) < 2:
        return []
    gaps = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
    total = sum(abs(g) for g in gaps) or 1.0
    return [g / total for g in gaps]


def _best_window_by_spacing(all_sorted_ltr: list, ref_sorted_ltr: list) -> list:
    """
    Find a contiguous window of len(ref) leaves from all_sorted whose normalized
    x-gaps best match the reference ``MathTex`` (handles collapsed SVG groups).
    """
    n = len(ref_sorted_ltr)
    if n == 0:
        return []
    if len(all_sorted_ltr) < n:
        return []
    ref_xs = [m.get_center()[0] for m in ref_sorted_ltr]
    ref_g = _norm_gap_vector(ref_xs)
    if not ref_g:
        return all_sorted_ltr[:n]

    best_score = float("inf")
    best_window: list = []
    for start in range(len(all_sorted_ltr) - n + 1):
        window = all_sorted_ltr[start : start + n]
        w_xs = [m.get_center()[0] for m in window]
        w_g = _norm_gap_vector(w_xs)
        if len(w_g) != len(ref_g):
            continue
        score = sum((a - b) ** 2 for a, b in zip(ref_g, w_g))
        if score < best_score:
            best_score = score
            best_window = window
    return best_window


def _math_leaves_from_partition(tex: Tex, math_arg_index: int) -> list | None:
    """If Manim kept one submobject per ``tex_strings`` entry, return that part's leaves."""
    if len(tex.submobjects) != len(tex.tex_strings):
        return None
    if math_arg_index < 0 or math_arg_index >= len(tex.submobjects):
        return None
    return tex[math_arg_index].family_members_with_points()


def resolve_tex_inline_math_glyphs(
    tex: Tex,
    *,
    tex_strings_source: Sequence[str] | None = None,
    math_arg_index: int | None = None,
):
    """
    Returns math glyph VMobjects in **left-to-right visual order** (reading order for Latin math).

    *Classification* uses the same strings you passed to ``Tex(...)`` (``tex_strings_source``).
    Dollar signs are **not** required after compilation: only the Python-side strings
    must mark math with ``$...$`` (or use ``tex.tex_strings``, which still keeps them).

    When Manim splits SVG groups correctly, glyphs come from the matching submobject.
    Otherwise a spacing fingerprint vs. a standalone ``MathTex`` of the inner expression
    is used — important for Hebrew XeLaTeX when grouping falls back to ``root``.
    """
    strings = list(tex_strings_source) if tex_strings_source is not None else list(tex.tex_strings)
    math_indices = indices_of_inline_math_tex_args(strings)
    if not math_indices:
        raise ValueError("No inline math argument $...$ found in tex strings.")
    if math_arg_index is None:
        if len(math_indices) != 1:
            raise ValueError(
                "Multiple math segments in tex strings; pass math_arg_index explicitly."
            )
        math_arg_index = math_indices[0]

    inner = inline_math_inner(strings[math_arg_index])
    if inner is None:
        raise ValueError("Could not extract inner math from argument.")

    partitioned = _math_leaves_from_partition(tex, math_arg_index)
    if partitioned is not None:
        leaves = list(partitioned)
        leaves.sort(key=lambda m: m.get_center()[0])
        return leaves

    ref = MathTex(inner, tex_template=tex.tex_template)
    ref_leaves = ref.family_members_with_points()
    ref_leaves.sort(key=lambda m: m.get_center()[0])
    all_leaves = tex.family_members_with_points()
    all_sorted = sorted(all_leaves, key=lambda m: m.get_center()[0])
    return _best_window_by_spacing(all_sorted, ref_leaves)


def _normalize_math_glyph_for_animation(glyph) -> None:
    """
    Some SVG paths load with **fill_opacity 0** and **stroke_width 0** even though they are ink.
    For paths with **non-zero height**, restoring fill fixes ``Write`` / ``DrawBorderThenFill``.

    **Do not** use this for **degenerate-height** horizontal rules — use
    :func:`_prepare_flat_math_rule_glyph_for_write` instead (``Write`` must trace a **stroke**).
    """
    try:
        pts = glyph.get_points()
    except Exception:
        return
    if len(pts) < 2:
        return
    if float(glyph.get_height() or 0) <= 1e-5:
        return
    fo = float(glyph.get_fill_opacity() or 0)
    sw = float(glyph.get_stroke_width() or 0)
    if fo < 1e-6 and sw < 1e-6:
        glyph.set_fill(color=glyph.get_color(), opacity=1.0)


def _prepare_flat_math_rule_glyph_for_write(glyph) -> None:
    """
    Fraction-bar / **underline** style paths: ``get_height() == 0``, fill/stroke both 0 in VMobject data.
    ``DrawBorderThenFill`` interpolates toward the **starting** submobject; if that state is
    fill-only with no stroke, the **final** frame can be invisible (flash, then gone).

    Give a **thin stroke** (no fill) so ``Write`` has a border to trace and a stable visible end.
    Stroke width is ``_FLAT_MATH_RULE_STROKE_WIDTH`` (adjust if too thin vs LaTeX; ``1.5`` was the first stable look).
    """
    try:
        if len(glyph.get_points()) < 2:
            return
    except Exception:
        return
    c = glyph.get_color()
    glyph.set_fill(opacity=0.0)
    glyph.set_stroke(color=c, width=_FLAT_MATH_RULE_STROKE_WIDTH, opacity=1.0)


def _prepare_hebrew_leaf_for_write(leaf) -> None:
    """
    Match :func:`_math_glyph_write_or_fade_in` **geometry fixes** for each drawable leaf in a
    Hebrew ``Tex`` segment: thin horizontal rules (``\\underline``, decorative lines) need
    :func:`_prepare_flat_math_rule_glyph_for_write`; other paths may need
    :func:`_normalize_math_glyph_for_animation`. Without this, ``HebWrite`` / per-leaf ``Write`` can
    flash a rule then leave it invisible for the rest of the animation.
    """
    w, h = float(leaf.get_width()), float(leaf.get_height())
    if h <= 1e-5 and w > 1e-4:
        _prepare_flat_math_rule_glyph_for_write(leaf)
    else:
        _normalize_math_glyph_for_animation(leaf)


def _math_glyph_write_or_fade_in(glyph, *, math_force_write: bool = False, **kwargs):
    """
    ``Write`` / ``DrawBorderThenFill`` trace stroke; many LaTeX paths are **fill-only** (stroke 0).

    * **Degenerate height** (horizontal rules): add a stroke, then ``Write`` — do not rely on fill.
    * **Else**, normalize invisible fill-only paths, then ``FadeIn`` or ``Write`` as before.
    """
    if math_force_write:
        return Write(glyph, **kwargs)
    w, h = float(glyph.get_width()), float(glyph.get_height())
    if h <= 1e-5 and w > 1e-4:
        _prepare_flat_math_rule_glyph_for_write(glyph)
        return Write(glyph, **kwargs)
    _normalize_math_glyph_for_animation(glyph)
    stroke_w = float(glyph.get_stroke_width() or 0)
    fill_op = float(glyph.get_fill_opacity() or 0)
    if stroke_w <= 1e-9 and fill_op > 1e-6:
        return FadeIn(glyph, **kwargs)
    return Write(glyph, **kwargs)


def math_formula_write_animation(
    glyphs_ltr: list,
    *,
    reverse_index_order: bool = False,
    **kwargs,
) -> AnimationGroup:
    """
    ``Write`` animation for one inline-math formula.

    ``glyphs_ltr`` must be in **left-to-right** order (same as :func:`resolve_tex_inline_math_glyphs`):
    local index ``i = 0 … k-1`` is the usual Latin reading order.

    By default (``reverse_index_order=False``), glyphs are written in **ascending** index order
    ``0, 1, …, k-1`` (left-to-right on the page). Set ``reverse_index_order=True`` to write
    ``k-1, …, 0`` (descending indices).

    **Fill-only** paths with **non-zero** bbox height use ``FadeIn`` (``Write`` traces stroke badly).
    **Degenerate-height** paths (fraction bars) get a **thin stroke** so ``Write`` / ``DrawBorderThenFill``
    can finish visible. Pass ``math_force_write=True`` to always use ``Write`` (advanced).
    """
    kw = dict(kwargs)
    lag_between = kw.pop("math_inner_lag_ratio", 0.12)
    force_write = kw.pop("math_force_write", False)
    kw.setdefault("lag_ratio", 0.09)
    if not glyphs_ltr:
        return Wait(run_time=_MIN_PLAYABLE_RUN_TIME)
    if reverse_index_order:
        order = range(len(glyphs_ltr) - 1, -1, -1)
    else:
        order = range(len(glyphs_ltr))
    anims = [
        _math_glyph_write_or_fade_in(
            glyphs_ltr[i],
            math_force_write=force_write,
            **dict(kw),
        )
        for i in order
    ]
    return AnimationGroup(*anims, lag_ratio=lag_between)


def FadeInMathTexIndexLabels(
    tex: Tex,
    *,
    tex_strings_source: Sequence[str] | None = None,
    math_arg_index: int | None = None,
    font_size: float = 36,
    color=None,
    lag_ratio: float = 1.0,
    **kwargs,
):
    """
    Animates only **numeric indices** (0, 1, 2, …) at math glyph positions — not the glyphs.
    """
    if color is None:
        color = YELLOW

    glyphs = resolve_tex_inline_math_glyphs(
        tex,
        tex_strings_source=tex_strings_source,
        math_arg_index=math_arg_index,
    )
    animations = []
    for j, glyph in enumerate(glyphs):
        label = Text(str(j), font_size=font_size, color=color)
        label.move_to(glyph.get_center())
        animations.append(FadeIn(label, **kwargs))
    return AnimationGroup(*animations, lag_ratio=lag_ratio)

def get_hebrew_template(
    font_name: str = "David Libre",
    *,
    explicit_math_styles: bool = True,
    math_pt_smaller: float = 2.0,
) -> TexTemplate:
    """
    Creates and returns a Manim TexTemplate configured for Hebrew rendering.
    Uses XeLaTeX, polyglossia, and fontspec under the hood.

    **Inline vs display math:** Manim's :class:`~manim.mobject.text.tex_mobject.Tex` wraps the line in
    ``\\begin{center}...\\end{center}`` — ``$...$`` is still **inline** math in LaTeX (not a full-width
    display equation). If formulas look **too large**, common causes are ``\\displaystyle`` / ``\\dfrac``
    in the source, or naturally tall symbols (``\\int``, ``\\sum``). When ``explicit_math_styles`` is
    True (default), the preamble sets ``\\everymath{\\textstyle}`` so inline ``$...$`` defaults to
    **text style**. We do **not** set ``\\everydisplay{\\displaystyle}``: that breaks Manim's
    ``MathTex`` (``align*`` / ``\\halign``) with *Improper \\halign inside $$'s*. Display math already
    uses display style by default; override per formula with ``\\displaystyle`` or ``\\textstyle`` as usual.
    Pass ``explicit_math_styles=False`` to omit this.

    **Math font size vs Hebrew:** ``math_pt_smaller`` (default ``2.0``) shrinks **math** fonts by that many
    points relative to Manim's default ``\\documentclass[preview]{standalone}`` body size (10pt), via
    ``\\DeclareMathSizes``. Hebrew text size is unchanged. Pass ``0`` to disable. If you change the
    document class font size, adjust or disable this — it keys off nominal 10pt.
    """
    # xelatex is required to use system fonts and proper RTL shaping
    template = TexTemplate(
        tex_compiler="xelatex", 
        output_format=".pdf"
    )
    
    # Add RTL and language support packages
    template.add_to_preamble(r"\usepackage{polyglossia}")
    template.add_to_preamble(r"\setdefaultlanguage{hebrew}")
    template.add_to_preamble(r"\setotherlanguage{english}")
    
    # Define the font specifically for Hebrew script
    template.add_to_preamble(rf"\newfontfamily\hebrewfont[Script=Hebrew]{{{font_name}}}")
    
    # (Optional) Set it as the main font for the whole document to prevent fallback issues
    template.add_to_preamble(rf"\setmainfont{{{font_name}}}")

    at_begin: list[str] = []
    if explicit_math_styles:
        # % must end lines so TeX treats \everymath as code, not part of the comment.
        # Do not add \everydisplay{\displaystyle}: it breaks MathTex (align* / \halign).
        at_begin.append("\\everymath{\\textstyle}%")
    if math_pt_smaller and math_pt_smaller > 0:
        # Manim's default TexTemplate uses \documentclass[preview]{standalone} → 10pt body.
        base_pt = 10
        mt = max(5, int(round(base_pt - float(math_pt_smaller))))
        script = max(4, int(round(mt * 0.72)))
        scriptscript = max(3, int(round(mt * 0.52)))
        at_begin.append(
            f"\\DeclareMathSizes{{{base_pt}}}{{{mt}}}{{{script}}}{{{scriptscript}}}%"
        )
    if at_begin:
        template.add_to_preamble(
            "\\AtBeginDocument{%\n" + "\n".join(at_begin) + "\n}"
        )

    # Zero-width math kern (no visible output). Use as \manimmathmark inside $...$ and optionally
    # pass substrings_to_isolate=[MANIM_MATH_MARK] so Manim wraps it in an SVG subgroup.
    template.add_to_preamble(r"\newcommand{\manimmathmark}{\mkern0mu}")

    return template

def enable_hebrew_globally(font_name: str = "David Libre", **kwargs):
    """
    Overrides Manim's global configuration to use the Hebrew template by default.
    Call this at the top of your animation script.

    Extra keyword arguments are passed to :func:`get_hebrew_template` (e.g. ``explicit_math_styles=False``,
    ``math_pt_smaller=0``).
    """
    config.tex_template = get_hebrew_template(font_name, **kwargs)

class HebWrite(Write):
    def __init__(self, vmobject, **kwargs):
        
        # 1. Flatten and Sort
        letters = vmobject.family_members_with_points()
        letters.sort(key=lambda m: m.get_center()[0], reverse=True)
        vmobject.submobjects = letters
        
        # 2. Reverse the internal drawing direction
        for leaf in letters:
            leaf.reverse_direction()
            _prepare_hebrew_leaf_for_write(leaf)

        # 3. Set a better default lag_ratio for letter-by-letter drawing
        # (You can still override this in self.play() if you need to)
        kwargs.setdefault("lag_ratio", 0.55) 
        
        # 4. Pass it to Write
        super().__init__(vmobject, **kwargs)

def DebugMathIndices(tex_mobject, **kwargs):
    """
    Diagnostic: same as :func:`FadeInMathTexIndexLabels` (index labels on math only).
    Kept for backwards compatibility.
    """
    kwargs.setdefault("lag_ratio", 1)
    return FadeInMathTexIndexLabels(tex_mobject, **kwargs)


def _minmax_x(leaves: list) -> tuple[float, float]:
    xs = [m.get_center()[0] for m in leaves]
    return min(xs), max(xs)


def _gap_interval_between_math(
    range_a: tuple[float, float], range_b: tuple[float, float]
) -> tuple[float, float] | None:
    """Open interval strictly between two disjoint x-ranges (sorted by left edge)."""
    if range_a[0] <= range_b[0]:
        left, right = range_a, range_b
    else:
        left, right = range_b, range_a
    if left[1] < right[0]:
        return (left[1], right[0])
    return None


def _is_rtl_hebrew_line(hebrew_leaves: list, math_glyphs_by_idx: dict[int, list]) -> bool:
    """
    True if Hebrew text is laid out to the **right** of the math bulk (typical RTL mixed line).
    Used to decide whether "Hebrew before first math in source" sits at high x (RTL) or low x (LTR).
    """
    if not hebrew_leaves:
        return True
    all_math = [m for ix in math_glyphs_by_idx for m in math_glyphs_by_idx[ix]]
    if not all_math:
        return True
    hx = sum(h.get_center()[0] for h in hebrew_leaves) / len(hebrew_leaves)
    mx = sum(m.get_center()[0] for m in all_math) / len(all_math)
    return hx >= mx


def _split_leaves_into_k_groups_rtl(leaves: list, k: int) -> list[list]:
    """
    Partition ``leaves`` into ``k`` contiguous groups in **x descending** (RTL reading order on
    the line). Boundaries are the ``k - 1`` **largest** gaps between consecutive glyphs in that
    order — first ``tex_strings`` Hebrew segment in the group maps to the **rightmost** cluster.
    """
    if k <= 0:
        return []
    if k == 1:
        return [list(leaves)]
    if not leaves:
        return [[] for _ in range(k)]
    ordered = sorted(leaves, key=lambda m: m.get_center()[0], reverse=True)
    if len(ordered) < k:
        groups = [[g] for g in ordered]
        while len(groups) < k:
            groups.append([])
        return groups[:k]
    gaps = [
        (ordered[i].get_center()[0] - ordered[i + 1].get_center()[0], i)
        for i in range(len(ordered) - 1)
    ]
    gaps.sort(key=lambda t: t[0], reverse=True)
    split_after = sorted({g[1] for g in gaps[: k - 1]})
    groups: list[list] = []
    start = 0
    for cut in split_after:
        groups.append(ordered[start : cut + 1])
        start = cut + 1
    groups.append(ordered[start:])
    while len(groups) > k:
        groups[-2].extend(groups[-1])
        groups.pop()
    while len(groups) < k:
        groups.append([])
    return groups[:k]


def _partition_hebrew_for_collapsed(
    strings: list[str],
    hebrew_leaves: list,
    math_glyphs_by_idx: dict[int, list],
) -> dict[int, list]:
    """
    When SVG groups collapse, assign each non-math ``tex_strings`` index its Hebrew leaves.

    **Unified strategy** (no per-(H,M) count branching): split ``tex_strings`` into **zones**
    by source order relative to math arguments — *leading* (indices before the first ``$…$``),
    *between* (indices strictly between consecutive math args), *trailing* (after the last math).
    Leaves in the **open gap** between two math x-ranges go to the *between* zone; leaves on the
    **start side** of the first math / **end side** of the last math go to leading / trailing
    using RTL vs LTR detection. Multiple Hebrew segments in one zone are split by the largest
    intra-cluster gaps (RTL). Leaves that miss strict predicates (e.g. left of leftmost math while
    the leading zone only matched the right side) are merged into a zone that has a **single**
    Hebrew index, or split by gaps among the indices in that zone.
    """
    hebrew_ixs = [i for i in range(len(strings)) if not tex_arg_is_inline_math(strings[i])]
    math_ixs = [i for i in range(len(strings)) if tex_arg_is_inline_math(strings[i])]

    def _rtl_sort(ls: list) -> None:
        ls.sort(key=lambda m: m.get_center()[0], reverse=True)

    if len(hebrew_ixs) == 1:
        h = {hebrew_ixs[0]: list(hebrew_leaves)}
        _rtl_sort(h[hebrew_ixs[0]])
        return h

    if not math_ixs:
        groups = _split_leaves_into_k_groups_rtl(hebrew_leaves, len(hebrew_ixs))
        out = {hebrew_ixs[j]: list(groups[j]) for j in range(len(hebrew_ixs))}
        for k in out:
            _rtl_sort(out[k])
        return out

    ranges = {ix: _minmax_x(math_glyphs_by_idx[ix]) for ix in math_ixs}
    rtl = _is_rtl_hebrew_line(hebrew_leaves, math_glyphs_by_idx)

    out: dict[int, list] = {i: [] for i in hebrew_ixs}
    assigned: set[int] = set()

    def _assign_zone(indices: list[int], pool: list) -> None:
        if not indices:
            return
        groups = _split_leaves_into_k_groups_rtl(pool, len(indices))
        for j, ix in enumerate(sorted(indices)):
            out[ix].extend(groups[j])

    # 0) Hebrew strokes that landed inside a math x-span (collapsed SVG) → Hebrew before that math
    for mix in math_ixs:
        mn, mx = ranges[mix]
        before_h = [i for i in hebrew_ixs if i < mix]
        if not before_h:
            continue
        overlap = [
            leaf
            for leaf in hebrew_leaves
            if id(leaf) not in assigned and mn <= leaf.get_center()[0] <= mx
        ]
        if not overlap:
            continue
        if len(before_h) == 1:
            out[before_h[0]].extend(overlap)
        else:
            _assign_zone(before_h, overlap)
        for leaf in overlap:
            assigned.add(id(leaf))

    def _take_pool(pred) -> list:
        pool = []
        for leaf in hebrew_leaves:
            if id(leaf) in assigned:
                continue
            if pred(leaf.get_center()[0]):
                pool.append(leaf)
        for leaf in pool:
            assigned.add(id(leaf))
        return pool

    # 1) Between consecutive math pairs in **source** order
    for k in range(len(math_ixs) - 1):
        ma, mb = math_ixs[k], math_ixs[k + 1]
        between_idx = [i for i in hebrew_ixs if ma < i < mb]
        if not between_idx:
            continue
        gap = _gap_interval_between_math(ranges[ma], ranges[mb])
        if gap is not None:
            g_lo, g_hi = gap

            def _pred_between(x, lo=g_lo, hi=g_hi):
                return lo < x < hi

            pool = _take_pool(_pred_between)
        else:
            ca = (ranges[ma][0] + ranges[ma][1]) / 2
            cb = (ranges[mb][0] + ranges[mb][1]) / 2
            lo, hi = (ca, cb) if ca < cb else (cb, ca)

            def _pred_soft(x, a=lo, b=hi):
                return a < x < b

            pool = _take_pool(_pred_soft)
        _assign_zone(between_idx, pool)

    # 2) Leading (source indices before first math)
    lead_idx = [i for i in hebrew_ixs if i < math_ixs[0]]
    if lead_idx:
        m0 = math_ixs[0]
        mn, mx = ranges[m0]

        def _pred_lead(x):
            return x > mx if rtl else x < mn

        pool = _take_pool(_pred_lead)
        _assign_zone(lead_idx, pool)

    # 3) Trailing (source indices after last math)
    trail_idx = [i for i in hebrew_ixs if i > math_ixs[-1]]
    if trail_idx:
        mL = math_ixs[-1]
        mn, mx = ranges[mL]

        def _pred_trail(x):
            return x < mn if rtl else x > mx

        pool = _take_pool(_pred_trail)
        _assign_zone(trail_idx, pool)

    # 4) Residual leaves (e.g. left of leftmost math while leading predicate only took the right side)
    remaining = [leaf for leaf in hebrew_leaves if id(leaf) not in assigned]
    if remaining:
        if lead_idx and len(lead_idx) == 1:
            out[lead_idx[0]].extend(remaining)
            for leaf in remaining:
                assigned.add(id(leaf))
            remaining = []
    remaining = [leaf for leaf in hebrew_leaves if id(leaf) not in assigned]
    if remaining:
        if trail_idx and len(trail_idx) == 1:
            out[trail_idx[0]].extend(remaining)
            for leaf in remaining:
                assigned.add(id(leaf))
            remaining = []
    remaining = [leaf for leaf in hebrew_leaves if id(leaf) not in assigned]
    if remaining:

        def _anchor_x_for_hebrew(i: int) -> float:
            left_m = max((m for m in math_ixs if m < i), default=None)
            right_m = min((m for m in math_ixs if m > i), default=None)
            if left_m is None and right_m is None:
                return sum(ranges[m][0] + ranges[m][1] for m in math_ixs) / (2 * len(math_ixs))
            if left_m is None:
                rn, rx = ranges[right_m]
                return (rn + rx) / 2
            if right_m is None:
                ln, lx = ranges[left_m]
                return (ln + lx) / 2
            ln, lx = ranges[left_m]
            rn, rx = ranges[right_m]
            lo, hi = min(lx, rx), max(ln, rn)
            if lo < hi:
                return (lo + hi) / 2
            return (ln + lx + rn + rx) / 4

        for leaf in remaining:
            x = leaf.get_center()[0]
            empty = [i for i in hebrew_ixs if not out[i]]
            if len(empty) == 1:
                out[empty[0]].append(leaf)
            elif empty:
                best = min(empty, key=lambda i: abs(x - _anchor_x_for_hebrew(i)))
                out[best].append(leaf)
            else:
                best = min(hebrew_ixs, key=lambda i: abs(x - _anchor_x_for_hebrew(i)))
                out[best].append(leaf)

    for k in out:
        _rtl_sort(out[k])
    return out


def _hebrew_block_write_animation(leaves: list, **kwargs):
    """
    Same spirit as :class:`HebWrite` (RTL sweep, reversed stroke direction) but without
    reparenting paths into a new ``VGroup`` — one ``Write`` per leaf, RTL order.
    """
    letters = list(leaves)
    letters.sort(key=lambda m: m.get_center()[0], reverse=True)
    for leaf in letters:
        leaf.reverse_direction()
        _prepare_hebrew_leaf_for_write(leaf)
    kwargs.setdefault("lag_ratio", 0.55)
    lag = kwargs.get("lag_ratio", 0.55)
    return AnimationGroup(*[Write(leaf, **kwargs) for leaf in letters], lag_ratio=lag)


def _smart_heb_write_partitioned(
    tex: Tex,
    tex_strings_source: Sequence[str] | None,
    *,
    reverse_math_indices: bool,
    **kwargs,
):
    """
    One submobject per ``tex_strings`` entry: animate in **argument index order** (0, 1, …),
    not in spatial x-order (which broke RTL source order).
    """
    strings = list(tex_strings_source) if tex_strings_source is not None else list(tex.tex_strings)
    animations = []
    assert len(tex.submobjects) == len(strings)

    for i in range(len(strings)):
        part = tex[i]
        if tex_arg_is_inline_math(strings[i]):
            glyphs = resolve_tex_inline_math_glyphs(
                tex,
                tex_strings_source=strings,
                math_arg_index=i,
            )
            animations.append(
                math_formula_write_animation(
                    glyphs,
                    reverse_index_order=reverse_math_indices,
                    **kwargs,
                )
            )
        else:
            animations.append(HebWrite(part, **kwargs))

    return AnimationGroup(*animations, lag_ratio=_SMART_HEB_WRITE_SEGMENT_LAG_RATIO)


def _smart_heb_write_collapsed(
    tex: Tex,
    tex_strings_source: Sequence[str] | None,
    *,
    reverse_math_indices: bool,
    **kwargs,
):
    strings = list(tex_strings_source) if tex_strings_source is not None else list(tex.tex_strings)
    math_ixs = indices_of_inline_math_tex_args(strings)
    if not math_ixs:
        return HebWrite(tex, **kwargs)

    math_glyphs_by_idx: dict[int, list] = {}
    math_ids: set[int] = set()
    for mix in math_ixs:
        glyphs = resolve_tex_inline_math_glyphs(
            tex,
            tex_strings_source=strings,
            math_arg_index=mix,
        )
        math_glyphs_by_idx[mix] = glyphs
        math_ids.update(id(m) for m in glyphs)

    all_leaves = tex.family_members_with_points()
    hebrew_leaves = [m for m in all_leaves if id(m) not in math_ids]

    hebrew_by_idx = _partition_hebrew_for_collapsed(
        strings,
        hebrew_leaves,
        math_glyphs_by_idx,
    )

    animations = []
    for i in range(len(strings)):
        if tex_arg_is_inline_math(strings[i]):
            animations.append(
                math_formula_write_animation(
                    math_glyphs_by_idx[i],
                    reverse_index_order=reverse_math_indices,
                    **kwargs,
                )
            )
        else:
            leaves = hebrew_by_idx.get(i, [])
            if leaves:
                animations.append(_hebrew_block_write_animation(leaves, **kwargs))

    return AnimationGroup(*animations, lag_ratio=_SMART_HEB_WRITE_SEGMENT_LAG_RATIO)


def SmartHebWrite(
    tex_mobject: Tex,
    *,
    tex_strings_source: Sequence[str] | None = None,
    reverse_math_indices: bool = False,
    **kwargs,
):
    """
    One ``Tex`` mobject (single baseline). Segments are animated in **``tex_strings`` index
    order**     ``0, 1, 2, …`` (source order), not in spatial left/right order — so e.g. Hebrew + first
    math + second Hebrew + second math is written in that order even when RTL layout places
    the middle Hebrew chunk to the right on screen.

    Hebrew segments use :class:`HebWrite` when Manim kept per-argument SVG groups; otherwise
    an RTL leaf sweep on the leaves assigned to each Hebrew argument (see
    :func:`_partition_hebrew_for_collapsed` when groups collapse).

    **Math detection:** each ``Tex`` argument that matches a standalone ``$...$`` inline-math
    string (see :func:`tex_arg_is_inline_math`) is treated as a formula. Glyphs for that segment
    come from :func:`resolve_tex_inline_math_glyphs`, in **LTR** order with local indices
    ``0 … k-1`` — the same indexing as in the glyph diagnostic scripts.

    **Math writing order:** by default (``reverse_math_indices=False``), each formula is
    animated with :func:`math_formula_write_animation` in **ascending** index order
    ``0, …, k-1``. Set ``reverse_math_indices=True`` to write ``k-1, …, 0`` instead.

    **Lag / timing:** consecutive ``tex_strings`` segments use an outer ``AnimationGroup`` with
    ``lag_ratio`` ``0.88`` (slightly below ``1`` so the next segment begins a little before the
    previous fully ends — lighter Hebrew ↔ math handoffs). Inside a Hebrew
    segment, :class:`HebWrite` / :func:`_hebrew_block_write_animation` default ``lag_ratio≈0.55``
    between letters; inside math, :func:`math_formula_write_animation` defaults to ``lag_ratio≈0.09``
    per glyph and ``math_inner_lag_ratio≈0.12`` between glyphs. Extra ``**kwargs`` are forwarded to
    those inner animations, not to the outer segment group.

    Pass ``tex_strings_source`` if you built ``Tex`` from a tuple and want an explicit
    reference (same as ``tex.tex_strings`` in the usual case).
    """
    strings = list(tex_strings_source) if tex_strings_source is not None else list(tex_mobject.tex_strings)

    if len(tex_mobject.submobjects) == len(tex_mobject.tex_strings):
        return _smart_heb_write_partitioned(
            tex_mobject,
            strings,
            reverse_math_indices=reverse_math_indices,
            **kwargs,
        )
    return _smart_heb_write_collapsed(
        tex_mobject,
        strings,
        reverse_math_indices=reverse_math_indices,
        **kwargs,
    )


def smart_heb_write_segment(
    tex_mobject: Tex,
    *,
    segment_index: int,
    tex_strings_source: Sequence[str] | None = None,
    reverse_math_indices: bool = False,
    **kwargs,
):
    """
    Build the **single-segment** write animation for ``tex_strings[segment_index]`` — same rules as
    :func:`SmartHebWrite` (partitioned vs collapsed). Use this when you want **pauses** or
    different ``self.play`` timing between segments::

        self.play(smart_heb_write_segment(tex, segment_index=0, tex_strings_source=parts))
        self.play(smart_heb_write_segment(tex, segment_index=1, tex_strings_source=parts))
        self.wait(3)
        self.play(smart_heb_write_segment(tex, segment_index=2, tex_strings_source=parts))

    If a Hebrew segment resolves to no drawable leaves (rare), returns a short
    :class:`~manim.animation.animation.Wait` (Manim cannot ``play`` zero-duration animations).
    """
    strings = list(tex_strings_source) if tex_strings_source is not None else list(tex_mobject.tex_strings)
    n = len(strings)
    if not (0 <= segment_index < n):
        raise ValueError(f"segment_index must be in 0..{n - 1}, got {segment_index}")

    if len(tex_mobject.submobjects) == len(tex_mobject.tex_strings):
        part = tex_mobject[segment_index]
        if tex_arg_is_inline_math(strings[segment_index]):
            glyphs = resolve_tex_inline_math_glyphs(
                tex_mobject,
                tex_strings_source=strings,
                math_arg_index=segment_index,
            )
            return math_formula_write_animation(
                glyphs,
                reverse_index_order=reverse_math_indices,
                **kwargs,
            )
        return HebWrite(part, **kwargs)

    math_ixs = indices_of_inline_math_tex_args(strings)
    if not math_ixs:
        if segment_index == 0:
            return HebWrite(tex_mobject, **kwargs)
        return Wait(run_time=_MIN_PLAYABLE_RUN_TIME)

    math_glyphs_by_idx: dict[int, list] = {}
    math_ids: set[int] = set()
    for mix in math_ixs:
        glyphs = resolve_tex_inline_math_glyphs(
            tex_mobject,
            tex_strings_source=strings,
            math_arg_index=mix,
        )
        math_glyphs_by_idx[mix] = glyphs
        math_ids.update(id(m) for m in glyphs)

    all_leaves = tex_mobject.family_members_with_points()
    hebrew_leaves = [m for m in all_leaves if id(m) not in math_ids]
    hebrew_by_idx = _partition_hebrew_for_collapsed(
        strings,
        hebrew_leaves,
        math_glyphs_by_idx,
    )

    if tex_arg_is_inline_math(strings[segment_index]):
        return math_formula_write_animation(
            math_glyphs_by_idx[segment_index],
            reverse_index_order=reverse_math_indices,
            **kwargs,
        )
    leaves = hebrew_by_idx.get(segment_index, [])
    if leaves:
        return _hebrew_block_write_animation(leaves, **kwargs)
    return Wait(run_time=_MIN_PLAYABLE_RUN_TIME)


def set_tex_segment_color(
    tex_mobject: Tex,
    *,
    segment_index: int,
    color,
    tex_strings_source: Sequence[str] | None = None,
) -> None:
    """
    Color every drawable path that belongs to ``tex_strings[segment_index]`` — same segmentation as
    :func:`SmartHebWrite` / :func:`smart_heb_write_segment`.

    Use this instead of Manim's ``tex_to_color_map`` when XeLaTeX collapses SVG groups: the built-in
    map can raise ``KeyError`` on ``id_to_vgroup_dict`` because substring groups never materialize.

    * **Partitioned** (one submobject per argument): ``tex[segment_index].set_color(...)``.
    * **Collapsed**: math leaves from :func:`resolve_tex_inline_math_glyphs`; Hebrew leaves from the
      same partition as the write animation.
    """
    strings = list(tex_strings_source) if tex_strings_source is not None else list(tex_mobject.tex_strings)
    n = len(strings)
    if not (0 <= segment_index < n):
        raise ValueError(f"segment_index must be in 0..{n - 1}, got {segment_index}")

    if len(tex_mobject.submobjects) == len(tex_mobject.tex_strings):
        tex_mobject[segment_index].set_color(color)
        return

    math_ixs = indices_of_inline_math_tex_args(strings)
    if not math_ixs:
        tex_mobject.set_color(color)
        return

    math_glyphs_by_idx: dict[int, list] = {}
    math_ids: set[int] = set()
    for mix in math_ixs:
        glyphs = resolve_tex_inline_math_glyphs(
            tex_mobject,
            tex_strings_source=strings,
            math_arg_index=mix,
        )
        math_glyphs_by_idx[mix] = glyphs
        math_ids.update(id(m) for m in glyphs)

    all_leaves = tex_mobject.family_members_with_points()
    hebrew_leaves = [m for m in all_leaves if id(m) not in math_ids]
    hebrew_by_idx = _partition_hebrew_for_collapsed(
        strings,
        hebrew_leaves,
        math_glyphs_by_idx,
    )

    if tex_arg_is_inline_math(strings[segment_index]):
        for g in math_glyphs_by_idx[segment_index]:
            g.set_color(color)
    else:
        for leaf in hebrew_by_idx.get(segment_index, []):
            leaf.set_color(color)