"""End-to-end smoke test: real MCP client -> stdio server -> arcpy worker.

Run:  uv run python tests/smoke_mcp.py
This is exactly how Claude Code will talk to ARCclaude.
"""

import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {detail}")


async def main() -> int:
    params = StdioServerParameters(command="uv", args=["run", "arcclaude"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            print("== list_tools ==")
            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
            expected = {
                "arcpy_execute", "run_gp_tool", "search_gp_tools",
                "describe_gp_tool", "describe_data", "create_features",
                "export_features", "list_workspace", "inspect_project",
                "session_status", "restart_session", "pro_live_execute",
            }
            check(f"all 12 tools exposed ({len(names)})", expected <= names,
                  f"missing: {expected - names}")

            print("== session_status (cold start, slow) ==")
            r = await session.call_tool("session_status", {})
            text = r.content[0].text
            check("session started", "ArcGISPro" in text or "license" in text, text[:300])

            print("== arcpy_execute via MCP ==")
            r = await session.call_tool(
                "arcpy_execute", {"code": "arcpy.ProductInfo()"})
            text = r.content[0].text
            check("returns license via arcpy", "ArcInfo" in text, text[:300])

            print("== search_gp_tools via MCP ==")
            r = await session.call_tool("search_gp_tools", {"query": "clip"})
            text = r.content[0].text
            check("finds Clip tools", "Clip_analysis" in text, text[:300])

            print(f"\n{PASS} passed, {FAIL} failed")
            return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
