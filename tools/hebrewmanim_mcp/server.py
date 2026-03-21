"""
MCP server: expose HebrewManim codegen (axes / graphs) for LLM clients.

Run (stdio, for Cursor / Claude Desktop):
  pip install mcp anyio
  python server.py

Natural language is interpreted by the *host* (chat UI); this server accepts
structured tool arguments. The model should map user requests to JSON fields.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from codegen_axes import generate_axes_scene

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:
    print("Install dependencies: pip install mcp anyio", file=sys.stderr)
    raise e

mcp = FastMCP("hebrewmanim-codegen")

CAPABILITIES_MD = """# HebrewManim codegen (MCP)

## What this server does
- **`hebrewmanim_axes_scene`**: Generates Manim **Axes / NumberPlane** code aligned with `tools/tex_line_codegen/index.html` (axes tab): ranges, tips, optional Hebrew template, per-object colors, `run_time` / `wait`, parallel `Create` groups, graphs (`plot`) and points (`Dot`).

## Natural language
The MCP does **not** parse natural language. Your chat client maps prose → tool calls. Describe the scene to the model; it should call tools with structured arguments.

## Roadmap
- **Tex / SmartHebWrite** line builder is still in the **static HTML** only; a shared Python module + MCP tool can be added later.

## Repo
`Technion-HebrewManim` — see `hebrew_utils.py`, `tools/tex_line_codegen/index.html`.
"""


@mcp.tool(name="hebrewmanim_capabilities", description="Markdown: capabilities and roadmap")
def hebrewmanim_capabilities() -> str:
    return CAPABILITIES_MD


@mcp.tool(
    name="hebrewmanim_axes_scene",
    description=(
        "Generate AxesScene Python: snippet_axes_and_objects, full_python_module, animation_only. "
        "Matches the axes tab in tools/tex_line_codegen/index.html."
    ),
)
def hebrewmanim_axes_scene(
    axes_kind: str = "Axes",
    x_range: str = "-7, 7, 1",
    y_range: str = "-4, 4, 1",
    x_length: float = 6,
    y_length: float = 4,
    include_tip: bool = True,
    use_hebrew_template: bool = False,
    axes_play_run_time: float = 1.0,
    axes_wait_after: float = 0.5,
    objects: list[dict[str, Any]] | None = None,
) -> str:
    payload: dict[str, Any] = {
        "axes_kind": axes_kind,
        "x_range": x_range,
        "y_range": y_range,
        "x_length": x_length,
        "y_length": y_length,
        "include_tip": include_tip,
        "use_hebrew_template": use_hebrew_template,
        "axes_play_run_time": axes_play_run_time,
        "axes_wait_after": axes_wait_after,
        "objects": objects or [],
    }
    try:
        result = generate_axes_scene(payload)
    except (ValueError, KeyError, TypeError) as e:
        return f"Error: {e}"
    return json.dumps(result, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="stdio")
