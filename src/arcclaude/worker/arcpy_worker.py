"""ARCclaude ArcPy worker — a persistent arcpy session driven over stdio.

This script runs on ArcGIS Pro's Python environment (arcgispro-py3) and
deliberately uses ONLY the standard library + arcpy, so Esri's locked
environment never needs any packages installed into it.

Protocol: JSON lines. One request object in on stdin, one response object
out on stdout, matched by "id".

Request:  {"id": 1, "op": "exec", ...op-specific fields...}
Response: {"id": 1, "ok": true, ...} or {"id": 1, "ok": false, "error": "..."}

On startup (after arcpy import) the worker emits a ready event:
  {"event": "ready", "product": "...", "version": "...", "license": "..."}
"""

from __future__ import annotations

import ast
import contextlib
import io
import json
import sys
import time
import traceback

# The persistent namespace shared by every "exec" request. Variables,
# imports and function definitions survive between calls.
SESSION: dict = {"__name__": "__arcclaude__"}

arcpy = None  # populated in main() after the slow import


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _send(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, default=repr) + "\n")
    sys.stdout.flush()


def _error_payload(req_id, exc: BaseException, stdout_text: str = "") -> dict:
    payload = {
        "id": req_id,
        "ok": False,
        "error": f"{type(exc).__name__}: {exc}",
        "traceback": traceback.format_exc(limit=20),
    }
    if stdout_text:
        payload["stdout"] = stdout_text
    # Geoprocessing failures carry rich messages worth surfacing.
    if arcpy is not None:
        try:
            gp_messages = arcpy.GetMessages()
            if gp_messages:
                payload["gp_messages"] = gp_messages
        except Exception:
            pass
    return payload


