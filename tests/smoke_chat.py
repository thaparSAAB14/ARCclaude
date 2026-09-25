"""Smoke test for the chat relay: the Pro pane and a connected AI app talking
through the Live Link's file queue. No ArcGIS, no network, no license.

Run:  python tests/smoke_chat.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# Point the Live Link at a scratch directory before anything imports it, so the
# test never touches a real session's queue.
_tmp = tempfile.mkdtemp(prefix="arcclaude_chat_")
os.environ["ARCCLAUDE_LIVE_DIR"] = _tmp

from arcclaude import mailbox  # noqa: E402

assert str(mailbox.CHAT_DIR).startswith(_tmp), (
    f"the relay must honour ARCCLAUDE_LIVE_DIR, got {mailbox.CHAT_DIR}"
)

mailbox.reset()
assert mailbox.take_user() == [] and mailbox.take_replies() == []
assert mailbox.pending() == (0, 0)

# Ordering is by filename, so a burst inside one clock tick is the case that
# breaks it — a float timestamp alone let the uuid decide the order at random.
for i in range(25):
    mailbox.post_user(f"m{i}")
assert mailbox.pending() == (25, 0)
assert [m["text"] for m in mailbox.take_user()] == [f"m{i}" for i in range(25)]
mailbox.reset()

# --- the MCP tools -------------------------------------------------------
from arcclaude import server  # noqa: E402

read_chat = server.read_chat.fn if hasattr(server.read_chat, "fn") else server.read_chat
send_chat = server.send_chat.fn if hasattr(server.send_chat, "fn") else server.send_chat

assert read_chat() == "(no new messages)", "an empty inbox must not block"

mailbox.post_user("clip the roads to the city boundary")
mailbox.post_user("then export a PNG")
drained = read_chat()
assert "clip the roads to the city boundary" in drained, drained
assert "then export a PNG" in drained, drained
assert drained.index("clip") < drained.index("then export"), "messages arrived out of order"
assert read_chat() == "(no new messages)", "messages replayed after delivery"

# replies travel the other way and do not leak into the inbox
assert send_chat("clipped: 2,883 -> 1,204 features") == "shown in the ARCclaude pane"
assert read_chat() == "(no new messages)", "a reply surfaced as a user message"
shown = [m["text"] for m in mailbox.take_replies()]
assert shown == ["clipped: 2,883 -> 1,204 features"], shown

# a backlog is reported honestly rather than silently dropped
send_chat("one")
second = send_chat("two")
assert "2 replies waiting" in second, second
assert len(mailbox.take_replies()) == 2

# an empty reply is refused, not queued as a blank bubble
assert "error" in send_chat("   ")
assert mailbox.take_replies() == []

# both directions survive a restart: the queue is on disk, not in memory
mailbox.post_user("still here after a reload")
import importlib  # noqa: E402

importlib.reload(mailbox)
assert [m["text"] for m in mailbox.take_user()] == ["still here after a reload"]

mailbox.reset()
assert mailbox.pending() == (0, 0)

import shutil  # noqa: E402

shutil.rmtree(_tmp, ignore_errors=True)
print("smoke_chat: all green")
