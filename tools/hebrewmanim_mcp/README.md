# HebrewManim MCP server

[Model Context Protocol](https://modelcontextprotocol.io/) server that exposes **Manim codegen** aligned with `tools/tex_line_codegen/index.html`.

## What runs today

| Piece | Status |
|--------|--------|
| **Axes / NumberPlane** (graphs, points, colors, timing, parallel `Create`) | Implemented in [`codegen_axes.py`](codegen_axes.py), used by the MCP tool `hebrewmanim_axes_scene` |
| **Tex lines** (`SmartHebWrite`, `$...$`, colors, underline, …) | Still **HTML-only**; future: extract shared Python + add `hebrewmanim_tex_lines` tool |

## Natural language vs this server

- **MCP does not parse natural language.** The chat client (Cursor, Claude Desktop, another MCP host) runs the LLM; the model turns user text into **tool calls** with JSON arguments.
- You connect this server to that host so the model can call `hebrewmanim_axes_scene` with structured parameters (or rely on the model to fill defaults).

## Install & run

```bash
cd tools/hebrewmanim_mcp
pip install mcp
python server.py
```

The process speaks **stdio** MCP (default for local tools).

## Cursor / Claude Desktop config (example)

Point the client at this server, e.g.:

```json
{
  "mcpServers": {
    "hebrewmanim-codegen": {
      "command": "python",
      "args": [
        "C:/path/to/Technion-HebrewManim/tools/hebrewmanim_mcp/server.py"
      ]
    }
  }
}
```

Use your real path and the same Python where `mcp` is installed.

## Tools

1. **`hebrewmanim_capabilities`** — Short markdown overview (roadmap, NL boundary).
2. **`hebrewmanim_axes_scene`** — Parameters mirror the axes tab (`axes_kind`, `x_range`, `y_range`, lengths, `include_tip`, `use_hebrew_template`, axis timing, `objects` list with `type` `graph` | `point`, `parallel_with_previous`, etc.). Returns JSON with:
   - `snippet_axes_and_objects`
   - `full_python_module`
   - `animation_only`

## Keeping parity with the HTML tool

When you change axes behavior in `index.html`, update **`codegen_axes.py`** (and optionally add a small test or diff checklist).

## Dependencies

- `mcp` (includes `anyio` transitively)

Optional: add a `pyproject.toml` or `requirements-mcp.txt` in this folder if you want a dedicated venv for the MCP server only.
