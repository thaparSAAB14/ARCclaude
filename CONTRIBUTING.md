# Contributing to ARCclaude

Thanks for helping build the open-source AI copilot for ArcGIS Pro! By taking
part you agree to uphold our [Code of Conduct](CODE_OF_CONDUCT.md).

## Ground rules

- **The worker stays stdlib-only.** `src/arcclaude/worker/` and the add-in's
  `Runner/` must import nothing beyond the Python standard library and
  `arcpy`. This is the invariant that keeps ARCclaude installable without
  touching Esri's environment. CI enforces it — run it yourself with
  `python scripts/check_worker_invariant.py`.
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

ARCclaude drives a licensed desktop application, so the suites that matter
most cannot run on a hosted CI runner — run them locally before opening a PR:

```powershell
uv run python tests/smoke_bridge.py   # bridge + worker, real geoprocessing
uv run python tests/smoke_mcp.py      # full MCP client end-to-end
uv run python tests/smoke_live.py     # Live Link queue (no ArcGIS needed)
```

Only `smoke_live.py` runs without ArcGIS Pro. Pure-logic changes (discovery,
protocol, converters) should come with tests that don't require arcpy.

### What CI checks

Every push and pull request runs lint (`ruff`), byte-compilation, the
stdlib-only worker invariant, a clean import of every module, and a check that
the MCP tool surface has not shrunk. Reproduce it locally with:

```powershell
uvx ruff check src tests scripts
uv run python scripts/check_worker_invariant.py
```

## Pull requests

1. One focused change per PR.
2. Update `docs/ROADMAP.md` if you complete or add a roadmap item.
3. Add an entry under "Unreleased" in `CHANGELOG.md` for user-visible changes.
4. Describe the manual test you ran (tool call transcript welcome).

## Working with an AI assistant

Much of ARCclaude is built with AI pair-programming. `rules.md` holds the
working rules an assistant should follow in this repo — stay inside the
current project, show changes immediately, use plain language, repair
predictable environment mismatches instead of failing. Point your assistant at
it before it starts.

## Reporting issues

Include: ArcGIS Pro version, license level, `session_status` output, and the
full JSON error from the failing tool call.
