@echo off
title ARCclaude Setup
rem Double-click installer for ARCclaude - runs the PowerShell installer
rem with a policy bypass limited to this one process.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*

echo.
pause
