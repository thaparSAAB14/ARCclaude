# ARCclaude — Complete Setup Guide

From a blank Windows machine to an AI running geoprocessing in ArcGIS Pro. Takes about 10 minutes (plus ArcGIS Pro install time if you don't have it).

---

## 1. Prerequisites

| Requirement | Why | Check |
|---|---|---|
| Windows 10/11 | ArcGIS Pro is Windows-only | — |
| **ArcGIS Pro 3.x, licensed** | The engine ARCclaude drives | Open Pro once; if it runs, you're licensed |
| **Git** | Clone the repo | `git --version` |
| **uv** | Runs the server with zero Python setup | `uv --version` |

**Install uv** (if missing) — one command in PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Install Git** (if missing): `winget install Git.Git`

> **Note on licensing:** ARCclaude checks out your ArcGIS license the same way Pro's own Python window does. If your license is Named User, sign in to ArcGIS Pro at least once so the license is cached. Concurrent-use and Single-use licenses work out of the box.

---

## 2. Install ARCclaude

### Option A — automatic installer (recommended)

One line in PowerShell does everything below *and* section 4's client configuration:

```powershell
irm https://raw.githubusercontent.com/thaparSAAB14/ARCclaude/main/install.ps1 | iex
```

Or, from a downloaded/cloned copy, **double-click `install.cmd`**. The installer:
1. Verifies ArcGIS Pro is present (fails with guidance if not)
2. Installs `uv` if missing (official astral.sh installer)
3. Downloads the latest ARCclaude to `%LOCALAPPDATA%\ARCclaude` (or uses the local copy it's run from)
4. Creates the isolated Python environment (`uv sync`)
5. Verifies the server can start and find ArcGIS Pro
6. Auto-registers with Claude Code (globally) and Claude Desktop (merging safely into your existing config, with a `.bak` backup)

Flags: `-NoClientConfig` (skip step 6), `-RunTests` (run the full geoprocessing smoke test), `-InstallDir C:\somewhere` (custom location). Re-running the installer updates in place — it will stop any running ARCclaude server first.

### Option B — manual

```powershell
git clone https://github.com/thaparSAAB14/ARCclaude.git
cd ARCclaude
uv sync
```

Either way, **nothing is ever installed into Esri's Python environment**, and no admin rights are needed.

---

## 3. Verify it works

```powershell
uv run python tests\smoke_bridge.py
```

Expected: `12 passed, 0 failed` (takes ~1 minute — the first arcpy import checks out your license). If this passes, the full stack works: discovery → worker → real geoprocessing.

Optional full-protocol test: `uv run python tests\smoke_mcp.py` (expected `4 passed, 0 failed`).

---

## 4. Connect your AI client

### Claude Code

**Option A — project-scoped (zero config):** open the ARCclaude folder in Claude Code. It reads the repo's `.mcp.json` automatically and asks you to approve the server. Done.

**Option B — global (available in every project):**

```powershell
claude mcp add arcclaude --scope user -- uv --directory C:\path\to\ARCclaude run arcclaude
```

### Claude Desktop

Edit `%APPDATA%\Claude\claude_desktop_config.json` (create it if missing):

```json
{
  "mcpServers": {
    "arcclaude": {
      "command": "uv",
      "args": ["--directory", "C:\\path\\to\\ARCclaude", "run", "arcclaude"]
    }
  }
}
```

Restart Claude Desktop; you'll see the tools under the 🔌 icon.

### Cursor / Windsurf / other MCP clients

Same shape — stdio server, command `uv`, args `["--directory", "<repo path>", "run", "arcclaude"]`. For Cursor: Settings → MCP → Add new global MCP server.

### GPT / Gemini / local models

Any agent framework that supports MCP (OpenAI Agents SDK, LangChain MCP adapters, etc.) can connect the same way. ARCclaude is model-agnostic by design.

---

## 5. First run — what to expect

1. Ask your AI: **"Check the ArcGIS session status."** The first call takes **20–60 seconds** (arcpy license checkout). You should get back your license level (e.g. `ArcInfo`) and scratch workspace.
2. Then try something real:
   - *"Search for geoprocessing tools related to watersheds."*
   - *"Create 10 random points in a scratch feature class and buffer them by 1 km."*
   - *"Describe the data in C:\path\to\my.gdb."*
   - *"Open my project at C:\...\project.aprx and list every layer with a broken data source."*

The session is persistent — variables the AI creates in one step stay available for the next, so it can build long multi-step workflows.

---

## 6. Configuration (optional)

Set these as environment variables if the defaults don't fit:

| Variable | Purpose | Default |
|---|---|---|
| `ARCCLAUDE_ARCGIS_PYTHON` | Full path to `arcgispro-py3\python.exe` if auto-discovery fails (custom install drives, portable installs) | Registry → standard paths |
| `ARCCLAUDE_STARTUP_TIMEOUT` | Seconds to wait for the arcpy import | `180` |
| `ARCCLAUDE_REQUEST_TIMEOUT` | Default per-call timeout in seconds | `300` |

---

## 7. Troubleshooting

**"Could not locate ArcGIS Pro's Python"**
Pro is installed somewhere non-standard. Find `python.exe` under `<Pro install>\bin\Python\envs\arcgispro-py3\` and set `ARCCLAUDE_ARCGIS_PYTHON` to it.

**Worker fails with a licensing error / "fatal" on startup**
Open ArcGIS Pro once and sign in, then retry. Named User licenses need a cached sign-in; if your org uses concurrent licenses, check the license server is reachable.

**First call times out**
A cold arcpy import on a slow disk or during antivirus scanning can exceed the default. Set `ARCCLAUDE_STARTUP_TIMEOUT=300` and retry.

**"Request timed out … session was killed"**
That geoprocessing call ran past the per-call timeout. Re-run with a larger `timeout_seconds` on the tool call — the AI can pass it directly — or raise `ARCCLAUDE_REQUEST_TIMEOUT`. Note the session restarts fresh, so re-run any setup steps.

**Tool calls return "Worker process exited unexpectedly"**
Almost always an arcpy hard crash (access violation in a native tool). Just retry — the session auto-restarts. If reproducible, please file an issue with the code that triggered it.

**Schema locks on geodatabases**
The worker holds locks like any arcpy session while data is open. Ask the AI to run `restart_session` to release everything.

**Claude Code doesn't show the server**
Run `claude mcp list` to confirm registration. For project scope, make sure you opened the repo folder itself and approved the `.mcp.json` prompt.

---

## 8. Updating

```powershell
cd C:\path\to\ARCclaude
git pull
uv sync
```

Restart your MCP client (or the session) to pick up the new server.

## 9. Uninstalling

Delete the repo folder and remove the server entry from your client config. Nothing else was installed anywhere — Esri's environment was never touched.

---

## Security reminder

`arcpy_execute` runs arbitrary Python with your permissions — that's what makes it a universal copilot. Use clients that show and let you approve tool calls, and read what the AI is about to run before approving anything destructive. See the [README security model](../README.md#security-model).
