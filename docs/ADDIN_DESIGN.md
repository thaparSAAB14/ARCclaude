# ArcGIS Pro Add-in — Design (Pillar 4)

Based on an external architectural review (Gemini/Antigravity, 2026-07-09),
**vetted and adapted** to ARCclaude's existing architecture. The review's core
ideas are sound; where it proposed new infrastructure that duplicates what
ARCclaude already ships, we reuse ours instead.

## Adopt / Adapt / Defer

| Recommendation | Verdict | Why |
|---|---|---|
| WPF **Dockpane** UI via ArcGIS Pro SDK for .NET | ✅ **Adopt** | The correct (only) native path |
| All state changes on the **MCT via `QueuedTask.Run()`** | ✅ **Adopt** | Fixes the root cause of the v0.3 Python-window freeze |
| **CIM-level edits** for live map changes | ✅ Adopt (incremental) | CIM = Pro's native model; start where it's needed |
| **`OperationManager` undo** (Ctrl+Z for AI changes) | ✅ Adopt (v2) | The right safety net; scoped after the host works |
| gRPC / Named Pipes **IPC to a new Python process** | 🔄 **Adapt** | We already have a proven IPC: the **Live Link file queue** (`~/.arcclaude/live`). The add-in becomes its *native host* — every existing client (MCP `pro_live_execute`, chat CLI) works unchanged, zero new protocol |
| **AvalonEdit 'Codex' terminal** embedded in the pane | 🔄 Adapt (v2) | v1 pane = status + activity log; a full editor is polish, not plumbing |
| **Roslyn dynamic C# execution** | ⏸️ **Defer** | Big security surface, marginal benefit while Python covers arcpy fully |
| CIM **JSON diff tab** + **Swipe visual diff** | ⏸️ Defer (v2/v3) | Excellent ideas; need the host + undo first |
| Industry risk list (privacy, spatial hallucination, API drift, corruption) | ✅ Already covered | SECURITY.md (privacy/offline mode), verified-results habit, `overwriteOutput` + explicit save policy; undo lands in v2 |

## v1 architecture: the add-in is a better Live Link host

```
MCP server / chat CLI  ──►  ~/.arcclaude/live/cmd_*.json   (unchanged protocol)
                                      │
                       ┌──────────────▼──────────────┐
                       │  ARCclaude Add-in (C#/WPF)  │
                       │  FileSystemWatcher + queue  │
                       │  heartbeat every 2 s        │
                       └──────────────┬──────────────┘
                                      │ per command
                       Geoprocessing.ExecuteToolAsync(
                           arcclaude_runner.pyt \ RunCode)
                                      │
                       Pro's in-process Python: exec(code),
                       CURRENT project live, writes result_*.json
```

Why this beats the v0.3 pasted listener:
- **No blocked Python window, no freeze risk** — file watching happens in .NET;
  execution rides Pro's own geoprocessing queue (designed for long work).
- **No paste-line ritual** — install the add-in once; the pane has an on/off toggle.
- **Protocol-compatible** — `pro_live_execute` and `arcclaude live stop` work as-is.
- **The runner stays stdlib+arcpy only** (worker invariant holds inside the .pyt).

Known v1 trade-off: each command executes in a fresh script-tool scope, so
*variables do not persist between live commands* (the headless `arcpy_execute`
session still persists as always). Documented in the tool description; a
persistent in-Pro namespace returns with the v2 CIM/undo work.

## Component map (`addin/ARCclaude.Addin/`)

| File | Role |
|---|---|
| `ARCclaude.Addin.csproj` | net8.0-windows, `Esri.ArcGISPro.Extensions30` NuGet — builds with `dotnet build`, no Visual Studio required |
| `Config.daml` | Add-in manifest: module, ribbon button, dockpane |
| `Module1.cs` | Module lifecycle; stops the service on unload |
| `LiveLinkService.cs` | Watcher, sequential dispatch, heartbeat, stale-queue purge |
| `ARCclaudePaneViewModel.cs` / `ARCclaudePaneView.xaml(.cs)` | Dockpane: toggle + live activity log |
| `ShowPaneButton.cs` | Ribbon button (Add-In tab) |
| `Runner/arcclaude_runner.pyt` | Python toolbox: executes one command file against CURRENT, writes the result JSON (stdlib+arcpy only) |

## Roadmap within the pillar

- **v1 (this scaffold):** native Live Link host + status pane
- **v2:** OperationManager undo units, CIM JSON diff view, persistent namespace,
  AvalonEdit console
- **v3:** Swipe-tool visual diff, embedded chat (agent core via local HTTP to the
  Python side), Roslyn *if* a concrete need appears
