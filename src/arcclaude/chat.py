"""`arcclaude chat` — an agentic AI GIS terminal (Codex-CLI style).

Works with an Anthropic API key (Claude) or any OpenAI-compatible endpoint
(OpenAI, Gemini compat, Groq, local Ollama / LM Studio). Configure once with
`arcclaude login`; keys live in ~/.arcclaude/config.json or env vars
(ANTHROPIC_API_KEY / OPENAI_API_KEY).
"""

from __future__ import annotations

import getpass
import json
import os
import sys
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
background session. Windows paths. Be concise in prose; be careful with data."""

# One schema, both providers. (name, description, {param: (type, description, required)})
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
      "timeout_seconds": ("number", "seconds to wait for the live session (default 60)", False)}),
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


def _schema(params):
    return {
        "type": "object",
        "properties": {k: {"type": t, "description": d} for k, (t, d, _r) in params.items()},
        "required": [k for k, (_t, _d, r) in params.items() if r],
    }


def load_config() -> dict:
    cfg = {}
    if CONFIG_FILE.exists():
        try:
            cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return cfg


def cmd_login(argv) -> None:
    print("ARCclaude login — choose your AI provider:")
    print("  1) Anthropic API key (Claude models)")
    print("  2) OpenAI-compatible (OpenAI, Gemini compat, Groq, Ollama, LM Studio)")
    choice = input("Provider [1/2]: ").strip()
    cfg = load_config()
    if choice == "2":
        cfg["provider"] = "openai"
        base = input("Base URL (blank = api.openai.com; Ollama = http://localhost:11434/v1): ").strip()
        cfg["base_url"] = base or None
        cfg["model"] = input("Model (e.g. gpt-4o, llama3.1): ").strip() or "gpt-4o"
        key = getpass.getpass("API key (blank if local server): ").strip()
        cfg["api_key"] = key or "local"
    else:
        cfg["provider"] = "anthropic"
        cfg["model"] = input("Model [claude-sonnet-5]: ").strip() or "claude-sonnet-5"
        cfg["api_key"] = getpass.getpass("Anthropic API key (sk-ant-...): ").strip()
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except OSError:
        pass
    print(f"Saved to {CONFIG_FILE}. Run: arcclaude chat")


def _dispatch(bridge: ArcPyBridge, name: str, args: dict) -> str:
    """Execute one tool call against the core engine; return a string for the model."""
    try:
        if name == "pro_live_execute":
            r = live_execute(args.get("code", ""), timeout=float(args.get("timeout_seconds", 60)))
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
        elif name in ("search_gp_tools",):
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
    out = json.dumps({k: v for k, v in r.items() if k not in ("id",)},
                     ensure_ascii=False, default=repr)
    if len(out) > MAX_TOOL_CHARS:
        out = out[:MAX_TOOL_CHARS] + f'... [truncated, {len(out)} chars total]'
    return out


# ---------------------------------------------------------------- providers

def _run_anthropic(cfg, bridge):
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY") or cfg.get("api_key"))
    model = os.environ.get("ARCCLAUDE_MODEL") or cfg.get("model") or "claude-sonnet-5"
    tools = [{"name": n, "description": d, "input_schema": _schema(p)} for n, d, p in TOOL_SPECS]
    messages = []
    print(f"ARCclaude chat — {model} via Anthropic. /exit to quit, /live for cowork setup.")
    while True:
        try:
            user = input("\nARCclaude » ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user: continue
        if user in ("/exit", "/quit"): break
        if user == "/live":
            print("Paste into Pro's Python window:\n  " + paste_line()); continue
        messages.append({"role": "user", "content": user})
        while True:
            try:
                resp = client.messages.create(model=model, system=SYSTEM, max_tokens=4096,
                                              messages=messages, tools=tools)
            except anthropic.AuthenticationError:
                print("\n✗ Your API key was rejected (401). Get a key at "
                      "https://console.anthropic.com → API keys, then run: arcclaude login")
                messages.pop(); break
            except anthropic.APIError as exc:
                print(f"\n✗ API error: {exc}. Try again or run: arcclaude login")
                messages.pop(); break
            messages.append({"role": "assistant", "content": resp.content})
            for block in resp.content:
                if block.type == "text" and block.text.strip():
                    print("\n" + block.text.strip())
            calls = [b for b in resp.content if b.type == "tool_use"]
            if not calls: break
            results = []
            for c in calls:
                print(f"  ⚙ {c.name} ...", flush=True)
                results.append({"type": "tool_result", "tool_use_id": c.id,
                                "content": _dispatch(bridge, c.name, dict(c.input))})
            messages.append({"role": "user", "content": results})


def _run_openai(cfg, bridge):
    import openai
    client = openai.OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY") or cfg.get("api_key") or "local",
        base_url=cfg.get("base_url") or None)
    model = os.environ.get("ARCCLAUDE_MODEL") or cfg.get("model") or "gpt-4o"
    tools = [{"type": "function",
              "function": {"name": n, "description": d, "parameters": _schema(p)}}
             for n, d, p in TOOL_SPECS]
    messages = [{"role": "system", "content": SYSTEM}]
    print(f"ARCclaude chat — {model} via OpenAI-compatible API. /exit to quit.")
    while True:
        try:
            user = input("\nARCclaude » ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user: continue
        if user in ("/exit", "/quit"): break
        if user == "/live":
            print("Paste into Pro's Python window:\n  " + paste_line()); continue
        messages.append({"role": "user", "content": user})
        while True:
            try:
                resp = client.chat.completions.create(model=model, messages=messages, tools=tools)
            except openai.AuthenticationError:
                print("\n✗ Your API key was rejected (401). Check the key/base URL, "
                      "then run: arcclaude login")
                messages.pop(); break
            except openai.OpenAIError as exc:
                print(f"\n✗ API error: {exc}. Try again or run: arcclaude login")
                messages.pop(); break
            msg = resp.choices[0].message
            messages.append({"role": "assistant", "content": msg.content,
                             "tool_calls": msg.tool_calls})
            if msg.content and msg.content.strip():
                print("\n" + msg.content.strip())
            if not msg.tool_calls: break
            for tc in msg.tool_calls:
                print(f"  ⚙ {tc.function.name} ...", flush=True)
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                messages.append({"role": "tool", "tool_call_id": tc.id,
                                 "content": _dispatch(bridge, tc.function.name, args)})


def cmd_chat(argv) -> None:
    cfg = load_config()
    provider = (os.environ.get("ARCCLAUDE_PROVIDER") or cfg.get("provider") or "").lower()
    if not provider:
        if os.environ.get("ANTHROPIC_API_KEY"):
            provider = "anthropic"
        elif os.environ.get("OPENAI_API_KEY"):
            provider = "openai"
        else:
            print("No AI provider configured. Run: arcclaude login")
            sys.exit(1)
    bridge = ArcPyBridge()
    try:
        if provider == "anthropic":
            _run_anthropic(cfg, bridge)
        else:
            _run_openai(cfg, bridge)
    finally:
        bridge.stop()
    print("bye.")
