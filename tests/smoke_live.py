"""Smoke test: Live Link file-queue round trip.

Simulates the in-Pro listener with a plain Python subprocess (the queue
mechanics are identical; only arcpy is absent). Run:
    uv run python tests/smoke_live.py
"""

import subprocess
import sys
import time
from pathlib import Path

from arcclaude.live import LIVE_DIR, LISTENER_PATH, live_execute, stop_listener, listener_alive

PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  PASS  {name}")
    else:
        FAIL += 1; print(f"  FAIL  {name}  {detail}")


def main() -> int:
    LIVE_DIR.mkdir(parents=True, exist_ok=True)
    for leftover in list(LIVE_DIR.glob("cmd_*")) + list(LIVE_DIR.glob("result_*")):
        leftover.unlink()

    print("== timeout path (no listener) ==")
    r = live_execute("1+1", timeout=2)
    check("times out with paste-line hint",
          r.get("ok") is False and "Python window" in r.get("hint", ""), str(r)[:200])

    print("== round trip with simulated listener ==")
    proc = subprocess.Popen([sys.executable, str(LISTENER_PATH)],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        deadline = time.time() + 15
        while not listener_alive() and time.time() < deadline:
            time.sleep(0.3)
        check("listener heartbeat", listener_alive())

        r = live_execute("x = 40\nx + 2", timeout=15)
        check("executes code", r.get("ok") is True and r.get("result") == "42", str(r)[:200])

        r = live_execute("x * 10", timeout=15)
        check("namespace persists", r.get("result") == "400", str(r)[:200])

        r = live_execute("1/0", timeout=15)
        check("errors survive", r.get("ok") is False and "ZeroDivisionError" in r.get("error", ""),
              str(r)[:200])

        r = live_execute("'still alive'", timeout=15)
        check("listener alive after error", r.get("result") == "'still alive'", str(r)[:200])

        print("== stop signal ==")
        stop_listener()
        try:
            proc.wait(timeout=10)
            check("listener exits on stop", True)
        except subprocess.TimeoutExpired:
            check("listener exits on stop", False, "still running")
    finally:
        if proc.poll() is None:
            proc.kill()

    print(f"\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
