# ARCclaude one-shot installer for Windows.
#
# Run it any of three ways:
#   1. Double-click install.cmd (next to this file)
#   2. From a cloned/unzipped repo:  powershell -ExecutionPolicy Bypass -File install.ps1
#   3. Straight from the internet (installs to %LOCALAPPDATA%\ARCclaude):
#      irm https://raw.githubusercontent.com/thaparSAAB14/ARCclaude/main/install.ps1 | iex
#
# Compatible with Windows PowerShell 5.1 (the Windows default) and PowerShell 7.

param(
    [string]$InstallDir = "$env:LOCALAPPDATA\ARCclaude",
    [switch]$NoClientConfig,   # skip Claude Code / Claude Desktop registration
    [switch]$RunTests          # run the full geoprocessing smoke test at the end (~1 min)
)

$ErrorActionPreference = 'Stop'
# TLS 1.2 for older Windows PowerShell downloads
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor 3072

$RepoZip = 'https://github.com/thaparSAAB14/ARCclaude/archive/refs/heads/main.zip'

function Write-Step([int]$n, [string]$msg) { Write-Host "`n[$n/6] $msg" -ForegroundColor Cyan }
function Write-Ok([string]$msg)   { Write-Host "      OK  $msg" -ForegroundColor Green }
function Write-Info([string]$msg) { Write-Host "      $msg" -ForegroundColor Gray }
function Fail([string]$msg) {
    Write-Host "`n  SETUP FAILED: $msg" -ForegroundColor Red
    exit 1
}

# Run a native tool via cmd.exe with stderr merged there, so PowerShell's
# error stream never wraps progress messages into fake errors (a Windows
# PowerShell 5.1 pitfall). Returns exit code + combined output.
function Invoke-Tool([string[]]$ArgList) {
    $quoted = foreach ($a in $ArgList) {
        if ($a -match '[\s"]') { '"' + ($a -replace '"', '\"') + '"' } else { $a }
    }
    $line = $quoted -join ' '
    $out = cmd /c "$line 2>&1"
    New-Object PSObject -Property @{
        ExitCode = $LASTEXITCODE
        Output   = (($out | ForEach-Object { "$_" }) -join "`n")
    }
}

Write-Host ''
Write-Host '  =============================================' -ForegroundColor DarkCyan
Write-Host '   ARCclaude Setup' -ForegroundColor White
Write-Host '   AI copilot for ArcGIS Pro (MCP server)' -ForegroundColor Gray
Write-Host '  =============================================' -ForegroundColor DarkCyan

# ---------------------------------------------------------------- 1. ArcGIS Pro
Write-Step 1 'Checking for ArcGIS Pro...'

function Find-ArcGISPython {
    foreach ($hive in 'HKLM:', 'HKCU:') {
        try {
            $key = Get-ItemProperty "$hive\SOFTWARE\ESRI\ArcGISPro" -ErrorAction Stop
            $candidate = Join-Path $key.InstallDir 'bin\Python\envs\arcgispro-py3\python.exe'
            if (Test-Path $candidate) { return $candidate }
        } catch { }
    }
    $known = @(
        'C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe',
        "$env:LOCALAPPDATA\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe"
    )
    foreach ($p in $known) { if (Test-Path $p) { return $p } }
    if ($env:ARCCLAUDE_ARCGIS_PYTHON -and (Test-Path $env:ARCCLAUDE_ARCGIS_PYTHON)) {
        return $env:ARCCLAUDE_ARCGIS_PYTHON
    }
    return $null
}

$arcPython = Find-ArcGISPython
if (-not $arcPython) {
    Fail ('ArcGIS Pro was not found. Install and license ArcGIS Pro 3.x first, ' +
          'or set ARCCLAUDE_ARCGIS_PYTHON to the full path of arcgispro-py3\python.exe.')
}
Write-Ok "ArcGIS Pro Python found: $arcPython"

# ---------------------------------------------------------------- 2. uv
Write-Step 2 'Checking for uv (Python runtime manager)...'

