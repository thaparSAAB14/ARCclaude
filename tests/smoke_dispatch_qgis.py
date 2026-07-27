"""Smoke test: server-derived tool dispatch + the QGIS algorithm runner.

Neither path needs ArcGIS Pro, so this is the one suite that can run anywhere
QGIS is installed.  Run:  uv run python tests/smoke_dispatch_qgis.py
"""

import json
import sys
import tempfile
from pathlib import Path

from arcclaude.agent import dispatch, tool_defs

PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {str(detail)[:300]}")


def main() -> int:
    print("== tool table comes from the MCP server ==")
    defs = tool_defs()
    names = {n for n, _d, _s in defs}
    check("every tool has name/description/schema",
          all(n and d and isinstance(s, dict) for n, d, s in defs), str(defs[:1])[:200])
    check("qgis_run is exposed", "qgis_run" in names, sorted(names))
    check("no tool lost in the collapse", len(defs) >= 14, f"{len(defs)} tools")

    print("== dispatch reaches a tool and returns text ==")
    out = dispatch("qgis_run", {})           # no algorithm -> list them
    check("qgis_run lists algorithms", "3d:tessellate" in out, out[:300])

    print("== dispatch survives a bad call instead of raising ==")
    out = dispatch("does_not_exist", {})
    check("unknown tool returns an error string", "error" in out.lower(), out[:200])

    print("== QGIS actually processes data (no ArcGIS involved) ==")
    tmp = Path(tempfile.mkdtemp(prefix="arcclaude_qgis_run_"))
    src = tmp / "pt.geojson"
    src.write_text(json.dumps({
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {"n": 1},
                      "geometry": {"type": "Point", "coordinates": [0, 0]}}],
    }), encoding="utf-8")
    out_shp = tmp / "buffered.gpkg"
    out = dispatch("qgis_run", {
        "algorithm": "native:buffer",
        "params": {"INPUT": str(src), "DISTANCE": 1, "OUTPUT": str(out_shp)},
    })
    check("buffer algorithm ran", out_shp.exists(), out[-400:])

    print("== QGIS project emitter, from a synthetic manifest ==")
    # No ArcGIS and no .aprx: the emitter is pure, so feed it the manifest the
    # worker would have produced and check the XML QGIS actually receives.
    from arcclaude.qgis_export import write_qgz
    manifest = {"project": "synthetic.aprx", "maps": [{
        "name": "Map", "crs": "EPSG:26917", "skipped": [],
        "layers": [{
            "name": "roads", "kind": "vector", "visible": True,
            "geometry": "Polyline", "crs": "EPSG:26917",
            "source": str(src), "definition_query": None,
            "renderer": {"type": "categorized", "fields": ["kind"], "classes": [
                {"values": [["paved"]], "label": "Paved", "visible": True,
                 "symbol": {"stroke": [255, 0, 0, 255], "stroke_width": 2.0}},
                {"values": [["gravel"]], "label": "Gravel", "visible": True,
                 "symbol": {"stroke": [0, 0, 255, 255], "stroke_width": 1.0}},
            ], "default": None},
        }],
    }]}
    qgz = tmp / "synthetic.qgz"
    summary = write_qgz(manifest, str(qgz))
    check("emitter writes a .qgz", qgz.exists() and summary["vector_layers"] == 1,
          str(summary))
    import zipfile
    with zipfile.ZipFile(qgz) as zf:
        xml = zf.read(next(n for n in zf.namelist() if n.endswith(".qgs"))).decode()
    check("categories and colours land in the XML",
          'type="categorizedSymbol"' in xml and "255,0,0,255" in xml
          and 'value="gravel"' in xml, xml[:300])
    check("project CRS carried through", "EPSG:26917" in xml)

    print(f"\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
