"""`arcclaude chat` — agentic AI GIS terminal (thin front end over agent.py)."""

from __future__ import annotations

import getpass
import sys

from .agent import CONFIG_FILE, AgentSession, load_config, save_config
from .live import paste_line


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
    save_config(cfg)
    print(f"Saved to {CONFIG_FILE}. Run: arcclaude chat  (or arcclaude app)")


def _emit_console(event: dict) -> None:
    kind = event.get("kind")
    if kind == "text":
        print("\n" + event["text"])
    elif kind == "tool_start":
        print(f"  ⚙ {event['tool']} ...", flush=True)
    elif kind == "tool_end" and not event.get("ok", True):
        print(f"    (tool reported an error - the AI will handle it)")
    elif kind == "error":
        print("\n✗ " + event["message"])


def cmd_chat(argv) -> None:
    session = AgentSession()
    if not session.provider:
        print("No AI provider configured. Run: arcclaude login")
        sys.exit(1)
    print(f"ARCclaude chat — {session.model} via {session.provider}. "
          "/exit to quit, /live for cowork setup.")
    try:
        while True:
            try:
                user = input("\nARCclaude » ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not user:
                continue
            if user in ("/exit", "/quit"):
                break
            if user == "/live":
                print("Paste into Pro's Python window:\n  " + paste_line())
                continue
            session.run_turn(user, _emit_console)
    finally:
        session.bridge.stop()
    print("bye.")
