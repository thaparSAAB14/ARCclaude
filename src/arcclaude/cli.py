"""ARCclaude command-line entry point.

  arcclaude              start the MCP server (stdio) - default, so existing
                         Claude Desktop/Code registrations keep working
  arcclaude serve        same, explicit
  arcclaude chat         agentic AI chat in your terminal (Codex-CLI style)
  arcclaude login        store an AI provider API key
  arcclaude live         print the one-liner that starts cowork mode in Pro
  arcclaude live stop    ask a running Pro listener to exit
"""

from __future__ import annotations

import sys

USAGE = __doc__


def main() -> None:
    argv = sys.argv[1:]
    cmd = argv[0] if argv else "serve"

    if cmd in ("-h", "--help", "help"):
        print(USAGE)
    elif cmd == "serve" or not argv:
        from .server import main as serve
        serve()
    elif cmd == "chat":
        from .chat import cmd_chat
        cmd_chat(argv[1:])
    elif cmd == "login":
        from .chat import cmd_login
        cmd_login(argv[1:])
    elif cmd == "live":
        from .live import paste_line, stop_listener, listener_alive
        if len(argv) > 1 and argv[1] == "stop":
            stop_listener()
            print("Stop signal sent to the Pro listener.")
        else:
            print("To start cowork mode, paste this ONE line into ArcGIS Pro's "
                  "Python window (View ribbon > Python):\n")
            print("  " + paste_line())
            print("\nListener currently running: "
                  + ("YES" if listener_alive() else "no"))
    else:
        print(f"Unknown command: {cmd}\n{USAGE}")
        sys.exit(2)


if __name__ == "__main__":
    main()
