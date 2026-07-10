# Packages the compiled add-in into an .esriAddinX (zip, OPC layout) without
# Visual Studio. Run after: dotnet build -c Release
param([string]$Configuration = "Release")

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$proj = Join-Path $root "ARCclaude.Addin"
$bin = Join-Path $proj "bin\$Configuration"
$dll = Join-Path $bin "ARCclaude.Addin.dll"
if (-not (Test-Path $dll)) { throw "Build first: dotnet build -c $Configuration ($dll missing)" }

$stage = Join-Path $env:TEMP ("arcclaude_addin_" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path "$stage\Install\Runner" -Force | Out-Null

Copy-Item (Join-Path $proj "Config.daml") $stage
Copy-Item $dll "$stage\Install"
Copy-Item (Join-Path $proj "Runner\arcclaude_runner.pyt") "$stage\Install\Runner"

$contentTypes = @'
<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="daml" ContentType="text/xml" />
  <Default Extension="dll" ContentType="application/octet-stream" />
  <Default Extension="pyt" ContentType="text/plain" />
  <Default Extension="xml" ContentType="text/xml" />
</Types>
'@
[System.IO.File]::WriteAllText((Join-Path $stage "[Content_Types].xml"), $contentTypes)

$out = Join-Path $bin "ARCclaude.Addin.esriAddinX"
if (Test-Path $out) { Remove-Item $out -Force }
$zip = "$out.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path "$stage\*" -DestinationPath $zip
Move-Item $zip $out
Remove-Item $stage -Recurse -Force

Write-Host "Packaged: $out"
Write-Host "Install: double-click the file (Esri Add-In installer), then restart ArcGIS Pro."
