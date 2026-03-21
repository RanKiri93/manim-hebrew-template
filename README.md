# Hebrew + math in Manim (`hebrew_utils`)

**עברית:** [`README.he.md`](README.he.md)

This project helps you mix **Hebrew text** and **inline LaTeX math** in a **single** [`Tex`](https://docs.manim.community/en/stable/reference/manim.mobject.text.tex_mobject.Tex.html) mobject, then animate it in a sensible order: Hebrew in **RTL** “writing” order, math in **left‑to‑right** glyph order.

Everything lives in **`hebrew_utils.py`**. Import it from your Manim scene file and set the template once (see below).

**Debug math glyph indices locally:** run `python tools/glyph_index_preview/server.py` and open http://127.0.0.1:8765/ — it renders `MathTex` with numeric labels in LTR order (see `tools/glyph_index_preview/README.md`).

**Generate `Tex` + animation boilerplate (Hebrew UI):** open `tools/tex_line_codegen/index.html` in a browser — **tabs**: **יוצר שורות** (Hebrew lines + `Tex` / `SmartHebWrite`, font name/size, colors, durations, optional **full-line underline** after write) and **צירים וגרפים** (`Axes` / `NumberPlane`, **`run_time`/`wait`**, optional **parallel** `play`, graphs + points `(x,y)`). See `tools/tex_line_codegen/README.md`.

**MCP (LLM clients):** optional [Model Context Protocol](https://modelcontextprotocol.io/) server for **axes/graph codegen** — `tools/hebrewmanim_mcp/` (`python server.py` after `pip install mcp`). Natural language is handled by the **host**; the server exposes structured tools. Tex-line parity is a roadmap item — see `tools/hebrewmanim_mcp/README.md`.

**GitHub:** this project is the source of truth for **[RanKiri93/manim-hebrew-template](https://github.com/RanKiri93/manim-hebrew-template)** — push from this folder (`git remote` name **`origin`**). Do not pull an older snapshot of that repo into here; see [`docs/GITHUB.md`](docs/GITHUB.md).

---

## What you need

- **Manim** (Community Edition is fine).
- **XeLaTeX** — the Hebrew template uses `xelatex`, not `latex`.
- A **Hebrew-capable font** on your system. The default in `get_hebrew_template()` is **David Libre**; install it or pass another font name.

---

## 1. Turn on the Hebrew template

Manim must compile your line with the same preamble as the rest of your helpers. At the **top** of your scene module (after imports):

```python
from hebrew_utils import get_hebrew_template
from manim import config

config.tex_template = get_hebrew_template()  # optional: get_hebrew_template("Your Hebrew Font")
```

Or call `enable_hebrew_globally()` once — it does the same assignment internally.

**Inline math size:** Manim’s `Tex` centers the line, but `$...$` is still **inline** math in LaTeX — it is not a full-width display equation. If formulas looked **too large**, the default template sets `\everymath{\textstyle}` so inline math defaults to **text style**, and `\DeclareMathSizes` so **math** is about **2pt smaller** than the default 10pt body (Hebrew text size is unchanged). We do not set `\everydisplay{\displaystyle}` (that can break `MathTex` / `align*`). Tune with `get_hebrew_template(math_pt_smaller=1.5)` or `math_pt_smaller=0` to turn off the math shrink. To drop `\everymath{\textstyle}` only, use `explicit_math_styles=False`. You can still force `\displaystyle` or `\dfrac` inside a single formula when you need it.

---

## 2. How to build a mixed Hebrew + math line

### One `Tex`, several string arguments

Put **each** inline formula in its **own** Python argument as a string that looks like **`"$...$"`** (one math chunk per argument). Plain Hebrew stays in separate arguments.

**Good:**

```python
tex_parts = (
    "משפט ראשון ",
    r"$\sin{(x)}$",
    " משפט שני ",
    r"$\cos{(x)}$",
)
text = Tex(*tex_parts)
```

**Why:** Manim stores this as `text.tex_strings`. The helpers use that list to know **which** slices are math and **in what order** they should animate — even when RTL layout places pieces left/right differently than the source order.

**Avoid:** One big string with multiple `$...$` blocks inside — you lose a clean per-block API and the tooling is harder to reason about.

### Dollar signs are not “drawn”

The `$` characters mark math in LaTeX; they usually **do not** show up as separate SVG paths. Detection is done from **Python** (`tex_strings`), not by hunting for dollar-shaped glyphs in the SVG.

---

## 3. Animate the line: `SmartHebWrite`

`SmartHebWrite` plays one animation for each **segment in `tex_strings` order** (`0, 1, 2, …`): Hebrew segments use RTL-style `Write` behavior; each math segment uses `Write` on its glyphs in **local** left‑to‑right order (`0 … k-1`).

```python
from hebrew_utils import SmartHebWrite

self.play(SmartHebWrite(text, tex_strings_source=tex_parts))
```

- Pass **`tex_strings_source`** with the same tuple you used for `Tex(*tex_parts)` when you want to be explicit (recommended if you build strings in multiple steps).
- **`reverse_math_indices=True`** — within each formula, draw glyphs from **last index to first** (handy for debugging or stylistic effect).

If XeLaTeX **collapses** SVG groups (common with Hebrew), `hebrew_utils` still assigns Hebrew paths to the right `tex_strings` index using **unified spatial + source-order heuristics** (zones: leading / between math / trailing, RTL detection, gap splits). It is **not** a formal proof for every possible layout — exotic lines may need extra isolation (`MANIM_MATH_MARK`) or splitting into more `Tex` arguments.

### Coloring one segment

- **When** ``len(tex.submobjects) == len(tex.tex_strings)``, you can color a whole argument with ``tex[i].set_color(...)``.
- **When groups collapse**, Manim’s `tex_to_color_map` may **raise** `KeyError` (substring SVG ids missing). Use **`set_tex_segment_color(tex, segment_index=i, color=..., tex_strings_source=parts)`** instead — it colors the same paths as `SmartHebWrite` would animate for that index.

Example scene: `tex_coloring_scene.py` (`TexColoringDemo`).

### Per-segment `run_time` and pauses

For **different durations per segment** or **waits between parts**, do **not** use a single `SmartHebWrite` — loop over indices with `smart_heb_write_segment` and pass `run_time=...` (and optional `lag_ratio` / `math_inner_lag_ratio` per play):

```python
from hebrew_utils import smart_heb_write_segment

segment_run_times = (1.0, 0.75, 1.25, 0.85, 1.1)  # one value per tex_strings index

for i in range(len(tex_parts)):
    self.play(
        smart_heb_write_segment(
            text,
            segment_index=i,
            tex_strings_source=tex_parts,
            run_time=segment_run_times[i],
        ),
    )
    if i == 2:
        self.wait(1)  # example: pause after the third segment
```

See `segment_pause_scene.py` (`SegmentPauseDemo`) for a minimal example with per-segment timing and a pause.

Scaling the **whole** line to one duration is still: `self.play(SmartHebWrite(...), run_time=T)`.

### Default lag / overlap (`SmartHebWrite` only)

When you **do** use one `SmartHebWrite`, consecutive segments are composed with an outer `AnimationGroup` whose `lag_ratio` is **`_SMART_HEB_WRITE_SEGMENT_LAG_RATIO`** in `hebrew_utils.py` (tweak there for a lighter or heavier handoff between Hebrew and math). Inner defaults: Hebrew letter sweeps ~`0.55`, math glyphs use `math_inner_lag_ratio` ~`0.12` (see `math_formula_write_animation`).

---

## 4. Other building blocks

| Name | Role |
|------|------|
| **`HebWrite`** | Subclass of `Write` for **Hebrew-only** text: RTL sweep and reversed stroke direction. |
| **`resolve_tex_inline_math_glyphs(tex, tex_strings_source=..., math_arg_index=...)`** | Returns the drawable **math** leaves for one `$...$` argument, in **LTR** order. If there are **several** math arguments, pass **`math_arg_index`** (index into your tuple). |
| **`indices_of_inline_math_tex_args(parts)`** | Lists which indices in `parts` are standalone `$...$` arguments. |
| **`tex_arg_is_inline_math` / `inline_math_inner`** | Small helpers for classifying and parsing those arguments. |
| **`math_formula_write_animation(glyphs, reverse_index_order=False, ...)`** | Builds a single formula’s `Write` chain from a glyph list (same order as `resolve_tex_inline_math_glyphs`). |
| **`FadeInMathTexIndexLabels`** | Animates **numbers** `0, 1, 2, …` at math glyph positions (diagnostic: check local indices). For **multiple** formulas, call it per `math_arg_index` or use a custom loop (see optional marker below). |
| **`set_tex_segment_color`** | Sets fill color on paths belonging to one `tex_strings` index (works when `tex[i]` is not available). |
| **`smart_heb_write_segment`** | Returns the write animation for a **single** segment — pass **`run_time=`** per segment; use with **`self.wait()`** between `self.play` calls for pauses. |
| **`MANIM_MATH_MARK`** + **`tex_extra_kwargs_for_isolated_math_marker()`** | Optional **invisible** `\mkern0mu` hook inside `$...$` so Manim can isolate a substring in the SVG. Append the mark to the math string and pass `**tex_extra_kwargs_for_isolated_math_marker()`` into `Tex(...)`. |

---

## 5. Optional: invisible math marker

If plain SVG grouping is flaky, you can add the marker **inside** the math argument and pass the extra kwargs:

```python
from hebrew_utils import MANIM_MATH_MARK, tex_extra_kwargs_for_isolated_math_marker

parts = ("טקסט ", f"$x^2{MANIM_MATH_MARK}$", " סוף")
t = Tex(*parts, **tex_extra_kwargs_for_isolated_math_marker())
```

The macro is defined in `get_hebrew_template()`; it should not add visible ink.

---

## 6. Rendering a Manim scene

From your project folder, with your scene file and class name:

```bash
manim -pql your_scene.py YourSceneName
```

`-ql` is fast preview quality; use `-qh` for higher quality. `-p` opens the player when the render finishes.

---

## 7. Troubleshooting

| Symptom | What it usually means |
|--------|-------------------------|
| Manim logs **“Could not find SVG group for tex part …”** | Often **normal** with Hebrew + XeLaTeX: Manim falls back to a root group. **`resolve_tex_inline_math_glyphs`** still has a **spacing-based** fallback vs a reference `MathTex`. |
| Math animates in the wrong **visual** order inside a formula | Check that `resolve_tex_inline_math_glyphs` sees the right **`math_arg_index`** when you have **multiple** `$...$` arguments. |
| Hebrew and math segments play in the wrong **story** order | Ensure you pass the same tuple to **`Tex`** and **`tex_strings_source`**, and that each formula is its **own** `$...$` argument. |

---

## 8. Compatibility note

This module is written for **Manim Community** APIs (`Tex`, `MathTex`, `config.tex_template`, etc.). If you use a different Manim fork, small import or API tweaks may be needed.

---

Happy animating.
