<!-- Thanks for contributing. Keep this short; delete what does not apply. -->

## What this changes

<!-- One or two sentences. Link the issue if there is one: Fixes #123 -->

## Why

<!-- The problem being solved, not a restatement of the diff. -->

## How it was verified

<!-- ARCclaude touches a licensed desktop app, so "it compiles" is not enough.
     Say what you actually ran and what you saw. -->

- [ ] `uv run python tests/smoke_bridge.py` (needs ArcGIS Pro)
- [ ] `uv run python tests/smoke_mcp.py` (needs ArcGIS Pro)
- [ ] `uv run python tests/smoke_live.py`
- [ ] Exercised by hand in ArcGIS Pro / an MCP client — describe what you saw:

## Checklist

- [ ] Worker code (`src/arcclaude/worker/`, add-in `Runner/`) still imports only
      the standard library and `arcpy` (`python scripts/check_worker_invariant.py`)
- [ ] No new required dependency in Esri's Python environment
- [ ] Docs updated if behaviour or setup changed
- [ ] `CHANGELOG.md` updated under "Unreleased" for user-visible changes
