# ARCclaude Roadmap

## Phase 1 — Core execution engine ✅ (v0.1, shipped)

- [x] MCP stdio server, model-agnostic
- [x] Persistent ArcPy worker on Esri's Python (zero-install-footprint design)
- [x] `arcpy_execute` with REPL semantics
- [x] Dynamic GP tool discovery/search/docs/execution (incl. extensions)
- [x] Data description, workspace inventory, .aprx inspection
- [x] Session lifecycle: status, restart, timeout-kill-recover
- [x] Smoke test suites (bridge-level and MCP end-to-end)

## Phase 2 — Analyst workflows (v0.2–0.3)

- [x] Natural-language vector creation: `create_features` (GeoJSON → shapefile/GDB,
      fields auto-created, geometry type inferred) + `export_features` (read-back
      with SQL filter) — v0.2.0
- [ ] Structured parameter schemas from `arcpy.GetParameterInfo()`
- [ ] Map & layout automation helpers (arcpy.mp): symbology, layouts, export to PDF/PNG
- [ ] Progress streaming for long geoprocessing jobs (MCP progress notifications)
- [ ] Attachment/resource support: return exported maps and charts as MCP resources
- [ ] Cursor-based data reading with pagination (arcpy.da → JSON)
- [ ] SD/geodatabase schema reporting; broken-source detection and repair
- [x] Windows installer: `install.cmd` / `install.ps1` one-liner with client auto-config
- [ ] Signed MSI release artifact (needs code-signing certificate + release pipeline)

## Phase 3 — Live application control (v0.4–0.5)

- [x] **Live Link** (v0.3): file-queue listener pasted into Pro's Python window;
      `pro_live_execute` drives the OPEN session (CURRENT project, live map changes)
- [x] **Terminal app** (v0.3): `arcclaude chat` agentic CLI + `arcclaude login`
      (Anthropic / OpenAI-compatible / local Ollama keys)
- [x] ~~ARCclaude App (v0.4): local web UI~~ — **removed in v0.5** (archived on
      `legacy-app` branch): Claude Desktop/Code is the main-user interface;
      the installer wires it up automatically
- [ ] Remote/hosted MCP mode so claude.ai (web) can drive a machine running
      ArcGIS Pro (auth required; design needed)
- [x] **ArcGIS Pro add-in v1 scaffold** (`addin/`): WPF dockpane with cowork
      toggle, native Live Link host (FileSystemWatcher + GP runner .pyt with
      CURRENT access, heartbeat) — same file-queue protocol, no pasted
      listener, no freeze risk. Compiles clean against Pro 3.7 SDK via
      `dotnet build` + `package.ps1` (no Visual Studio). Design:
      [ADDIN_DESIGN.md](ADDIN_DESIGN.md). ⚠ not yet run-tested inside Pro
- [ ] Add-in v2: OperationManager undo (Ctrl+Z for AI changes), CIM JSON diff
      tab, Swipe visual diff, persistent live namespace, AvalonEdit console
- [ ] `georeference_map` tool: scanned map → CV grid detection → warp, < 3 min
      (workflow proven on GSC OF 3511: 3.4 m / 2.5 m RMS)
- [ ] Drive the open Pro session: active map, views, selections, bookmarks, editing
- [ ] Bidirectional context: AI sees what the user sees (current extent, selected features)
- [ ] CIM-level symbology and layout manipulation

## Phase 4 — Enterprise & web GIS (v0.6–0.7)

- [ ] `arcgis` Python API worker: ArcGIS Online / Enterprise portals
- [ ] Content management: publish, share, clone items
- [ ] Hosted service administration; user/group/role management
- [ ] Web maps, dashboards, StoryMaps automation

## Phase 5 — Open geospatial ecosystem (v0.8+)

- [ ] AI-assisted digitizing of scanned/raster maps (Bunting Labs-style vector
      autocomplete), building on Image Analyst deep-learning tools
- [ ] Open-data connectors: STAC, OpenStreetMap, CKAN, Earthdata, Copernicus
- [ ] GDAL/OGR, GeoPandas, WhiteboxTools, PDAL bridges (server-env workers)
- [ ] PostGIS integration
- [ ] Cross-engine workflows: e.g. Sentinel scene via STAC → arcpy classification → web map

## Cross-cutting

- [ ] CI (lint + unit tests that mock the worker; GP tests need a licensed runner)
- [ ] Contributor docs, issue templates, discussions
- [ ] Security hardening: allowlist mode, read-only mode, audit log of executed code
- [ ] Docs site with cookbook of real workflows
