"""Locate the ArcGIS Pro Python environment (arcgispro-py3) on this machine."""

from __future__ import annotations

import os
from pathlib import Path

ENV_OVERRIDE = "ARCCLAUDE_ARCGIS_PYTHON"

_KNOWN_PATHS = [
    r"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe",
    os.path.expandvars(
        r"%LOCALAPPDATA%\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe"
    ),
]


def _from_registry() -> str | None:
    """Read the Pro install dir from the registry (HKLM, then HKCU)."""
    try:
        import winreg
    except ImportError:  # non-Windows: nothing to find
        return None
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(hive, r"SOFTWARE\ESRI\ArcGISPro") as key:
                install_dir, _ = winreg.QueryValueEx(key, "InstallDir")
            candidate = (
                Path(install_dir) / "bin" / "Python" / "envs" / "arcgispro-py3" / "python.exe"
            )
            if candidate.is_file():
                return str(candidate)
        except OSError:
            continue
    return None


def find_arcgis_python() -> str:
    """Return the path to arcgispro-py3's python.exe.

    Resolution order: ARCCLAUDE_ARCGIS_PYTHON env var -> registry -> known paths.
    Raises FileNotFoundError with guidance if nothing is found.
    """
    override = os.environ.get(ENV_OVERRIDE)
    if override:
        if Path(override).is_file():
            return override
        raise FileNotFoundError(
            f"{ENV_OVERRIDE} is set to {override!r} but that file does not exist."
        )

    found = _from_registry()
    if found:
        return found

    for candidate in _KNOWN_PATHS:
        if Path(candidate).is_file():
            return candidate

    raise FileNotFoundError(
        "Could not locate ArcGIS Pro's Python (arcgispro-py3). Is ArcGIS Pro "
        f"installed? You can point ARCclaude at it explicitly by setting the "
        f"{ENV_OVERRIDE} environment variable to the full path of python.exe."
    )
