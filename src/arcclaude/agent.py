"""Provider-agnostic agent core — shared by the chat CLI and the App.

An AgentSession holds the conversation and runs agentic turns (model call →
tool calls → model call …) against the ARCclaude engine, reporting progress
through an `emit(event_dict)` callback so any front end (terminal, web app,
future add-in) can render it.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from . import server
from .bridge import ArcPyBridge

CONFIG_FILE = Path.home() / ".arcclaude" / "config.json"
MAX_TOOL_CHARS = 24000

SYSTEM = """You are ARCclaude, an expert GIS copilot with full access to ArcGIS Pro via ArcPy.
The arcpy session is persistent: variables survive between arcpy_execute calls. The first
call is slow (~20-60s license checkout); later calls are fast. Prefer real geoprocessing
tools over reimplementing algorithms. Verify results (counts, extents) before declaring
success. pro_live_execute runs inside the user's OPEN ArcGIS Pro window (CURRENT project,
live map changes) and needs the user to start cowork mode; arcpy_execute is the headless
background session. Avoid rapid camera/view manipulation in the live session. Windows
paths. The user may be a GIS beginner: explain what you did in one or two plain sentences.

House rules (the user relies on these):
1. Work inside the CURRENT project. Never create or save new .aprx files, never add
   duplicate maps, layout tabs, or copies of layers for the same data - prefer updating
   symbology or properties in place. Only create new layers/maps/layouts when the user
   explicitly asks.
2. Show changes instantly: after modifying a map or layout in the live session, activate
   its view (e.g. lyt.openView() / map.openView()) so the user sees it without clicking.
3. Always pass a short human-friendly `action` label to pro_live_execute (e.g.
   "Applying symbology", "Calculating buffer") - it appears in the user's add-in log.
   Narrate progress in plain language, never raw step numbers or jargon.
4. Anticipate non-technical users: validate paths, shapefile field-name limits (10 chars),
   layer order and coordinate systems before running; if you auto-fix a mismatch (e.g.
   reproject to match the map), say what you fixed and why in one plain sentence."""

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


def tool_defs() -> list[tuple[str, str, dict]]:
    """(name, description, json-schema) for every MCP tool, read from the
    server itself. One source of truth: a tool added to server.py shows up
    here, in both provider adapters, and in dispatch() with no other edits."""
    return [(t.name, t.description or "", t.inputSchema)
            for t in asyncio.run(server.mcp.list_tools())]


def dispatch(name: str, args: dict) -> str:
    """Execute one tool call through the MCP server; return text for the model."""
    try:
        result = asyncio.run(server.mcp.call_tool(name, args))
    except Exception as exc:  # a failed tool must not end the conversation
        return json.dumps({"error": f"{type(exc).__name__}: {exc}"})
    blocks = result[0] if isinstance(result, tuple) else result
    out = "\n".join(getattr(b, "text", "") for b in blocks)
    if len(out) > MAX_TOOL_CHARS:
        out = out[:MAX_TOOL_CHARS] + f"... [truncated, {len(out)} chars total]"
    return out


class AgentSession:
    """One conversation against one engine. Not thread-safe; one turn at a time."""

    def __init__(self, cfg: dict | None = None, bridge: ArcPyBridge | None = None):
        self.cfg = cfg if cfg is not None else load_config()
        # Tools run through the MCP server, so share its bridge - one ArcGIS
        # session per process, not one per front end.
        self.bridge = bridge or server.bridge
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
        tools = [{"name": n, "description": d, "input_schema": schema}
                 for n, d, schema in tool_defs()]
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
                out = dispatch(c.name, dict(c.input))
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
                  "function": {"name": n, "description": d, "parameters": schema}}
                 for n, d, schema in tool_defs()]
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
                out = dispatch(tc.function.name, args)
                ok = '"error"' not in out[:200]
                emit({"kind": "tool_end", "tool": tc.function.name, "ok": ok})
                self.messages.append({"role": "tool", "tool_call_id": tc.id, "content": out})
