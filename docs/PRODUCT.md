# ARCclaude Product Architecture — the four pillars

One engine, four ways in. Every pillar reuses the same core (discovery → bridge →
persistent ArcPy worker), so capabilities land everywhere at once.

```
                        ┌────────────────────────────────────┐
                        │        ARCclaude Core Engine       │
                        │  bridge + persistent ArcPy worker  │
                        └──┬────────┬───────────┬────────┬───┘
   ┌───────────┐   ┌───────┴──┐  ┌──┴───────┐  ┌┴───────────────┐
   │ 1. MCP    │   │ 2. Chat  │  │ 3. Live  │  │ 4. Pro Add-in  │
   │  server   │   │   CLI    │  │   Link   │  │  (dock pane)   │
   │  (DONE)   │   │  (v0.3)  │  │  (v0.3)  │  │  (Phase 3)     │
   └───────────┘   └──────────┘  └──────────┘  └────────────────┘
    Claude Code,    any terminal,  drives the     chat UI inside
    Claude Desktop, incl. Pro's    OPEN Pro       ArcGIS Pro
    Cursor, agents  Python Cmd     session live   itself
```

## Pillar 1 — MCP server ✅ (v0.1–0.2, shipped)

For people who already have an AI client (Claude Desktop/Code, Cursor…).
Model-agnostic, uses the client's own AI subscription. 11 tools today.

## Pillar 2 — Claude IS the interface (v0.5 repositioning)

Main users never see ARCclaude. They run the one-line installer, which wires
the MCP server into **Claude Desktop and Claude Code** — then they just talk
to Claude. No custom UI to learn, no key management (their Claude subscription
covers it), no repo. The custom browser App shipped in v0.4 was **removed in
v0.5** by design (archived on the `legacy-app` branch): maintaining a parallel
chat UI added surface without adding capability Claude doesn't already have.

Constraint worth stating: Claude must run on the same PC as ArcGIS Pro —
claude.ai in a web browser cannot reach local software. A hosted/remote MCP
mode is a roadmap item.

### `arcclaude chat`: the terminal flavor (v0.3, kept for nerds)

A Codex-CLI-style agentic REPL — no Claude Desktop/Code required:

```
C:\> arcclaude chat
ARCclaude » make a shapefile of the 5 biggest parks in Burnaby
  ⚙ arcpy_execute … done
  ✓ parks.shp created (5 features)
```

- **Login:** `arcclaude login` — pick a provider and paste an API key:
  - **Anthropic API** (Claude models)
  - **Any OpenAI-compatible endpoint** — OpenAI, Google Gemini
    (compat endpoint), Groq, or **local models via Ollama/LM Studio** (free,
    fully offline)
- Runs in **any** Windows terminal, including the *Python Command Prompt*
  that ships with ArcGIS Pro.
- Same tool surface as the MCP server, plus Live Link tools.

**Honest note on auth:** a claude.ai *subscription* login (OAuth) is not
available to third-party apps — subscription users get ARCclaude through
Claude Desktop/Code via Pillar 1. The CLI uses pay-as-you-go API keys or
free local models.

## Pillar 3 — Live Link: cowork inside the OPEN Pro session (v0.3)

The CAD-copilot experience, today, without waiting for the add-in.

**Problem:** an open `.aprx` is locked — external processes can't save it,
and can't touch the running app.

**Solution:** a one-line listener you paste into Pro's Python window:

```python
exec(open(r"C:\...\ARCclaude\src\arcclaude\worker\live_listener.py").read()); arcclaude_live()
```

Pro's own Python then polls a command queue (`~/.arcclaude/live/`). The AI
drops code into the queue; **Pro executes it inside the live session** —
`arcpy.mp.ArcGISProject("CURRENT")`, add layers to the open map, change
symbology, zoom, select, save — and you watch it happen. Exposed to every
AI surface as the `pro_live_execute` tool.

## Pillar 4 — ArcGIS Pro add-in (Phase 3, next milestone)

A .NET (ArcGIS Pro SDK) add-in with a dockable chat pane — the polished
"built-in cowork" UI. It will host the same agent loop and speak to the same
core. Requires Visual Studio + Pro SDK templates; scoped as its own build.
Live Link (Pillar 3) is the functional bridge until this ships — and the
add-in will reuse its command-queue protocol.

## Cross-cutting goals

| Goal | Approach |
|---|---|
| **Speed** | Worker stays warm (~8 s reconnect, then instant); `memory/` workspaces for intermediates; `parallelProcessingFactor` env; GP tools over row-by-row Python |
| **Complex research, high accuracy** | Open-data connectors (STAC/OSM/CKAN); numpy/scipy/PIL vision workflows (all ship inside Esri's Python — no installs); every result verified with real geoprocessing checks |
| **Georeferencing < 3 min** | Package the proven GeoMap workflow as a `georeference_map` tool: rasterize → detect printed UTM/graticule grid with computer vision → robust affine fit (achieved 3.4 m/2.5 m RMS) → warp. GDAL (ships with Pro) as fallback for GCP text files. Target v0.4 |
| **Live file changes** | Live Link edits the CURRENT project; for closed files the worker edits directly; Pro auto-redraws layers whose underlying data changed |
```
