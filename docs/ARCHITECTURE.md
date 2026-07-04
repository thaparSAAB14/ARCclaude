# ARCclaude Architecture

## Overview

```
┌──────────────────────────────────────────────┐
│  MCP client (Claude Code, Claude Desktop,    │
│  Cursor, GPT/Gemini via adapters, agents)    │
└──────────────────┬───────────────────────────┘
                   │ MCP over stdio
┌──────────────────▼───────────────────────────┐
│  ARCclaude MCP server  (src/arcclaude)       │
│  • FastMCP tool definitions   server.py      │
│  • Worker lifecycle + timeouts bridge.py     │
│  • Pro install discovery      discovery.py   │
│  Runs on its own Python, managed by uv       │
└──────────────────┬───────────────────────────┘
                   │ JSON lines over stdin/stdout
┌──────────────────▼───────────────────────────┐
│  ArcPy worker  (worker/arcpy_worker.py)      │
│  • stdlib + arcpy ONLY                       │
│  • persistent exec namespace (REPL-like)     │
│  Runs on Esri's arcgispro-py3 Python         │
└──────────────────┬───────────────────────────┘
                   │
            ArcGIS Pro install
     (license, toolboxes, extensions)
```

## Why two processes?

**Problem:** the MCP SDK needs modern third-party packages, but Esri's
`arcgispro-py3` environment lives under `Program Files`, is version-locked,
and installing into it requires admin rights and risks breaking Pro.
The conventional workaround — cloning the conda environment — is slow,
multi-GB, and fragile across Pro upgrades.

**Solution:** split the system at the package boundary.

- The **server** owns all third-party dependencies (`mcp`, etc.) in a tiny
  uv-managed environment.
- The **worker** owns arcpy and imports *nothing else* beyond the standard
  library, so Esri's environment is used exactly as shipped. Zero install
  footprint, upgrade-proof, no admin rights.

## Why a persistent worker?

`import arcpy` takes 20–60 s cold (license checkout). Paying that per call
would make the copilot unusable. The worker imports once and then serves
requests indefinitely. A side benefit: the exec namespace persists, so the
AI works like a human in a Python window — building variables, loading
layers, iterating on an analysis across many tool calls.

## Worker protocol

JSON lines on stdin/stdout, matched by `id`:

```
→ {"id": 7, "op": "exec", "code": "x = 1"}
← {"id": 7, "ok": true, "stdout": ""}

→ {"id": 8, "op": "run_tool", "tool": "analysis.Buffer",
   "args": [], "kwargs": {"in_features": "...", ...}}
← {"id": 8, "ok": true, "outputs": ["..."], "messages": "..."}
```

Startup handshake: the worker emits `{"event": "ready", ...}` after arcpy
imports, or `{"event": "fatal", ...}` if licensing fails.

Ops implemented: `exec`, `run_tool`, `search_tools`, `describe_tool`,
`describe_data`, `list_workspace`, `inspect_project`, `ping`, `shutdown`.

### Design rules for ops

1. **`exec` is the universal escape hatch.** Anything ArcPy can do is
   reachable through it. Every other op exists to make a common operation
   *structured and reliable* (typed JSON out instead of parsing prints).
2. **The worker never dies on user errors.** Exceptions are caught, encoded
   (with traceback and `arcpy.GetMessages()`), and returned; the session
   survives. Only a bridge-enforced timeout kills the process.
3. **Dynamic over static.** Tools are discovered at runtime with
   `arcpy.ListTools()`, so extension toolboxes appear automatically. We do
   not hand-map 1800 tools into 1800 MCP tools — the model discovers, reads
   docs, and executes.

## Timeouts and cancellation

arcpy calls are blocking and cannot be interrupted from Python. The bridge
enforces deadlines: on timeout it kills the worker and reports that state
was lost; the next request transparently starts a fresh session. Default
request timeout 300 s (configurable per call and via
`ARCCLAUDE_REQUEST_TIMEOUT`).

## Discovery

`discovery.py` resolves the arcgispro-py3 interpreter:

1. `ARCCLAUDE_ARCGIS_PYTHON` env var (explicit override)
2. Registry `HKLM/HKCU SOFTWARE\ESRI\ArcGISPro → InstallDir`
3. Known default install paths

## Threading model

The MCP server may receive concurrent tool calls; the bridge serializes all
worker access behind a lock because arcpy is not thread-safe and the session
is single-threaded by design (matching Pro's own Python window).

## Extension points (roadmap)

- **Live Pro session control:** a .NET add-in (ArcGIS Pro SDK) hosting a
  local bridge, letting the AI drive the *open* application — active map,
  selections, editing sessions, camera. Same MCP surface, second backend.
- **ArcGIS Online / Enterprise:** the `arcgis` Python API in a separate
  worker (it's pip-installable, so it can live in the server env).
- **Open-data connectors:** STAC, OSM, CKAN etc. as ordinary MCP tools in
  the server process — no arcpy needed.
- **Structured tool schemas:** generate per-tool JSON schemas from
  `arcpy.GetParameterInfo()` for richer client-side validation.
