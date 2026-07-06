"""ARCclaude Live Link listener — paste into ArcGIS Pro's Python window.

    exec(open(r"<this file>").read()); arcclaude_live()

Runs a cowork loop INSIDE the live Pro session: polls ~/.arcclaude/live/ for
command files dropped by an AI (MCP server or arcclaude chat) and executes
them with full access to the open application — arcpy.mp.ArcGISProject
("CURRENT"), the active map, live redraws, project saves.

Stdlib-only, self-contained (it is exec'd, not imported). Stop it by letting
it time out, or from the AI side via the stop command, or by creating a file
named 'stop' in the queue folder.
"""

import ast as _ast
import contextlib as _contextlib
import io as _io
import json as _json
import os as _os
import time as _time
import traceback as _traceback
from pathlib import Path as _Path

_ARCCLAUDE_LIVE_DIR = _Path(_os.environ.get("ARCCLAUDE_LIVE_DIR")
                            or _Path.home() / ".arcclaude" / "live")
_ARCCLAUDE_NS = {"__name__": "__arcclaude_live__"}


def _arcclaude_run(code):
    buf = _io.StringIO()
    resp = {"ok": True}
    try:
        tree = _ast.parse(code, mode="exec")
        last = None
        if tree.body and isinstance(tree.body[-1], _ast.Expr):
            last = _ast.Expression(tree.body.pop(-1).value)
        with _contextlib.redirect_stdout(buf), _contextlib.redirect_stderr(buf):
            exec(compile(tree, "<arcclaude-live>", "exec"), _ARCCLAUDE_NS)
            if last is not None:
                value = eval(compile(last, "<arcclaude-live>", "eval"), _ARCCLAUDE_NS)
                if value is not None:
                    resp["result"] = repr(value)
    except BaseException as exc:  # keep the listener alive no matter what
        resp = {"ok": False, "error": f"{type(exc).__name__}: {exc}",
                "traceback": _traceback.format_exc(limit=15)}
    resp["stdout"] = buf.getvalue()
    return resp


def arcclaude_live(minutes=45, poll=0.5, idle_minutes=10):
    """Cowork mode: execute queued AI commands inside this Pro session.

    IMPORTANT: while active, this loop keeps the Python window busy — don't
    type further commands there, and don't close Pro to stop it. Stop it from
    any terminal with `arcclaude live stop` (or wait for the idle timeout).
    """
    try:
        import arcpy  # noqa: F401 — preload into the shared namespace
        _ARCCLAUDE_NS["arcpy"] = arcpy
    except ImportError:
        print("arcclaude live: WARNING - arcpy not importable here.")

    _ARCCLAUDE_LIVE_DIR.mkdir(parents=True, exist_ok=True)
    stop_file = _ARCCLAUDE_LIVE_DIR / "stop"
    if stop_file.exists():
        stop_file.unlink()
    # purge leftovers from previous sessions so nothing stale ever replays
    for old in list(_ARCCLAUDE_LIVE_DIR.glob("cmd_*")) + list(_ARCCLAUDE_LIVE_DIR.glob("result_*")):
        try:
            old.unlink()
        except OSError:
            pass
    heartbeat = _ARCCLAUDE_LIVE_DIR / "heartbeat"
    deadline = _time.time() + minutes * 60
    last_activity = _time.time()
    print(f"ARCclaude Live Link ACTIVE (max {minutes} min, auto-exits after "
          f"{idle_minutes} idle min).")
    print("  While active, this Python window is busy - don't type here.")
    print("  To stop from a terminal:  uv run arcclaude live stop")

    done = 0
    try:
        while _time.time() < deadline:
            if stop_file.exists():
                stop_file.unlink()
                print("ARCclaude Live Link: stop requested - exiting.")
                break
            if _time.time() - last_activity > idle_minutes * 60:
                print(f"ARCclaude Live Link: no commands for {idle_minutes} min - "
                      "exiting so the Python window is free again. Re-paste to resume.")
                break
            try:
                heartbeat.write_text(str(_time.time()))
            except OSError:
                pass
            for cmd_file in sorted(_ARCCLAUDE_LIVE_DIR.glob("cmd_*.json")):
                try:
                    req = _json.loads(cmd_file.read_text(encoding="utf-8"))
                except (OSError, _json.JSONDecodeError):
                    continue
                try:
                    cmd_file.unlink()
                except OSError:
                    continue  # another listener claimed it
                resp = _arcclaude_run(req.get("code", ""))
                resp["id"] = req.get("id")
                tmp = _ARCCLAUDE_LIVE_DIR / (f"result_{req.get('id')}.tmp")
                out = _ARCCLAUDE_LIVE_DIR / (f"result_{req.get('id')}.json")
                tmp.write_text(_json.dumps(resp, ensure_ascii=False, default=repr),
                               encoding="utf-8")
                _os.replace(tmp, out)
                done += 1
                last_activity = _time.time()
                status = "ok" if resp.get("ok") else "ERROR"
                print(f"  [{done}] executed command {req.get('id')} -> {status}")
                _time.sleep(0.1)  # let Pro breathe between commands
            _time.sleep(poll)
    except KeyboardInterrupt:
        print("ARCclaude Live Link: interrupted - exiting.")
    finally:
        try:
            heartbeat.unlink()
        except OSError:
            pass
    print(f"ARCclaude Live Link ended ({done} commands executed).")


if __name__ == "__main__":
    arcclaude_live(minutes=float(_os.environ.get("ARCCLAUDE_LIVE_MINUTES", "120")))
