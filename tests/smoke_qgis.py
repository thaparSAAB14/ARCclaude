"""Smoke test: .aprx -> QGIS project conversion, validated by real QGIS.

Stage 1: worker extracts the CIM manifest from a real project.
Stage 2: emitter writes the .qgz; XML checked structurally.
Stage 3 (if QGIS is installed): headless PyQGIS opens the .qgz and reports
         layer validity + renderer types.

Run:  uv run python tests/smoke_qgis.py
"""

import glob
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.dom import minidom

from arcclaude.bridge import ArcPyBridge
from arcclaude.qgis_export import heal_gdb_rasters, write_qgz

APRX = r"C:\Users\ps103\OneDrive\Documents\ArcGIS\Projects\MyProject1\MyProject1_ARCclaude.aprx"

PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  PASS  {name}")
    else:
        FAIL += 1; print(f"  FAIL  {name}  {str(detail)[:300]}")


def find_qgis_python() -> str | None:
    hits = sorted(glob.glob(r"C:\Program Files\QGIS*\bin\python-qgis*.bat"))
    return hits[-1] if hits else None


def main() -> int:
    if not Path(APRX).exists():
        print(f"SKIP: test project missing ({APRX})")
        return 0

    print("== stage 1: extract manifest from real .aprx ==")
    out = Path(tempfile.mkdtemp(prefix="arcclaude_qgis_")) / "converted.qgz"
    bridge = ArcPyBridge()
    bridge.start()
    try:
        r = bridge.request("extract_qgis_manifest", path=APRX, timeout=300)
        check("manifest extracted", r.get("ok") is True, str(r)[:300])
        manifest = r.get("manifest") or {}
        maps = manifest.get("maps") or []
        check("has at least one map", len(maps) >= 1)
        the_map = maps[0] if maps else {"layers": [], "skipped": []}
        vectors = [l for l in the_map.get("layers", []) if l.get("kind") == "vector"]
        gdb_rasters = [l for l in the_map.get("layers", [])
                       if l.get("kind") == "raster" and ".gdb" in (l.get("source") or "").lower()]
        check("multiple vector layers found", len(vectors) >= 3, f"got {len(vectors)}")
        check("basemaps were skipped with notes", len(the_map.get("skipped", [])) >= 1)

        categorized = [l for l in vectors
                       if (l.get("renderer") or {}).get("type") == "categorized"]
        check("categorized symbology extracted from CIM", len(categorized) >= 1,
              str([(l['name'], (l.get('renderer') or {}).get('type')) for l in vectors])[:300])
        if categorized:
            classes = categorized[0]["renderer"].get("classes") or []
            check("categories carry values + colors",
                  classes and classes[0].get("values") and bool(
                      (classes[0].get("symbol") or {}).get("stroke")
                      or (classes[0].get("symbol") or {}).get("fill")),
                  str(classes[:1])[:250])

        print("== stage 1.5: self-heal GDB rasters to GeoTIFF ==")
        def _req(op, **fields):
            return bridge.request(op, timeout=300, **fields)
        fixes = heal_gdb_rasters(manifest, str(out), _req)
        if gdb_rasters:
            check("GDB rasters auto-exported to GeoTIFF",
                  len(fixes) == len(gdb_rasters), f"{len(fixes)} fixes: {fixes}")
        else:
            print("  SKIP: project has no GDB rasters to heal")
    finally:
        bridge.stop()

    print("== stage 2: emit .qgz and inspect XML ==")
    summary = write_qgz(manifest, str(out))
    check("qgz written", out.exists(), str(summary))
    check("summary counts vectors", summary["vector_layers"] == len(vectors), str(summary))

    with zipfile.ZipFile(out) as zf:
        qgs_name = [n for n in zf.namelist() if n.endswith(".qgs")][0]
        xml_text = zf.read(qgs_name).decode("utf-8")
    doc = minidom.parseString(xml_text)
    maplayers = doc.getElementsByTagName("maplayer")
    check("XML parses; maplayer count matches",
          len(maplayers) == len(the_map.get("layers", [])),
          f"xml {len(maplayers)} vs manifest {len(the_map.get('layers', []))}")
    cat_renderers = [el for el in doc.getElementsByTagName("renderer-v2")
                     if el.getAttribute("type") == "categorizedSymbol"]
    check("categorized renderer present in XML", len(cat_renderers) >= 1)

    print("== stage 3: real QGIS opens the project ==")
    qgis_py = find_qgis_python()
    if not qgis_py:
        print("  SKIP: QGIS not installed on this machine")
    else:
        validator = str(Path(__file__).parent / "qgis_validate.py")
        proc = subprocess.run([qgis_py, validator, str(out)],
                              capture_output=True, text=True, timeout=300)
        line = next((ln for ln in proc.stdout.splitlines()
                     if ln.startswith("QGIS_VALIDATE_JSON:")), None)
        check("validator produced a report", line is not None,
              (proc.stdout + proc.stderr)[-400:])
        if line:
            report = json.loads(line.split(":", 1)[1])
            check("QGIS read the project", report.get("read_ok") is True, str(report)[:300])
            check("QGIS sees every layer",
                  report.get("layer_count") == len(the_map.get("layers", [])),
                  str(report)[:400])
            invalid = [l for l in report.get("layers", []) if not l["valid"]]
            check("all layers valid (data sources resolve)", not invalid, str(invalid)[:300])
            cats = [l for l in report.get("layers", [])
                    if l.get("renderer") == "categorizedSymbol"]
            check("categorized symbology survived into QGIS", len(cats) >= 1,
                  str(report.get("layers"))[:400])

    print(f"\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
