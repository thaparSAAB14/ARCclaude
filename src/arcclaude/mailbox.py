"""Chat relay between the ArcGIS Pro pane and a connected AI app.

The Live Link already moves work into Pro through a file queue (see live.py):
the add-in polls ~/.arcclaude/live/ and executes what it finds. The same
directory carries the conversation, so there is no second transport to install,
secure or explain.

One file per message, written to .tmp and renamed into place, exactly as live.py
does. Writers never collide: a reader only ever sees complete files, and two
writers cannot lose each other's messages the way a shared inbox.json would.

Readers are serialised by a lock rather than by the filesystem — see _drain for
why Windows leaves no cheaper option.

  in_*.json   the user typed this in Pro   -> the AI reads it with read_chat
  out_*.json  the AI answered              -> the pane shows it

Stdlib only: this is imported on both sides of the link, including inside Pro's
locked arcgispro-py3 environment.
"""

from __future__ import annotations

import itertools
import json
import os
import threading
import time
import uuid
from pathlib import Path

from .live import LIVE_DIR

CHAT_DIR = LIVE_DIR / "chat"
IN, OUT = "in", "out"

# Ordering is by filename, so the name has to sort correctly on its own.
# A float timestamp alone does not: a tight loop posts several messages inside
# one clock tick, and the uuid then decided their order at random. Nanoseconds
# separate writers in different processes, the counter separates writes in this
# one, and both are zero-padded so the comparison stays lexicographic.
_seq = itertools.count()


def _post(prefix: str, text: str) -> Path:
    CHAT_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"{prefix}_{time.time_ns():019d}_{next(_seq):06d}_{uuid.uuid4().hex[:8]}"
    tmp = CHAT_DIR / (stem + ".tmp")
    final = CHAT_DIR / (stem + ".json")
    tmp.write_text(json.dumps({"text": text, "at": time.time()}), encoding="utf-8")
    os.replace(tmp, final)  # atomic: a reader never sees a half-written message
    return final


# One drain at a time in this process. Windows will not give us a cheaper
# guarantee: measured under four concurrent readers, both os.unlink and
# os.rename reported success for the SAME file more than once (651 "successful"
# claims for 300 files), because a delete-pending entry still answers. So a
# filesystem-level claim cannot be the serialisation point here, and this lock
# is. It makes the case that actually occurs — several threads inside the MCP
# server, or inside the pane — exactly-once and deterministic.
# ponytail: in-process lock. Two separate processes draining the SAME direction
# at once could still double-deliver; that needs a real cross-process lock
# (msvcrt.locking / a lock file), and it is not a shape this product has — the
# server owns `in_*` and the pane owns `out_*`.
_drain_lock = threading.Lock()


def _drain(prefix: str) -> list[dict]:
    """Everything waiting in one direction, delivered once."""
    if not CHAT_DIR.exists():
        return []
    out = []
    with _drain_lock:
        for path in sorted(CHAT_DIR.glob(f"{prefix}_*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except ValueError:
                path.unlink(missing_ok=True)  # corrupt: drop, do not retry forever
                continue
            except OSError:
                continue  # vanished between the glob and the read
            path.unlink(missing_ok=True)
            out.append(payload)
    return out


def _count(prefix: str) -> int:
    return len(list(CHAT_DIR.glob(f"{prefix}_*.json"))) if CHAT_DIR.exists() else 0


def post_user(text: str) -> None:
    """Pro pane: the user said this, and a connected app should answer it."""
    _post(IN, text)


def take_user() -> list[dict]:
    """AI: everything typed since the last call. Draining is the delivery
    receipt, so a crashed client loses messages rather than replaying them."""
    return _drain(IN)


def post_reply(text: str) -> None:
    """AI: show this in the Pro pane."""
    _post(OUT, text)


def take_replies() -> list[dict]:
    """Pro pane: answers waiting to be rendered."""
    return _drain(OUT)


def pending() -> tuple[int, int]:
    """(messages waiting for the AI, replies waiting for the pane)."""
    return _count(IN), _count(OUT)


def reset() -> None:
    """Tests only: forget every queued message, including any half-written or
    claimed-but-not-deleted leftovers."""
    if not CHAT_DIR.exists():
        return
    for path in CHAT_DIR.iterdir():
        if path.is_file():
            path.unlink(missing_ok=True)
