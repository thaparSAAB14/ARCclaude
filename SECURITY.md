# Security & Data Privacy

This page answers the questions IT and security teams ask about ARCclaude.

## Data flow — what leaves the machine

| Data | Where it goes |
|---|---|
| Your prompts and the AI's tool-call *summaries/results* | To the AI provider you configured (Anthropic, OpenAI, etc.) |
| Your datasets (geodatabases, shapefiles, rasters, projects) | **Nowhere.** All geoprocessing runs locally in ArcGIS Pro's Python. Data content only leaves if a tool result explicitly includes it (e.g. you ask to export features as GeoJSON) |
| Telemetry / analytics | **None.** ARCclaude phones home to nothing |

**Fully-offline mode:** configure a local model (Ollama / LM Studio) via
`arcclaude login` and *nothing* leaves the machine — the only option in this
category with a zero-egress deployment.

## Execution model

- `arcpy_execute` / `pro_live_execute` run arbitrary Python with the user's
  permissions **by design** — that's what makes the copilot universal.
- Use clients that display tool calls and require human approval (Claude
  Desktop and Claude Code both do). The App and CLI show every tool
  invocation as it happens.
- There is no sandboxing beyond the user's own OS account. Do not run
  ARCclaude under an account with access you wouldn't give a Python script.
- Audit logging of executed code is on the roadmap.

## Network surface

- The MCP server is **stdio only** — no listening ports.
- The App binds to **127.0.0.1** only; it is never reachable from the network.
- The Live Link is a **local file queue** under `%USERPROFILE%\.arcclaude\live`
  (same-user filesystem permissions); no sockets, no remote access.
- Outbound connections: only to the AI provider endpoint you configure
  (none, for local models).

## Credentials

- API keys are stored in `%USERPROFILE%\.arcclaude\config.json`
  (owner-restricted where the filesystem supports it) or supplied via
  environment variables (`ANTHROPIC_API_KEY` / `OPENAI_API_KEY`).
- Keys are sent only to the corresponding provider endpoint, never logged.

## Licensing

- ARCclaude automates ArcGIS Pro through **arcpy**, Esri's official scripting
  API — the same mechanism as any organizational Python script. It checks out
  the same license the user is already entitled to, and never modifies
  Esri's installed environment.
- ARCclaude itself is Apache-2.0 open source and fully auditable.

## Reporting a vulnerability

Open a GitHub issue marked `security`, or email the maintainer. Please do not
post exploit details publicly before a fix is available.
