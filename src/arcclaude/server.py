"""ARCclaude MCP server — exposes the ArcGIS Pro ecosystem to AI assistants.

Runs as a stdio MCP server. Geoprocessing happens in a separate persistent
worker process on ArcGIS Pro's own Python (see bridge.py / arcpy_worker.py).
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from .bridge import ArcPyBridge, WorkerError
from .live import live_execute, paste_line

mcp = FastMCP(
    "arcclaude",
    instructions=(
        "ARCclaude gives you full access to ArcGIS Pro via ArcPy. "
        "The arcpy session is PERSISTENT: variables set in one arcpy_execute "
        "call remain available in later calls. The first call is slow "
        "(~20-60s) while arcpy imports and checks out a license; subsequent "
        "calls are fast. Use search_gp_tools/describe_gp_tool to discover any "
        "of the ~1800 geoprocessing tools, run_gp_tool to execute one, and "
        "arcpy_execute for arbitrary ArcPy/Python code. House rules: work in "
        "the CURRENT project - never create new .aprx files, duplicate maps/"
        "layouts, or add layers unless explicitly asked (prefer symbology/"
        "property updates in place); after editing a map or layout live, call "
        "its .openView() so the user sees it instantly; pass a human-friendly "
        "`action` label to pro_live_execute; explain auto-fixes in plain words."
    ),
)

bridge = ArcPyBridge()


def _dump(resp: dict) -> str:
    """Render a worker response for the model: readable JSON, no id noise."""
    resp = {k: v for k, v in resp.items() if k not in ("id", "ok")}
    return json.dumps(resp, indent=2, ensure_ascii=False, default=repr)


def _call(op: str, timeout: float | None = None, **fields) -> str:
    try:
        resp = bridge.request(op, timeout=timeout, **fields)
    except WorkerError as exc:
        return json.dumps({"error": str(exc)})
    return _dump(resp)


# ---------------------------------------------------------------------------


@mcp.tool()
def arcpy_execute(code: str, timeout_seconds: float = 300) -> str:
    """Execute Python code in the persistent ArcPy session.

    `arcpy` is already imported. Variables persist between calls, so you can
    build up state across multiple invocations. If the last statement is a
    bare expression its repr is returned (like a REPL). stdout is captured.

    Use this for anything ArcPy can do: geoprocessing, arcpy.da cursors,
    arcpy.mp map automation, raster algebra, arcpy.Describe, etc.
    """
    return _call("exec", timeout=timeout_seconds, code=code)


@mcp.tool()
def run_gp_tool(
    tool: str,
    args: list[str] | None = None,
    kwargs: dict[str, str] | None = None,
    timeout_seconds: float = 600,
) -> str:
    """Run a geoprocessing tool by name and return its outputs and messages.

    `tool` accepts either the flat name ('Buffer_analysis') or module form
    ('analysis.Buffer'). Positional parameters go in `args`, named parameters
    in `kwargs`. Use describe_gp_tool first if unsure of the signature.
    """
    return _call(
        "run_tool", timeout=timeout_seconds,
        tool=tool, args=args or [], kwargs=kwargs or {},
    )


@mcp.tool()
def search_gp_tools(query: str = "", limit: int = 40) -> str:
    """Search all available geoprocessing tools (including extension toolboxes).

    Space-separated terms are ANDed, matched against tool names like
    'Buffer_analysis'. Empty query lists everything (up to limit).
    """
    return _call("search_tools", query=query, limit=limit)


@mcp.tool()
def describe_gp_tool(tool: str) -> str:
    """Get the syntax and full documentation for a geoprocessing tool."""
    return _call("describe_tool", tool=tool)


@mcp.tool()
def create_features(
    geojson: str,
    output_path: str,
    geometry_type: str = "",
    timeout_seconds: float = 300,
) -> str:
    """Create vector data (shapefile or geodatabase feature class) from GeoJSON.

    This is the fastest way to MAKE data from scratch: emit a GeoJSON
    FeatureCollection and pick an output path. `output_path` decides the
    format: `C:\\data\\roads.shp` creates a shapefile, `C:\\data\\my.gdb\\roads`
    a file-geodatabase feature class. Attribute fields are created from the
    feature properties automatically. Coordinates must be WGS84 lon/lat (the
    GeoJSON spec); use run_gp_tool 'Project_management' afterwards if you
    need another CRS. Existing outputs are overwritten. The geometry type is
    inferred from the data; set `geometry_type` (POINT, MULTIPOINT, POLYLINE,
    POLYGON) only when the collection mixes types and you must pick one.
    Returns a description of the created dataset.
    """
    fields = {"geojson": geojson, "path": output_path}
    if geometry_type:
        fields["geometry_type"] = geometry_type.upper()
    return _call("create_features", timeout=timeout_seconds, **fields)


@mcp.tool()
def export_features(
    path: str,
    where: str = "",
    limit: int = 1000,
    timeout_seconds: float = 300,
) -> str:
    """Read vector data (shapefile, feature class, layer) as GeoJSON.

    The inverse of create_features — lets you inspect actual geometries and
    attributes. Optional `where` is a SQL where-clause to filter rows
    (e.g. "POP > 10000"); `limit` caps returned features (response says if
    truncated). Output coordinates are WGS84.
    """
    return _call("export_features", timeout=timeout_seconds,
                 path=path, where=where, limit=limit)


@mcp.tool()
def describe_data(path: str) -> str:
    """Describe a dataset: type, spatial reference, extent, fields, row count.

    Works on feature classes, shapefiles, rasters, tables, workspaces —
    anything arcpy.Describe understands.
    """
    return _call("describe_data", path=path)


@mcp.tool()
def list_workspace(path: str) -> str:
    """Inventory a workspace (geodatabase or folder): feature classes,
    rasters, tables and datasets it contains."""
    return _call("list_workspace", path=path)


@mcp.tool()
def inspect_project(path: str) -> str:
    """Inspect an ArcGIS Pro project (.aprx): maps, layers, data sources,
    layouts and default geodatabase."""
    return _call("inspect_project", path=path, timeout=120)


@mcp.tool()
def pro_live_execute(code: str, timeout_seconds: float = 60, action: str = "") -> str:
    """Execute Python INSIDE the currently open ArcGIS Pro application.

    Unlike arcpy_execute (headless background session), this runs in the live
    Pro session the user is looking at: `arcpy.mp.ArcGISProject("CURRENT")`
    works, added layers appear immediately, the open project can be saved.
    Requires the user to have cowork mode running — if no listener responds,
    the error includes the exact one-liner they must paste into Pro's Python
    window. Variables persist between calls (separate namespace from
    arcpy_execute). Caution: prefer data/layer/symbology operations; avoid
    rapid or repeated view/camera manipulation, which can destabilize Pro.
    Pass `action` as a short human label ("Applying symbology") - it shows in
    the user's add-in activity log. House rules: don't create new .aprx files,
    maps, layouts or layers unless the user asked; after changing a map or
    layout, call its .openView() so the change appears instantly.
    """
    result = live_execute(code, timeout=timeout_seconds, action=action if action else None)
    return json.dumps(result, indent=2, ensure_ascii=False, default=repr)


@mcp.tool()
def session_status() -> str:
    """Check the ArcPy session: license level, workspace, live variables.
    Starts the session if it isn't running yet (first start is slow)."""
    try:
        if not bridge.alive:
            info = bridge.start()
            return json.dumps({"started": True, **info}, default=repr)
        return _call("ping", timeout=30)
    except (WorkerError, FileNotFoundError) as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool()
def restart_session() -> str:
    """Restart the ArcPy worker process. Clears all session variables and
    releases any locks/licenses. Use after a hang, crash, or to free state."""
    try:
        info = bridge.restart()
        return json.dumps({"restarted": True, **info}, default=repr)
    except (WorkerError, FileNotFoundError) as exc:
        return json.dumps({"error": str(exc)})


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
