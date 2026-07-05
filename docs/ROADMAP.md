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

- [ ] Structured parameter schemas from `arcpy.GetParameterInfo()`
- [ ] Map & layout automation helpers (arcpy.mp): symbology, layouts, export to PDF/PNG
- [ ] Progress streaming for long geoprocessing jobs (MCP progress notifications)
- [ ] Attachment/resource support: return exported maps and charts as MCP resources
- [ ] Cursor-based data reading with pagination (arcpy.da → JSON)
- [ ] SD/geodatabase schema reporting; broken-source detection and repair
- [x] Windows installer: `install.cmd` / `install.ps1` one-liner with client auto-config
- [ ] Signed MSI release artifact (needs code-signing certificate + release pipeline)

## Phase 3 — Live application control (v0.4–0.5)

- [ ] ArcGIS Pro SDK (.NET) add-in hosting a local bridge
- [ ] Drive the open Pro session: active map, views, selections, bookmarks, editing
- [ ] Bidirectional context: AI sees what the user sees (current extent, selected features)
- [ ] CIM-level symbology and layout manipulation

## Phase 4 — Enterprise & web GIS (v0.6–0.7)

- [ ] `arcgis` Python API worker: ArcGIS Online / Enterprise portals
- [ ] Content management: publish, share, clone items
- [ ] Hosted service administration; user/group/role management
- [ ] Web maps, dashboards, StoryMaps automation

## Phase 5 — Open geospatial ecosystem (v0.8+)

- [ ] Open-data connectors: STAC, OpenStreetMap, CKAN, Earthdata, Copernicus
- [ ] GDAL/OGR, GeoPandas, WhiteboxTools, PDAL bridges (server-env workers)
- [ ] PostGIS integration
- [ ] Cross-engine workflows: e.g. Sentinel scene via STAC → arcpy classification → web map

## Cross-cutting

- [ ] CI (lint + unit tests that mock the worker; GP tests need a licensed runner)
- [ ] Contributor docs, issue templates, discussions
- [ ] Security hardening: allowlist mode, read-only mode, audit log of executed code
- [ ] Docs site with cookbook of real workflows
