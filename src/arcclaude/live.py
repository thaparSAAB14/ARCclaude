"""Live Link client — drive the OPEN ArcGIS Pro session.

An external process can't touch a running Pro app or its locked .aprx. The
Live Link works around that with a file command queue: the user pastes one
line into Pro's Python window (see worker/live_listener.py), and Pro's own
Python polls ~/.arcclaude/live/ and executes what it finds — inside the live
session, where arcpy.mp.ArcGISProject("CURRENT") and live map redraws work.

This module is the sending side, used by the MCP server and the chat CLI.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

LIVE_DIR = Path(os.environ.get("ARCCLAUDE_LIVE_DIR")
                or Path.home() / ".arcclaude" / "live")
LISTENER_PATH = Path(__file__).parent / "worker" / "live_listener.py"


def paste_line() -> str:
    """The one-liner the user pastes into ArcGIS Pro's Python window."""
    return (
        f'exec(open(r"{LISTENER_PATH}").read()); arcclaude_live()'
    )


def listener_alive(max_age_seconds: float = 5.0) -> bool:
    """True if a listener heartbeat has been written recently."""
    hb = LIVE_DIR / "heartbeat"
    try:
        return (time.time() - hb.stat().st_mtime) < max_age_seconds
    except OSError:
        return False


def live_execute(code: str, timeout: float = 60.0) -> dict:
    """Queue code for the live Pro session and wait for its result."""
    LIVE_DIR.mkdir(parents=True, exist_ok=True)
    cmd_id = uuid.uuid4().hex[:12]
    cmd_tmp = LIVE_DIR / f"cmd_{cmd_id}.tmp"
    cmd_file = LIVE_DIR / f"cmd_{cmd_id}.json"
    result_file = LIVE_DIR / f"result_{cmd_id}.json"

    cmd_tmp.write_text(json.dumps({"id": cmd_id, "code": code}), encoding="utf-8")
    os.replace(cmd_tmp, cmd_file)  # atomic: listener never sees partial files

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if result_file.exists():
            try:
                payload = json.loads(result_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                time.sleep(0.1)
                continue
            try:
                result_file.unlink()
            except OSError:
                pass
            return payload
        time.sleep(0.25)

    try:
        cmd_file.unlink()  # withdraw the command
    except OSError:
        pass
    hint = (
        "No ArcGIS Pro listener responded. In ArcGIS Pro, open the Python "
        "window (View ribbon > Python) and paste this one line to start "
        "cowork mode:\n  " + paste_line()
    )
    if listener_alive():
        hint = ("A listener heartbeat exists but the command timed out - the "
                "live session may be busy with a long operation.")
    return {"ok": False, "error": f"Live Link timeout after {timeout:.0f}s.", "hint": hint}


def stop_listener() -> bool:
    """Ask a running listener to exit."""
    LIVE_DIR.mkdir(parents=True, exist_ok=True)
    (LIVE_DIR / "stop").write_text("stop", encoding="utf-8")
    return True
