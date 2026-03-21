# Glyph index preview (local web UI)

Small **localhost** tool that runs **Manim** `MathTex` and draws **yellow indices** `0, 1, …` on each drawable leaf in **left-to-right** order (sorted by glyph center `x`). That matches the ordering used for math animation helpers in `hebrew_utils` when the **inner** expression is the same.

## Run

From the **repository root**:

```bash
python tools/glyph_index_preview/server.py
```

Open **http://127.0.0.1:8765/** in a browser. Paste LaTeX for `MathTex` (no surrounding `$`), click **Render**.

- **Hebrew template** checkbox uses `get_hebrew_template()` (XeLaTeX) — slower but aligned with mixed Hebrew scenes.
- Unchecked uses Manim’s default template (often fine for pure math).

## Limits

- This previews **`MathTex`** only, not a full mixed `Tex` line. For inline math inside `Tex("…", "$…$", …)`, the **inner** expression should match what you type here for index alignment; path counts can still differ if grouping differs.
- Requires **Manim** installed in the same Python environment you use to run the server.
- Bad LaTeX returns an error message from the Manim subprocess.

## Files

| File | Role |
|------|------|
| `server.py` | HTTP server + `POST /api/render` → PNG bytes |
| `scene_glyph_debug.py` | Manim scene (labels on leaves) |
| `index.html` | UI |
