# ARCclaude — Pitch Kit

One page for decision-makers, a rehearsal script for the demo, and
copy-paste posts for community distribution.

---

## The one-pager

**Problem.** GIS analysts spend a large share of their week on mechanical
work: georeferencing scans, converting formats, fetching open data, batch
geoprocessing, repairing projects. Skilled judgment time is scarce; clicking
time is not.

**Solution.** ARCclaude connects AI assistants to our existing ArcGIS Pro
licenses. Analysts type plain English — *"pull the city's bikeway open data,
clip to our district, put it on the map"* — and the work happens in Pro,
with every action shown and human-approved. It runs as a beginner-friendly
app, a terminal, or inside Claude Desktop, and can *cowork* live in an open
Pro session.

**Why it's safe.** Datasets never leave our machines — only prompts go to
the AI provider, and a fully-offline local-model mode exists for sensitive
work. Open source (Apache-2.0), auditable, no telemetry, no listening ports.
Details: `SECURITY.md`.

**Why now.** Esri is shipping its own Pro Assistant (beta) and 30+
governments already pay per-seat for the QGIS equivalent (Kue). This
category is validated; ARCclaude gives us the open, no-per-seat-fee, any-
model version today. Details: `docs/COMPARISON.md`.

**The ask.** A 3-week pilot: one team, non-sensitive data, three workflows
(georeferencing backlog, open-data integration, batch geoprocessing).
Success metric: hours saved per workflow vs. current practice.

**Cost.** Software: $0. AI usage: cents per task (or $0 with local models).
Uses ArcGIS licenses we already own.

---

## Demo script (10 minutes, rehearse twice)

> Setup beforehand: ArcGIS Pro open with a simple project; ARCclaude App
> running; Live Link listener pasted and green; API key working. Record a
> backup video of each demo in case the network misbehaves.

**Demo 1 — Sentence to map (3 min).**
Prompt: `Download Vancouver's bikeways open data, save it as a shapefile in
my project, and add it to my open map colored by bikeway type.`
Expect: tool chips for download/convert/live-add; layers appear in the open
Pro session. Talking point: "no code, no portal hunting, license-safe."

**Demo 2 — The georeferencing party trick (4 min).**
Show a scanned geology PDF (GSC Open File 3511). Prompt: `Georeference this
scanned map PDF into my project.` Talking point: "manual georeferencing is
30–60 minutes of clicking control points; this ran in ~3 minutes at 3-metre
accuracy — we verified it against live city data."
(Backup: show the before/after overlay screenshot.)

**Demo 3 — Ask your data questions (2 min).**
Prompt: `How many bikeway segments are protected lanes, and what's their
total length in km?` Expect: a plain-English answer computed by real
geoprocessing. Talking point: "verification built in — it counts with the
same tools an analyst would."

**Close (1 min).** The pilot ask, the security one-pager, the repo URL.

---

## Copy-paste community posts (post under your own account)

**Esri Community / LinkedIn:**

> I built ARCclaude — an open-source (Apache-2.0) bridge that gives AI
> assistants full access to ArcGIS Pro via ArcPy. It's model-agnostic
> (Claude, GPT, Gemini, or fully-offline local models), exposes all ~1,800
> geoprocessing tools dynamically, keeps a persistent REPL session, and has
> a "Live Link" mode that coworks inside your open Pro session. One-line
> installer auto-connects it to Claude Desktop/Code — non-technical users
> just install and talk to Claude.
> Repo: https://github.com/thaparSAAB14/ARCclaude — feedback and PRs welcome!

**r/gis:**

> Made an open-source AI copilot for ArcGIS Pro (MCP server + standalone
> app). Type "make a shapefile of X and put it on my open map" and it
> happens — real arcpy underneath, any AI model on top (including free local
> Ollama, so nothing leaves your machine). It also georeferenced a scanned
> 1998 geology PDF to 3 m RMS in ~3 minutes using the printed UTM grid.
> Apache-2.0, Windows + ArcGIS Pro 3.x: https://github.com/thaparSAAB14/ARCclaude
