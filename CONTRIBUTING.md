# Contributing to ARCclaude

Thanks for helping build the open-source AI copilot for ArcGIS Pro!

## Ground rules

- **The worker stays stdlib-only.** `src/arcclaude/worker/` must import
  nothing beyond the Python standard library and `arcpy`. This is the
  invariant that keeps ARCclaude installable without touching Esri's
  environment. CI will reject violations.
- **Dynamic over static.** Prefer runtime discovery (`arcpy.ListTools`,
  `Describe`) over hand-maintained tool catalogs.
- **Errors are data.** Tool failures must return structured, actionable
  messages (including `arcpy.GetMessages()`) — never crash the session.

## Dev setup

```powershell
git clone https://github.com/thaparSAAB14/ARCclaude.git
cd ARCclaude
uv sync
```

Requires ArcGIS Pro 3.x licensed locally for integration tests.

## Tests

```powershell
uv run python tests/smoke_bridge.py   # bridge + worker, real geoprocessing
uv run python tests/smoke_mcp.py      # full MCP client end-to-end
```

Both suites must pass before a PR. Pure-logic changes (discovery, protocol)
should come with pytest unit tests that don't require arcpy.

## Pull requests

1. One focused change per PR.
2. Update `docs/ROADMAP.md` if you complete or add a roadmap item.
3. Describe the manual test you ran (tool call transcript welcome).

## Reporting issues

Include: ArcGIS Pro version, license level, `session_status` output, and the
full JSON error from the failing tool call.
