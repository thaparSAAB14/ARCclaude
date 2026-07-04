"""Smoke test: drive the bridge + worker directly with real geoprocessing.

Run:  uv run python tests/smoke_bridge.py
Requires a licensed ArcGIS Pro install. Takes ~60s (arcpy cold start).
"""

import sys
import time

from arcclaude.bridge import ArcPyBridge

PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {detail}")


def main() -> int:
    bridge = ArcPyBridge()

    print("== startup ==")
    t0 = time.time()
    info = bridge.start()
    print(f"  ready in {time.time() - t0:.1f}s: {info.get('product')} "
          f"{info.get('version')} license={info.get('license')}")
    check("worker ready", info.get("event") == "ready")

    print("== ping ==")
    r = bridge.request("ping")
    check("ping ok", r.get("ok") is True, str(r))

    print("== exec: persistent state ==")
    r1 = bridge.request("exec", code="x = 21")
    r2 = bridge.request("exec", code="x * 2")
    check("state persists across calls", r2.get("result") == "42", str(r2))

    print("== exec: stdout capture ==")
    r = bridge.request("exec", code="print('hello from arcpy session')")
    check("stdout captured", "hello from arcpy session" in r.get("stdout", ""), str(r))

    print("== exec: error handling ==")
    r = bridge.request("exec", code="1 / 0")
    check("error surfaced, worker survives",
          r.get("ok") is False and "ZeroDivisionError" in r.get("error", ""), str(r))
    r = bridge.request("ping")
    check("worker alive after error", r.get("ok") is True)

    print("== search_tools ==")
    r = bridge.request("search_tools", query="buffer")
    check("finds Buffer_analysis",
          any("Buffer_analysis" in t for t in r.get("tools", [])), str(r)[:300])

    print("== describe_tool ==")
    r = bridge.request("describe_tool", tool="Buffer_analysis")
    check("has usage", bool(r.get("usage")), str(r)[:200])

    print("== real geoprocessing: create + buffer ==")
    setup = """
import arcpy, os
gdb = arcpy.env.scratchGDB
fc = os.path.join(gdb, 'arcclaude_smoke_pts')
if arcpy.Exists(fc):
    arcpy.management.Delete(fc)
sr = arcpy.SpatialReference(3857)
arcpy.management.CreateFeatureclass(gdb, 'arcclaude_smoke_pts', 'POINT', spatial_reference=sr)
with arcpy.da.InsertCursor(fc, ['SHAPE@XY']) as cur:
    cur.insertRow([(0.0, 0.0)])
    cur.insertRow([(1000.0, 1000.0)])
fc
"""
    r = bridge.request("exec", code=setup, timeout=120)
    check("feature class created", r.get("ok") is True, str(r)[:400])

    r = bridge.request(
        "run_tool", tool="analysis.Buffer",
        args=[], timeout=120,
        kwargs={
            "in_features": r.get("result", "").strip("'"),
            "out_feature_class": "memory/smoke_buf",
            "buffer_distance_or_field": "500 Meters",
        },
    )
    check("buffer ran", r.get("ok") is True, str(r)[:400])

    print("== describe_data on buffer output ==")
    r = bridge.request("describe_data", path="memory/smoke_buf")
    d = r.get("description", {})
    check("describes polygons, 2 rows",
          d.get("shapeType") == "Polygon" and d.get("rowCount") == 2, str(d)[:400])

    print("== cleanup + shutdown ==")
    bridge.request("exec", code=(
        "import arcpy, os\n"
        "arcpy.management.Delete(os.path.join(arcpy.env.scratchGDB, 'arcclaude_smoke_pts'))\n"
        "arcpy.management.Delete('memory/smoke_buf')"
    ), timeout=120)
    bridge.stop()
    check("worker stopped", not bridge.alive)

    print(f"\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
