# Changelog

All notable changes to ARCclaude are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
While the version is below 1.0.0, minor bumps may include breaking changes.

## [Unreleased]

### Added
- **`export_to_qgis`** — convert an ArcGIS Pro project to a QGIS project
  (`.qgz`), carrying over layers, order, visibility, definition queries, CRS
  and symbology (single, categorized and graduated renderers). The project is
  read through arcpy and the CIM, so no proprietary format is reverse
  engineered. Rasters stored inside a file geodatabase — which QGIS cannot
  read — are exported to GeoTIFF sidecars automatically and reported.
  See [docs/QGIS_EXPORT.md](docs/QGIS_EXPORT.md).
- Continuous integration: lint, byte-compile, import and MCP tool-surface
  checks on every push and pull request.
- `scripts/check_worker_invariant.py` — machine-enforces the rule that worker
  code imports only the standard library and `arcpy`, so Esri's Python
  environment is never a dependency target.
- Issue forms, pull-request template and Dependabot configuration.
- `CHANGELOG.md`, `CODE_OF_CONDUCT.md`, and a `docs/` index.

### Changed
- `.gitattributes` normalises line endings (LF in the repository, CRLF for
  Windows scripts), ending the checkout warnings on every commit.
- Ruff configuration added; the codebase is lint-clean.

### Fixed
- `bridge.py` now chains the underlying timeout exception (`raise ... from`)
  so worker stalls keep their original traceback.
- `tests/smoke_bridge.py` is hermetic and repeatable. It previously borrowed
  `arcpy.env.scratchGDB`, which an interrupted session can leave as a plain
  folder; geoprocessing then wrote shapefiles there, cleanup missed them by
  name, and every later run failed with a misleading "output already exists".
  The suite now owns a dedicated file geodatabase and asserts its own cleanup.

## [0.5.0] — 2026-07-09

### Changed
- **Claude is the interface.** ARCclaude is now purely the bridge: the
  one-line installer wires the MCP server into Claude Desktop and Claude Code,
  and users simply talk to Claude. Documentation restructured around this.

### Removed
- The bundled browser App (v0.4.0). It duplicated capability Claude already
  provides; the code is preserved on the `legacy-app` branch.

### Added
- ArcGIS Pro add-in scaffold (`addin/`): a WPF dock pane that hosts Live Link
  natively — no listener to paste into the Python window, and no freeze risk,
  because file watching happens in .NET and execution rides the geoprocessing
  queue. Builds with `dotnet build` plus `addin/package.ps1`; no Visual Studio
  required.
- House rules applied at the core (see `rules.md`): work inside the current
  project, open views after edits so changes are visible immediately, pass
  human-readable action labels, and explain automatic fixes in plain language.
- Plain-language translations for the most common ArcPy failures, attached to
  every error as `friendly_hint`; shapefile field-name truncation is now
  reported rather than silently applied.

## [0.4.0] — 2026-07-06

### Added
- A local browser App (`arcclaude app`) with status indicators and one-time
  key setup, plus a desktop launcher. *(Removed again in 0.5.0.)*
- Shared agent core (`agent.py`) behind every front end.

## [0.3.0] — 2026-07-05

### Added
- **Live Link cowork mode**: `pro_live_execute` drives the ArcGIS Pro session
  the user is looking at — the current project, live map changes.
- `arcclaude chat` and `arcclaude login`: a standalone agent in the terminal
  for people without a Claude subscription (Anthropic, any OpenAI-compatible
  endpoint, or a local model via Ollama).

## [0.2.0] — 2026-07-05

### Added
- `create_features`: GeoJSON to shapefile or geodatabase feature class, with
  fields created automatically and geometry type inferred.
- `export_features`: read any vector dataset back as GeoJSON, with optional
  SQL filtering.

### Fixed
- `JSONToFeatures` silently produced an empty dataset when the geometry type
  was omitted for GeoJSON input; the type is now inferred from the data.
- `FeaturesToJSON` renames its output file; the worker now reads the path the
  tool reports rather than the one requested.

## [0.1.0] — 2026-07-04

### Added
- Initial release: MCP server exposing ArcGIS Pro to AI assistants over stdio.
- Persistent ArcPy worker on Esri's own Python — the slow licence checkout is
  paid once, then variables persist across calls like a REPL.
- Dynamic discovery of all ~1,800 geoprocessing tools, including extensions.
- One-command Windows installer that configures Claude Desktop and Claude Code.

[Unreleased]: https://github.com/thaparSAAB14/ARCclaude/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/thaparSAAB14/ARCclaude/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/thaparSAAB14/ARCclaude/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/thaparSAAB14/ARCclaude/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/thaparSAAB14/ARCclaude/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/thaparSAAB14/ARCclaude/releases/tag/v0.1.0
