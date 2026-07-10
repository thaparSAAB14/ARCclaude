# ARCclaude ArcGIS Pro Add-in (Pillar 4, v1 scaffold)

A native WPF dockpane that hosts the **Live Link** inside ArcGIS Pro — no more
pasting a listener into the Python window. Toggle "Cowork mode" in the pane and
every ARCclaude client (Claude via the MCP `pro_live_execute` tool, the chat
CLI) can drive the open session. Design rationale: [docs/ADDIN_DESIGN.md](../docs/ADDIN_DESIGN.md).

## Build (no Visual Studio needed)

Requires the .NET 10 SDK and ArcGIS Pro 3.7+ on the machine (Pro 3.7's SDK
package targets net10.0-windows):

```powershell
cd addin\ARCclaude.Addin
dotnet build -c Release
```

The Esri NuGet package (`Esri.ArcGISPro.Extensions30`) supplies both the API
references and the packaging targets; a successful build produces
`bin\Release\ARCclaude.Addin.esriAddinX`.

## Install

Double-click the `.esriAddinX` file (Esri's add-in installer opens), then start
ArcGIS Pro → **Add-In tab → ARCclaude** → toggle **Cowork mode**.

## Status

Compile-ready scaffold. Not yet exercised inside a live Pro session — treat as
beta until the first in-app run is logged. Known v1 trade-off: live commands
run in fresh scopes (no variable persistence between calls); the headless
`arcpy_execute` session persists as always.