if (Get-Command uv -ErrorAction SilentlyContinue) {
    $uvVer = (Invoke-Tool @('uv', '--version')).Output
    Write-Ok "uv already installed ($uvVer)"
} else {
    Write-Info 'uv not found - installing from astral.sh (official installer)...'
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression | Out-Null
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Fail 'uv installation did not complete. Install manually: https://docs.astral.sh/uv/'
    }
    $uvVer = (Invoke-Tool @('uv', '--version')).Output
    Write-Ok "uv installed ($uvVer)"
}
$uvExe = (Get-Command uv).Source

# ---------------------------------------------------------------- 3. Get ARCclaude
Write-Step 3 'Getting ARCclaude...'

$localMode = $false
if ($PSScriptRoot) {
    $pj = Join-Path $PSScriptRoot 'pyproject.toml'
    if ((Test-Path $pj) -and ((Get-Content $pj -Raw) -match 'name = "arcclaude"')) {
        $localMode = $true
        $InstallDir = $PSScriptRoot
    }
}

if ($localMode) {
    Write-Ok "Using this local copy: $InstallDir"
} else {
    Write-Info "Downloading latest ARCclaude to $InstallDir ..."
    $tmp = Join-Path $env:TEMP ('arcclaude-setup-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $tmp -Force | Out-Null
    try {
        Invoke-WebRequest $RepoZip -OutFile "$tmp\arcclaude.zip" -UseBasicParsing
        Expand-Archive "$tmp\arcclaude.zip" -DestinationPath $tmp
        $src = Get-ChildItem $tmp -Directory | Where-Object { $_.Name -like 'ARCclaude-*' } | Select-Object -First 1
        if (-not $src) { Fail 'Downloaded archive had an unexpected layout.' }
        if (Test-Path $InstallDir) {
            Write-Info 'Existing installation found - replacing it (your data is not touched).'
            Remove-Item $InstallDir -Recurse -Force
        }
        Move-Item $src.FullName $InstallDir
    } finally {
        if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue }
    }
    Write-Ok "Downloaded to $InstallDir"
}

# ---------------------------------------------------------------- 4. Dependencies
Write-Step 4 'Installing dependencies (isolated - Esri''s Python is never touched)...'

# A running ARCclaude server (Claude Desktop/Code keeps it alive and even
# respawns it) locks files in .venv and would make the update fail. Stop the
# whole chain by command line, and retry the sync — like any installer that
# says "setup detected the application is running".
function Stop-ARCclaudeProcesses([string]$dir) {
    $targets = 'uv.exe', 'python.exe', 'pythonw.exe', 'arcclaude.exe'
    $procs = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $targets -contains $_.Name -and $_.CommandLine -and $_.CommandLine -like "*$dir*"
    })
    foreach ($p in $procs) {
        try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop } catch { }
    }
    return $procs.Count
}

Push-Location $InstallDir
try {
    $synced = $false
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        $killed = Stop-ARCclaudeProcesses $InstallDir
        if ($killed -gt 0) {
            Write-Info "Stopped $killed running ARCclaude process(es) to allow the update."
            Start-Sleep -Seconds 2
        }
        $r = Invoke-Tool @($uvExe, 'sync')
        if ($r.ExitCode -eq 0) { $synced = $true; break }
        if ($attempt -lt 3) { Write-Info "Environment was locked by a client - retrying ($attempt/3)..." }
    }
    if (-not $synced) {
        Write-Host $r.Output
        Fail ('uv sync failed - details above. If a Claude Desktop/Code session is ' +
              'using ARCclaude, close it and run setup again.')
    }
    Write-Ok 'Python environment ready'

    # ------------------------------------------------------------ 5. Verify
    Write-Step 5 'Verifying installation...'
    $r = Invoke-Tool @($uvExe, 'run', 'python', '-c',
        'from arcclaude.discovery import find_arcgis_python; print(find_arcgis_python())')
    if ($r.ExitCode -ne 0) {
        Write-Host $r.Output
        Fail 'Verification failed: the server cannot locate ArcGIS Pro.'
    }
    Write-Ok ('Server starts and discovers ArcGIS Pro: ' + $r.Output.Trim())

    if ($RunTests) {
        Write-Info 'Running full geoprocessing smoke test (about 1 minute)...'
        $r = Invoke-Tool @($uvExe, 'run', 'python', 'tests\smoke_bridge.py')
        Write-Host $r.Output
        if ($r.ExitCode -ne 0) { Fail 'Smoke test failed - see output above.' }
        Write-Ok 'Smoke test passed: real geoprocessing works'
    }
} finally {
    Pop-Location
}

