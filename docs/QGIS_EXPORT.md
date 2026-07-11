# ArcGIS Pro → QGIS project conversion

One tool call converts a whole `.aprx` into a QGIS project:

> *"Convert my project to QGIS"* → `export_to_qgis(aprx_path, output.qgz)`

The `.qgz` opens directly in QGIS 3.x with the same layers, order, visibility,
definition queries, CRS, and symbology. Data stays where it is — QGIS reads
your shapefiles and file-geodatabase feature classes in place via OGR.

## Why this can be free

Traditional migration tools must reverse-engineer Esri's proprietary binary
formats — years of specialist work, usually sold commercially. ARCclaude
sidesteps that entirely: since ArcGIS Pro is installed anyway, we read the
project through **Esri's own front door**
(arcpy + the CIM, Esri's full-fidelity object model) and write **QGIS's open
XML format**. No binary spelunking, nothing to license.

```
.aprx ──arcpy/CIM──► neutral JSON manifest ──emitter──► .qgs XML ──zip──► .qgz
        (worker,      layers, sources, CRS,   (pure stdlib,
       stdlib-only)   renderers, colors...     no QGIS needed)
```

## What converts today (v1)

| | |
|---|---|
| Layers & order | ✅ vector (shapefile, GDB feature class) + raster, visibility, tree order |
| CRS | ✅ per-layer and per-map (EPSG authids) |
| Symbology | ✅ single, unique-value → categorized, class-breaks → graduated; colors (RGB/HSV/CMYK/gray), stroke widths, marker sizes (points → mm) |
| Definition queries | ✅ become QGIS subset strings |
| **GDB rasters** | 🩹 **self-healed**: QGIS/GDAL cannot read rasters inside a file geodatabase, so each one is automatically exported to a GeoTIFF sidecar folder and the QGIS layer repointed — the fix is reported in `auto_fixes` |
| Basemaps / web layers | ⚠️ skipped with a note (add an XYZ basemap in QGIS — e.g. OpenStreetMap) |
| Layouts, labels, complex symbols | ❌ not yet (roadmap) |

## Verified how

`tests/smoke_qgis.py` converts a real multi-layer project and then — when QGIS
is installed — launches **headless PyQGIS** (`python-qgis.bat`) to open the
result and assert every layer is valid and the categorized symbology survived.
Not "the XML looks right": QGIS itself signs off.
