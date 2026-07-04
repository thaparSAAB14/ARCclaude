"""Bridge between the MCP server and the persistent ArcPy worker process.

Spawns arcpy_worker.py on ArcGIS Pro's Python, speaks JSON-lines over the
worker's stdin/stdout, and enforces per-request timeouts. All access is
serialized with a lock — arcpy itself is not thread-safe.
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time
from pathlib import Path

from .discovery import find_arcgis_python

WORKER_PATH = Path(__file__).parent / "worker" / "arcpy_worker.py"
STARTUP_TIMEOUT = float(os.environ.get("ARCCLAUDE_STARTUP_TIMEOUT", "180"))
DEFAULT_TIMEOUT = float(os.environ.get("ARCCLAUDE_REQUEST_TIMEOUT", "300"))


class WorkerError(RuntimeError):
    """The worker failed, died, or timed out."""


class ArcPyBridge:
    def __init__(self) -> None:
        self._proc: subprocess.Popen | None = None
        self._lines: queue.Queue = queue.Queue()
        self._lock = threading.Lock()
        self._next_id = 0
        self.ready_info: dict = {}

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> dict:
        """Spawn the worker and block until arcpy is imported (slow)."""
        with self._lock:
            if self._proc and self._proc.poll() is None:
                return self.ready_info
            python = find_arcgis_python()
            env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
            self._proc = subprocess.Popen(
                [python, str(WORKER_PATH)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                env=env,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            self._lines = queue.Queue()
            threading.Thread(target=self._reader, args=(self._proc,), daemon=True).start()

            event = self._next_message(timeout=STARTUP_TIMEOUT)
            if event.get("event") == "ready":
                self.ready_info = event
                return event
            raise WorkerError(f"Worker failed to start: {event}")

    def stop(self) -> None:
        with self._lock:
            if self._proc and self._proc.poll() is None:
                try:
                    self._proc.stdin.write(json.dumps({"op": "shutdown"}) + "\n")
                    self._proc.stdin.flush()
                    self._proc.wait(timeout=10)
                except Exception:
                    self._proc.kill()
            self._proc = None
            self.ready_info = {}

    def restart(self) -> dict:
        self.stop()
        return self.start()

    @property
    def alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    # -- request/response ---------------------------------------------------

    def request(self, op: str, timeout: float | None = None, **fields) -> dict:
        """Send one op to the worker and wait for its matching response."""
        if not self.alive:
            self.start()
        timeout = timeout or DEFAULT_TIMEOUT
        with self._lock:
            self._next_id += 1
            req_id = self._next_id
            payload = {"id": req_id, "op": op, **fields}
            try:
                self._proc.stdin.write(json.dumps(payload) + "\n")
                self._proc.stdin.flush()
            except OSError as exc:
                raise WorkerError(f"Worker pipe broken: {exc}") from exc

            deadline = time.monotonic() + timeout
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    # A stuck arcpy call can't be interrupted — kill the session
                    # so the next request gets a fresh one.
                    self._proc.kill()
                    self._proc = None
                    self.ready_info = {}
                    raise WorkerError(
                        f"Request timed out after {timeout:.0f}s. The ArcPy session "
                        "was killed and will restart on the next call (state was lost)."
                    )
                msg = self._next_message(timeout=remaining)
                if msg.get("id") == req_id:
                    return msg
                # ignore stray events (e.g. protocol_error for garbage lines)

    # -- internals -----------------------------------------------------------

    def _reader(self, proc: subprocess.Popen) -> None:
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                self._lines.put(json.loads(line))
            except json.JSONDecodeError:
                self._lines.put({"event": "noise", "raw": line[:500]})
        self._lines.put({"event": "eof"})

    def _next_message(self, timeout: float) -> dict:
        try:
            msg = self._lines.get(timeout=timeout)
        except queue.Empty:
            raise WorkerError(f"No response from worker within {timeout:.0f}s")
        if msg.get("event") == "eof":
            raise WorkerError(
                "Worker process exited unexpectedly. It will restart on the next call."
            )
        return msg