# ---------------------------------------------------------------- 6. AI clients
Write-Step 6 'Configuring AI clients...'

$configured = @()

if ($NoClientConfig) {
    Write-Info 'Skipped (-NoClientConfig).'
} else {
    # ---- Claude Code (global registration)
    $claudeCmd = Get-Command claude -ErrorAction SilentlyContinue
    if ($claudeCmd) {
        Invoke-Tool @($claudeCmd.Source, 'mcp', 'remove', 'arcclaude', '--scope', 'user') | Out-Null
        $r = Invoke-Tool @($claudeCmd.Source, 'mcp', 'add', 'arcclaude', '--scope', 'user', '--',
                           $uvExe, '--directory', $InstallDir, 'run', 'arcclaude')
        if ($r.ExitCode -eq 0) {
            $configured += 'Claude Code (all projects)'
            Write-Ok 'Claude Code: registered globally'
        } else {
            Write-Info 'Claude Code: registration failed - add manually (see docs/SETUP.md).'
        }
    } else {
        Write-Info 'Claude Code CLI not found - skipped.'
    }

    # ---- Claude Desktop (config file merge)
    $desktopDir = Join-Path $env:APPDATA 'Claude'
    if (Test-Path $desktopDir) {
        $configPath = Join-Path $desktopDir 'claude_desktop_config.json'
        if (Test-Path $configPath) {
            Copy-Item $configPath "$configPath.bak" -Force
            $config = Get-Content $configPath -Raw | ConvertFrom-Json
            if ($null -eq $config) { $config = New-Object PSObject }
        } else {
            $config = New-Object PSObject
        }
        if (-not ($config.PSObject.Properties.Name -contains 'mcpServers')) {
            $config | Add-Member -NotePropertyName 'mcpServers' -NotePropertyValue (New-Object PSObject)
        }
        $server = New-Object PSObject -Property @{
            command = 'uv'
            args    = @('--directory', $InstallDir, 'run', 'arcclaude')
        }
        if ($config.mcpServers.PSObject.Properties.Name -contains 'arcclaude') {
            $config.mcpServers.arcclaude = $server
        } else {
            $config.mcpServers | Add-Member -NotePropertyName 'arcclaude' -NotePropertyValue $server
        }
        $json = $config | ConvertTo-Json -Depth 10
        [System.IO.File]::WriteAllText($configPath, $json)  # UTF-8, no BOM
        $configured += 'Claude Desktop'
        Write-Ok "Claude Desktop: configured ($configPath)"
        Write-Info 'Restart Claude Desktop to load the server.'
    } else {
        Write-Info 'Claude Desktop not found - skipped.'
    }

    if ($configured.Count -eq 0) {
        Write-Info 'No supported clients auto-configured. Manual snippets: docs/SETUP.md section 4.'
    }
}

# ---------------------------------------------------------------- done
Write-Host ''
Write-Host '  =============================================' -ForegroundColor DarkGreen
Write-Host '   ARCclaude is installed!' -ForegroundColor Green
Write-Host '  =============================================' -ForegroundColor DarkGreen
Write-Host ''
Write-Host "   Location:   $InstallDir"
if ($configured.Count -gt 0) {
    Write-Host ('   Configured: ' + ($configured -join ', '))
}
Write-Host ''
Write-Host '   Try it - ask your AI:' -ForegroundColor White
Write-Host '     "Check the ArcGIS session status"' -ForegroundColor Yellow
Write-Host '   (first call takes 20-60s while arcpy checks out your license)' -ForegroundColor Gray
Write-Host ''