def _jsonable(value, depth: int = 0):
    """Best-effort conversion to something json.dumps can handle."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if depth >= 3:
        return repr(value)
    if isinstance(value, dict):
        return {str(k): _jsonable(v, depth + 1) for k, v in list(value.items())[:200]}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v, depth + 1) for v in list(value)[:500]]
    return repr(value)


# --------------------------------------------------------------------------
# op: exec — run arbitrary Python in the persistent session
# --------------------------------------------------------------------------

def op_exec(req: dict) -> dict:
    code = req.get("code", "")
    buf = io.StringIO()
    result_value = None
    has_result = False

    tree = ast.parse(code, mode="exec")
    # IPython-style: if the last statement is a bare expression, evaluate it
    # and return its repr so the caller sees the value without print().
    last_expr = None
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        last_expr = ast.Expression(tree.body.pop(-1).value)

    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        exec(compile(tree, "<arcclaude>", "exec"), SESSION)
        if last_expr is not None:
            result_value = eval(compile(last_expr, "<arcclaude>", "eval"), SESSION)
            has_result = result_value is not None

    resp = {"id": req["id"], "ok": True, "stdout": buf.getvalue()}
    if has_result:
        resp["result"] = repr(result_value)
    return resp


# --------------------------------------------------------------------------
# op: run_tool — execute any geoprocessing tool by name
# --------------------------------------------------------------------------

def op_run_tool(req: dict) -> dict:
    tool_name = req["tool"]
    args = req.get("args", [])
    kwargs = req.get("kwargs", {})

    func = getattr(arcpy, tool_name, None)
    if func is None:
        # Try module-qualified form, e.g. "analysis.Buffer"
        if "." in tool_name:
            module_name, short = tool_name.split(".", 1)
            module = getattr(arcpy, module_name, None)
            func = getattr(module, short, None) if module else None
    if func is None:
        raise AttributeError(
            f"Tool {tool_name!r} not found. Use search_tools to find the exact "
            f"name, e.g. 'Buffer_analysis' or 'analysis.Buffer'."
        )

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        result = func(*args, **kwargs)

    outputs = []
    try:
        for i in range(result.outputCount):
            outputs.append(str(result.getOutput(i)))
    except Exception:
        outputs = [repr(result)]

    return {
        "id": req["id"],
        "ok": True,
        "outputs": outputs,
        "messages": arcpy.GetMessages(),
        "stdout": buf.getvalue(),
    }


# --------------------------------------------------------------------------
# op: search_tools / describe_tool — dynamic discovery of every GP tool,
# including tools from any installed extension toolbox.
# --------------------------------------------------------------------------

def op_search_tools(req: dict) -> dict:
    query = req.get("query", "").lower().strip()
    limit = int(req.get("limit", 40))
    tools = arcpy.ListTools("*")  # e.g. "Buffer_analysis"
    if query:
        terms = query.split()
        tools = [t for t in tools if all(term in t.lower() for term in terms)]
    return {
        "id": req["id"],
        "ok": True,
        "total_matches": len(tools),
        "tools": sorted(tools)[:limit],
        "toolboxes": arcpy.ListToolboxes("*") if req.get("include_toolboxes") else None,
    }


def op_describe_tool(req: dict) -> dict:
    tool_name = req["tool"]
    usage = None
    try:
        usage = arcpy.Usage(tool_name)
    except Exception:
        pass
    func = getattr(arcpy, tool_name, None)
    doc = getattr(func, "__doc__", None) if func else None
    if usage is None and doc is None:
        raise AttributeError(f"Tool {tool_name!r} not found.")
    return {"id": req["id"], "ok": True, "usage": usage, "doc": doc}


# --------------------------------------------------------------------------
# op: describe_data — structured description of any dataset
# --------------------------------------------------------------------------

def op_describe_data(req: dict) -> dict:
    path = req["path"]
    d = arcpy.Describe(path)
    info: dict = {"path": path}
    for attr in (
        "dataType", "name", "baseName", "extension", "dataElementType",
        "shapeType", "featureType", "hasZ", "hasM", "workspaceType",
        "format", "bandCount", "compressionType",
    ):
        try:
            info[attr] = _jsonable(getattr(d, attr))
        except Exception:
            pass
    try:
        sr = d.spatialReference
        info["spatialReference"] = {
            "name": sr.name, "factoryCode": sr.factoryCode, "type": sr.type,
        }
    except Exception:
        pass
    try:
        ext = d.extent
        info["extent"] = {
            "xmin": ext.XMin, "ymin": ext.YMin, "xmax": ext.XMax, "ymax": ext.YMax,
        }
    except Exception:
        pass
    try:
        info["fields"] = [
            {"name": f.name, "type": f.type, "length": f.length, "alias": f.aliasName}
            for f in d.fields
        ]
    except Exception:
        pass
    try:
        info["rowCount"] = int(arcpy.management.GetCount(path)[0])
    except Exception:
        pass
    return {"id": req["id"], "ok": True, "description": info}


# --------------------------------------------------------------------------
# op: list_workspace — inventory feature classes / rasters / tables
# --------------------------------------------------------------------------

def op_list_workspace(req: dict) -> dict:
    path = req["path"]
    previous = arcpy.env.workspace
    arcpy.env.workspace = path
    try:
        result = {
            "workspace": path,
            "featureClasses": arcpy.ListFeatureClasses() or [],
            "rasters": arcpy.ListRasters() or [],
            "tables": arcpy.ListTables() or [],
            "datasets": arcpy.ListDatasets() or [],
        }
    finally:
        arcpy.env.workspace = previous
    return {"id": req["id"], "ok": True, **result}


# --------------------------------------------------------------------------
# op: inspect_project — maps, layers and layouts of an .aprx
# --------------------------------------------------------------------------

def op_inspect_project(req: dict) -> dict:
    path = req["path"]
    aprx = arcpy.mp.ArcGISProject(path)
    maps = []
    for m in aprx.listMaps():
        layers = []
        for lyr in m.listLayers():
            entry = {"name": lyr.name, "visible": lyr.visible}
            try:
                entry["dataSource"] = lyr.dataSource if lyr.supports("DATASOURCE") else None
            except Exception:
                entry["dataSource"] = None
            entry["isFeatureLayer"] = lyr.isFeatureLayer
            entry["isRasterLayer"] = lyr.isRasterLayer
            layers.append(entry)
        maps.append({
            "name": m.name,
            "mapType": m.mapType,
            "spatialReference": m.spatialReference.name,
            "layers": layers,
            "tables": [t.name for t in m.listTables()],
        })
    layouts = [
        {"name": l.name, "pageWidth": l.pageWidth, "pageHeight": l.pageHeight}
        for l in aprx.listLayouts()
    ]
    info = {
        "path": path,
        "defaultGeodatabase": aprx.defaultGeodatabase,
        "homeFolder": aprx.homeFolder,
        "maps": maps,
        "layouts": layouts,
    }
    del aprx  # release the project file lock promptly
    return {"id": req["id"], "ok": True, "project": info}


# --------------------------------------------------------------------------
# op: ping — health / license status
# --------------------------------------------------------------------------

def op_ping(req: dict) -> dict:
    return {
        "id": req["id"],
        "ok": True,
        "license": arcpy.ProductInfo(),
        "workspace": str(arcpy.env.workspace),
        "scratchGDB": str(arcpy.env.scratchGDB),
        "session_variables": [k for k in SESSION if not k.startswith("__")][:100],
    }


OPS = {
    "exec": op_exec,
    "run_tool": op_run_tool,
    "search_tools": op_search_tools,
    "describe_tool": op_describe_tool,
    "describe_data": op_describe_data,
    "list_workspace": op_list_workspace,
    "inspect_project": op_inspect_project,
    "ping": op_ping,
}


def main() -> None:
    global arcpy
    t0 = time.time()
    try:
        import arcpy as _arcpy  # slow: license checkout, ~20-60s cold
        arcpy = _arcpy
        SESSION["arcpy"] = arcpy
    except Exception as exc:
        _send({
            "event": "fatal",
            "error": f"{type(exc).__name__}: {exc}",
            "hint": "Is ArcGIS Pro licensed on this machine? Try opening Pro once.",
        })
        sys.exit(3)

    info = arcpy.GetInstallInfo()
    _send({
        "event": "ready",
        "product": info.get("ProductName"),
        "version": info.get("Version"),
        "license": arcpy.ProductInfo(),
        "startup_seconds": round(time.time() - t0, 1),
    })

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as exc:
            _send({"event": "protocol_error", "error": str(exc)})
            continue

        if req.get("op") == "shutdown":
            _send({"id": req.get("id"), "ok": True, "event": "bye"})
            break

        handler = OPS.get(req.get("op"))
        if handler is None:
            _send({"id": req.get("id"), "ok": False,
                   "error": f"Unknown op {req.get('op')!r}. Valid: {sorted(OPS)}"})
            continue

        try:
            _send(handler(req))
        except BaseException as exc:  # noqa: BLE001 — worker must never die mid-session
            _send(_error_payload(req.get("id"), exc))


if __name__ == "__main__":
    main()
