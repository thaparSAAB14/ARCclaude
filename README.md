# ARCclaude

**An open-source MCP server that gives AI assistants complete access to the ArcGIS Pro ecosystem.**

ARCclaude connects Large Language Models — Claude, GPT, Gemini, local models, or anything that speaks [MCP](https://modelcontextprotocol.io) — to ArcGIS Pro through ArcPy. It is not a chatbot that answers GIS questions: it's a copilot that *does the work* — running geoprocessing tools, writing and debugging ArcPy, inspecting projects and data, automating maps, and building complete analysis pipelines from natural language.

> "Buffer every school in the city by 500 m, clip to the district boundary, and tell me how many parcels intersect" — and it actually happens, in your local ArcGIS Pro install, with full messages and outputs reported back.

## How it works

```
Claude / GPT / any MCP client
        │  MCP over stdio
        ▼
ARCclaude server (lightweight Python, managed by uv)
        │  JSON-lines over pipes
        ▼
ArcPy worker — persistent session on ArcGIS Pro's own Python
        ▼
ArcGIS Pro  (all licensed tools & extensions)
```

### The mental model (read this first)

**There is no chat window inside ArcGIS Pro, and you never "open" ARCclaude.** The relationship is flipped:

1. **You talk to your AI app** (Claude Desktop, Claude Code, Cursor, …) in plain English: *"Create a shapefile of the 5 largest lakes in Ontario with name and area fields."*
2. **The AI drives ArcGIS Pro's engine** through ARCclaude, in the background — Pro doesn't even need to be running.
3. **You open the results in Pro** like any other data: Map → Add Data → your new shapefile/geodatabase is just *there*, fields and all.

Pro can be open at the same time; just avoid pointing both Pro and the AI at the same geodatabase simultaneously (file locks). An in-Pro chat panel is on the [roadmap](docs/ROADMAP.md) (Phase 3).

Two design decisions make this robust:

1. **Esri's Python environment is never modified.** The worker script uses only the standard library + arcpy, so nothing is ever installed into `arcgispro-py3`. No env cloning, no admin rights, upgrade-safe.
2. **The arcpy session is persistent.** The slow arcpy import (~20–60 s license checkout) is paid once; after that every call is fast, and variables persist across calls like a REPL — the AI can build up state over a long workflow.

## Requirements

- Windows with **ArcGIS Pro 3.x** installed and licensed
- [`uv`](https://docs.astral.sh/uv/) (installs its own Python — you don't need one)

## Install (everyone) — one command, then just talk to Claude

You do **not** need this repo, git, or any coding. Paste one line into PowerShell:

```powershell
irm https://raw.githubusercontent.com/thaparSAAB14/ARCclaude/main/install.ps1 | iex
```

It checks ArcGIS Pro, installs what's needed, and **auto-connects ARCclaude to
Claude Desktop and Claude Code**. Then open **Claude Desktop** (or Claude Code)
and just talk: *"make a shapefile of the 3 biggest parks near me."* That's the
whole product — Claude is the interface; ARCclaude works invisibly underneath.
Re-running the same line updates you to the latest version.

> Note: Claude must run **on the same PC** as ArcGIS Pro (Claude Desktop or
> Claude Code). The claude.ai website in a browser cannot reach software on
> your machine — a hosted/remote mode is on the roadmap.

### Manual install (nerds)

```powershell
git clone https://github.com/thaparSAAB14/ARCclaude.git
cd ARCclaude
uv sync
```

New to this? The **[complete setup guide](docs/SETUP.md)** walks through everything from a blank machine, including client configs and troubleshooting.

### Claude Code

The repo ships a project-scoped `.mcp.json`, so opening this folder in Claude Code just works. To register it globally instead:

```powershell
claude mcp add arcclaude --scope user -- uv --directory C:\path\to\arcclaude run arcclaude
```

### Claude Desktop

Add to `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "arcclaude": {
      "command": "uv",
      "args": ["--directory", "C:\\path\\to\\arcclaude", "run", "arcclaude"]
    }
  }
}
```

Any other MCP-capable client (Cursor, Windsurf, open-source agents, GPT/Gemini via MCP adapters) configures the same way: `uv --directory <repo> run arcclaude` over stdio.

## Tools

| Tool | What it does |
|---|---|
| `arcpy_execute` | Run any Python/ArcPy code in the persistent session (REPL semantics) |
| `pro_live_execute` | **Cowork mode**: run code inside the user's OPEN ArcGIS Pro app — live map changes, `CURRENT` project |
| `search_gp_tools` | Search all ~1800 geoprocessing tools, incl. extension toolboxes |
| `describe_gp_tool` | Syntax + full documentation for any GP tool |
| `run_gp_tool` | Execute a GP tool by name with parameters; returns outputs + messages |
| `create_features` | **Make vector data from GeoJSON** — shapefiles or geodatabase feature classes, fields auto-created, geometry type inferred |
| `export_features` | Read any vector dataset back as GeoJSON (SQL `where` filter, row limit) |
| `describe_data` | Dataset profile: type, CRS, extent, fields, row count |
| `list_workspace` | Inventory a geodatabase or folder |
| `inspect_project` | Maps, layers, sources, layouts of an `.aprx` |
| `session_status` | License level, workspace, live session variables |
| `restart_session` | Kill and restart the ArcPy session (clears state, releases locks) |

Because discovery is dynamic (`arcpy.ListTools`), newly installed extensions and custom toolboxes are exposed automatically — no code changes needed.

## No Claude subscription? The nerd door (terminal chat)

ARCclaude also ships a standalone agentic CLI (bring your own API key — Anthropic,
OpenAI, Gemini-compat, Groq, or a free local model via Ollama):

```powershell
uv run arcclaude login    # one-time: pick provider, paste key
uv run arcclaude chat     # Codex-style AI GIS terminal
```

Works in any Windows terminal, including ArcGIS Pro's own *Python Command Prompt*.

## Cowork mode — live changes in the OPEN ArcGIS Pro

An open project is locked to outside processes, so ARCclaude ships a Live Link:
run `uv run arcclaude live`, paste the printed one-liner into Pro's **Python
window** (View ribbon → Python), and the AI can now drive the session you're
looking at — add layers to the current map, restyle, zoom, save — via the
`pro_live_execute` tool.

Cowork rules (experimental feature): while active, Pro's Python window is
**busy** — don't type more commands into it, and don't close Pro to end it.
Stop from any terminal with `uv run arcclaude live stop`; it also auto-exits
after 10 minutes with no commands. See [PRODUCT.md](docs/PRODUCT.md) for the
architecture — the Phase-3 add-in replaces this with proper in-app threading.

## Security model

`arcpy_execute` runs **arbitrary Python code on your machine with your permissions**. That is the point — it's what makes the copilot universal — but understand it:

- Run it only with MCP clients that show you tool calls and let you approve them (Claude Code and Claude Desktop both do).
- The worker inherits your ArcGIS license and file access; it can edit and delete data you can.
- Never expose the server over a network transport without adding authentication.

## Configuration

| Environment variable | Purpose | Default |
|---|---|---|
| `ARCCLAUDE_ARCGIS_PYTHON` | Explicit path to `arcgispro-py3\python.exe` | auto-discover (registry → known paths) |
| `ARCCLAUDE_STARTUP_TIMEOUT` | Seconds to wait for arcpy import | `180` |
| `ARCCLAUDE_REQUEST_TIMEOUT` | Default per-request timeout (seconds) | `300` |

## Project documents

- [Setup guide](docs/SETUP.md) — complete walkthrough: install, client configs, troubleshooting
- [Security & privacy](SECURITY.md) — data flow, offline mode, network surface (read this, IT folks)
- [Comparison](docs/COMPARISON.md) — vs. Esri's Pro Assistant, community MCP servers, and Kue
- [Vision](docs/VISION.md) — the full scope this project is building toward
- [Architecture](docs/ARCHITECTURE.md) — design decisions and worker protocol
- [Roadmap](docs/ROADMAP.md) — phased plan from this MVP to the full vision
- [Contributing](CONTRIBUTING.md)

## Status

**Alpha (v0.5.0).** The core execution engine works end-to-end. The surface area of the vision — Pro SDK add-in for live session control, ArcGIS Online/Enterprise, open-data connectors — is roadmap. Issues and PRs welcome.

## License

[Apache-2.0](LICENSE). ArcGIS, ArcPy and ArcGIS Pro are trademarks of Esri. This is an independent community project, not affiliated with or endorsed by Esri.
