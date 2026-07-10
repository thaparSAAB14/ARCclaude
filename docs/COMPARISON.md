# How ARCclaude compares (July 2026)

AI-assisted GIS is a hot, validated category — Esri is building an assistant
into ArcGIS Pro, and governments pay per-seat for the equivalent on QGIS.
ARCclaude's position: **the open, model-agnostic, full-execution option.**

## The landscape

| | Esri ArcGIS Pro Assistant (beta) | Community ArcGIS MCP servers | Kue (QGIS, Bunting Labs) | **ARCclaude** |
|---|---|---|---|---|
| Open source | ❌ | ✅ | ❌ ($19/seat/mo) | ✅ Apache-2.0 |
| Choose your AI model | ❌ Esri-hosted | mostly Claude-only | ❌ | ✅ Claude / GPT / Gemini / Groq / **local Ollama** |
| Fully offline option | ❌ | ❌ | ❌ | ✅ (local models) |
| Geoprocessing coverage | opens tools w/ preset params | ~30 curated tools | QGIS algorithms | ✅ all ~1,800 arcpy tools, discovered dynamically |
| Persistent agent session (REPL) | ❌ | varies | — | ✅ |
| Works without a paid AI client | ❌ | ❌ (needs Claude Desktop) | ✅ | ✅ terminal chat (BYO key / local model) |
| Drives the OPEN Pro session | ✅ (in-app) | rare | ✅ (in QGIS) | ✅ Live Link |
| Headless automation (Pro closed) | ❌ | ✅ | ❌ | ✅ same engine |
| Scanned-map georeferencing (CV) | ❌ | ❌ | raster tracing (different) | ✅ proven 3.4 m RMS workflow |
| Install footprint | built-in | manual setup | QGIS plugin | one-line installer, Esri env untouched |

## Detail

**Esri ArcGIS Pro Assistant** — official, in beta since Pro 3.6. Docs Q&A,
ArcPy/SQL generation, and in-app actions (styling, zoom, selection, opening
GP tools with preset parameters). Closed source, Esri-account gated, Esri's
models only. Read: the category is validated by the vendor itself; ARCclaude
differentiates on openness, model freedom, agentic end-to-end execution and
offline use.

**Community MCP servers** (SojiroPopo/arcgis-mcp, geo2004/MCP-ArcGISPro,
choraquest, nicogis, …) — same core idea, typically a curated subset of
arcpy tools, Claude Desktop required, no app/CLI surface, no live-session
story, no installer. ARCclaude ships four surfaces off one tested core.

**Kue (Bunting Labs)** and the academic **SpatialAnalysisAgent / GIS
Copilot** — strong proof of demand on QGIS (Kue: 30+ governments,
per-seat pricing). Different ecosystem; no ArcGIS Pro coverage.

## Positioning in one sentence

> Esri validated the idea and QGIS users pay monthly for it — ARCclaude is
> the free, open-source, any-model version for ArcGIS Pro, with the only
> fully-offline privacy story in the category.

## Sources

- [Esri: Pro Assistant 3.7 beta](https://www.esri.com/arcgis-blog/products/arcgis-pro/announcements/try-the-arcgis-pro-assistant-3-7-beta-and-get-more-done-in-arcgis-pro)
- [Esri: What's new in AI Assistants (June 2026)](https://www.esri.com/arcgis-blog/products/arcgis-online/geoai/whats-new-in-ai-assistants-june-2026)
- [Esri: The Next Era of AI and ArcGIS](https://www.esri.com/about/newsroom/arcnews/the-next-era-of-ai-and-arcgis)
- [Glama MCP directory: ARCclaude](https://glama.ai/mcp/servers/thaparSAAB14/ARCclaude) · [arcgis-mcp](https://glama.ai/mcp/servers/SojiroPopo/arcgis-mcp)
- [geo2004/MCP-ArcGISPro](https://github.com/geo2004/MCP-ArcGISPro)
- [Kue AI](https://buntinglabs.com/solutions/kue-ai) · [SpatialAnalysisAgent](https://plugins.qgis.org/plugins/SpatialAnalysisAgent-master/) · [GIS Copilot paper](https://www.tandfonline.com/doi/full/10.1080/17538947.2025.2497489)
