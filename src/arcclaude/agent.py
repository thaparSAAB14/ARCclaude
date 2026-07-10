"""Provider-agnostic agent core — shared by the chat CLI and the App.

An AgentSession holds the conversation and runs agentic turns (model call →
tool calls → model call …) against the ARCclaude engine, reporting progress
through an `emit(event_dict)` callback so any front end (terminal, web app,
future add-in) can render it.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .bridge import ArcPyBridge, WorkerError
from .live import live_execute, paste_line

CONFIG_FILE = Path.home() / ".arcclaude" / "config.json"
MAX_TOOL_CHARS = 24000

SYSTEM = """You are ARCclaude, an expert GIS copilot with full access to ArcGIS Pro via ArcPy.
The arcpy session is persistent: variables survive between arcpy_execute calls. The first
call is slow (~20-60s license checkout); later calls are fast. Prefer real geoprocessing
tools over reimplementing algorithms. Verify results (counts, extents) before declaring
success. pro_live_execute runs inside the user's OPEN ArcGIS Pro window (CURRENT project,
live map changes) and needs the user to start cowork mode; arcpy_execute is the headless
background session. Avoid rapid camera/view manipulation in the live session. Windows
paths. The user may be a GIS beginner: explain what you did in one or two plain sentences."""

TOOL_SPECS = [
    ("arcpy_execute",
     "Run Python in the persistent headless ArcPy session. arcpy is imported; variables "
     "persist; last bare expression is returned like a REPL.",
     {"code": ("string", "Python source to execute", True),
      "timeout_seconds": ("number", "kill+restart session after this many seconds (default 300)", False)}),
    ("pro_live_execute",
     "Run Python INSIDE the user's open ArcGIS Pro app (CURRENT project, live map). "
     "If no listener responds, relay the returned paste-line hint to the user.",
     {"code": ("string", "Python source to execute in the live session", True),
      "timeout_seconds": ("number", "seconds to wait for the live session (default 60)", False),
      "action": ("string", "name of the action being performed (e.g. 'Symbology', 'Buffer')", False)}),
    ("run_gp_tool",
     "Execute a geoprocessing tool by name ('Buffer_analysis' or 'analysis.Buffer').",
     {"tool": ("string", "tool name", True),
      "args": ("array", "positional parameters", False),
      "kwargs": ("object", "named parameters", False)}),
    ("search_gp_tools",
     "Search all ~1800 geoprocessing tools by space-separated AND terms.",
     {"query": ("string", "search terms", False),
      "limit": ("integer", "max results (default 40)", False)}),
    ("describe_gp_tool", "Get syntax + docs for a geoprocessing tool.",
     {"tool": ("string", "tool name", True)}),
    ("describe_data", "Describe a dataset: type, CRS, extent, fields, row count.",
     {"path": ("string", "dataset path", True)}),
    ("create_features",
     "Create a shapefile (.shp path) or geodatabase feature class from a GeoJSON "
     "FeatureCollection (WGS84). Fields auto-created; geometry type inferred.",
     {"geojson": ("string", "GeoJSON FeatureCollection as a string", True),
      "output_path": ("string", "output .shp path or gdb feature class path", True),
      "geometry_type": ("string", "POINT|MULTIPOINT|POLYLINE|POLYGON, only for mixed collections", False)}),
    ("export_features", "Read vector data back as GeoJSON (WGS84), optional SQL where filter.",
     {"path": ("string", "dataset path", True),
      "where": ("string", "SQL where clause", False),
      "limit": ("integer", "max features (default 1000)", False)}),
    ("list_workspace", "Inventory a geodatabase or folder.",
     {"path": ("string", "workspace path", True)}),
    ("inspect_project", "Maps, layers, layouts of an .aprx project file.",
     {"path": ("string", "path to .aprx", True)}),
    ("session_status", "ArcPy session status: license, workspace, variables.", {}),
    ("restart_session", "Restart the headless ArcPy session (clears state, releases locks).", {}),
]


def schema_for(params: dict) -> dict:
    return {
        "type": "object",
        "properties": {k: {"type": t, "description": d} for k, (t, d, _r) in params.items()},
        "required": [k for k, (_t, _d, r) in params.items() if r],
    }


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def save_config(cfg: dict) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except OSError:
        pass


def resolve_provider(cfg: dict) -> str | None:
    p = (os.environ.get("ARCCLAUDE_PROVIDER") or cfg.get("provider") or "").lower()
    if p:
        return p
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return None


def dispatch(bridge: ArcPyBridge, name: str, args: dict) -> str:
    """Execute one tool call against the engine; return a string for the model."""
    try:
        if name == "pro_live_execute":
            r = live_execute(args.get("code", ""),
                             timeout=float(args.get("timeout_seconds", 60)),
                             action=args.get("action"))
        elif name == "session_status":
            r = bridge.start() if not bridge.alive else bridge.request("ping", timeout=30)
        elif name == "restart_session":
            r = bridge.restart()
        elif name == "arcpy_execute":
            r = bridge.request("exec", timeout=float(args.get("timeout_seconds", 300)),
                               code=args.get("code", ""))
        elif name == "run_gp_tool":
            r = bridge.request("run_tool", timeout=600, tool=args.get("tool", ""),
                               args=args.get("args") or [], kwargs=args.get("kwargs") or {})
        elif name == "create_features":
            fields = {"geojson": args.get("geojson", ""), "path": args.get("output_path", "")}
            if args.get("geometry_type"):
                fields["geometry_type"] = str(args["geometry_type"]).upper()
            r = bridge.request("create_features", timeout=300, **fields)
        elif name == "export_features":
            r = bridge.request("export_features", timeout=300, path=args.get("path", ""),
                               where=args.get("where", ""), limit=int(args.get("limit", 1000)))
        elif name == "search_gp_tools":
            r = bridge.request("search_tools", query=args.get("query", ""),
                               limit=int(args.get("limit", 40)))
        elif name == "describe_gp_tool":
            r = bridge.request("describe_tool", tool=args.get("tool", ""))
        elif name == "describe_data":
            r = bridge.request("describe_data", path=args.get("path", ""))
        elif name == "list_workspace":
            r = bridge.request("list_workspace", path=args.get("path", ""))
        elif name == "inspect_project":
            r = bridge.request("inspect_project", path=args.get("path", ""), timeout=120)
        else:
            r = {"error": f"unknown tool {name}"}
    except (WorkerError, FileNotFoundError) as exc:
        r = {"error": str(exc)}
    out = json.dumps({k: v for k, v in r.items() if k != "id"},
                     ensure_ascii=False, default=repr)
    if len(out) > MAX_TOOL_CHARS:
        out = out[:MAX_TOOL_CHARS] + f'... [truncated, {len(out)} chars total]'
    return out


class AgentSession:
    """One conversation against one engine. Not thread-safe; one turn at a time."""

    def __init__(self, cfg: dict | None = None, bridge: ArcPyBridge | None = None):
        self.cfg = cfg if cfg is not None else load_config()
        self.bridge = bridge or ArcPyBridge()
        self.messages: list = []

    @property
    def provider(self) -> str | None:
        return resolve_provider(self.cfg)

    @property
    def model(self) -> str:
        default = "claude-sonnet-5" if self.provider == "anthropic" else "gpt-4o"
        return os.environ.get("ARCCLAUDE_MODEL") or self.cfg.get("model") or default

    def run_turn(self, user_text: str, emit) -> None:
        """Run one full agentic turn. emit(dict) receives:
        {"kind": "text"|"tool_start"|"tool_end"|"error"|"done", ...}"""
        if self.provider == "anthropic":
            self._turn_anthropic(user_text, emit)
        elif self.provider == "openai":
            self._turn_openai(user_text, emit)
        else:
            emit({"kind": "error",
                  "message": "No AI provider configured yet — open Settings and add a key."})
        emit({"kind": "done"})

    # -- providers ----------------------------------------------------------

    def _turn_anthropic(self, user_text: str, emit) -> None:
        import anthropic
        client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY") or self.cfg.get("api_key"))
        tools = [{"name": n, "description": d, "input_schema": schema_for(p)}
                 for n, d, p in TOOL_SPECS]
        self.messages.append({"role": "user", "content": user_text})
        while True:
            try:
                resp = client.messages.create(model=self.model, system=SYSTEM,
                                              max_tokens=4096, messages=self.messages,
                                              tools=tools)
            except anthropic.AuthenticationError:
                self.messages.pop()
                emit({"kind": "error", "message":
                      "Your API key was rejected (401). Get one at console.anthropic.com "
                      "and update it in Settings."})
                return
            except anthropic.APIError as exc:
                self.messages.pop()
                emit({"kind": "error", "message": f"API error: {exc}"})
                return
            self.messages.append({"role": "assistant", "content": resp.content})
            for block in resp.content:
                if block.type == "text" and block.text.strip():
                    emit({"kind": "text", "text": block.text.strip()})
            calls = [b for b in resp.content if b.type == "tool_use"]
            if not calls:
                return
            results = []
            for c in calls:
                emit({"kind": "tool_start", "tool": c.name})
                out = dispatch(self.bridge, c.name, dict(c.input))
                ok = '"error"' not in out[:200]
                emit({"kind": "tool_end", "tool": c.name, "ok": ok})
                results.append({"type": "tool_result", "tool_use_id": c.id, "content": out})
            self.messages.append({"role": "user", "content": results})

    def _turn_openai(self, user_text: str, emit) -> None:
        import openai
        client = openai.OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY") or self.cfg.get("api_key") or "local",
            base_url=self.cfg.get("base_url") or None)
        tools = [{"type": "function",
                  "function": {"name": n, "description": d, "parameters": schema_for(p)}}
                 for n, d, p in TOOL_SPECS]
        if not self.messages:
            self.messages.append({"role": "system", "content": SYSTEM})
        self.messages.append({"role": "user", "content": user_text})
        while True:
            try:
                resp = client.chat.completions.create(model=self.model,
                                                      messages=self.messages, tools=tools)
            except openai.AuthenticationError:
                self.messages.pop()
                emit({"kind": "error", "message":
                      "Your API key was rejected (401). Check the key/base URL in Settings."})
                return
            except openai.OpenAIError as exc:
                self.messages.pop()
                emit({"kind": "error", "message": f"API error: {exc}"})
                return
            msg = resp.choices[0].message
            self.messages.append({"role": "assistant", "content": msg.content,
                                  "tool_calls": msg.tool_calls})
            if msg.content and msg.content.strip():
                emit({"kind": "text", "text": msg.content.strip()})
            if not msg.tool_calls:
                return
            for tc in msg.tool_calls:
                emit({"kind": "tool_start", "tool": tc.function.name})
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                out = dispatch(self.bridge, tc.function.name, args)
                ok = '"error"' not in out[:200]
                emit({"kind": "tool_end", "tool": tc.function.name, "ok": ok})
                self.messages.append({"role": "tool", "tool_call_id": tc.id, "content": out})
