"""Convert an ARCclaude project manifest into a QGIS project (.qgz).

The worker's `extract_qgis_manifest` op distills an .aprx through Esri's own
CIM into neutral JSON (layers, sources, CRS, renderers, colors). This module
turns that manifest into QGIS's open XML project format — no QGIS install
needed to write it, and no reverse engineering of Esri's binary formats:
we read the Esri side through arcpy's front door.

Fidelity notes (v1): simple / unique-value / class-break renderers with flat
colors, stroke widths and marker sizes; layer visibility, order, definition
queries and CRS. Basemap/web layers are skipped with a note (add an XYZ
basemap in QGIS). Layouts are not converted yet.
"""

from __future__ import annotations

import re
import uuid
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

PT_TO_MM = 0.352778  # ArcGIS symbol sizes are points; QGIS defaults to mm

GEOMETRY_MAP = {
    "point": ("Point", "marker"),
    "multipoint": ("Point", "marker"),
    "polyline": ("Line", "line"),
    "polygon": ("Polygon", "fill"),
}

FALLBACK = {"fill": [141, 90, 153, 255], "stroke": [35, 35, 35, 255],
            "stroke_width": 0.7, "size": 6.0}


def _rgba_str(rgba) -> str:
    r, g, b, a = (list(rgba) + [255, 255, 255, 255])[:4]
    return f"{int(r)},{int(g)},{int(b)},{int(a)}"


def _opt(name: str, value) -> str:
    return f'<Option name={quoteattr(name)} type="QString" value={quoteattr(str(value))}/>'


def _symbol_xml(kind: str, spec: dict, name: str) -> str:
    """One <symbol> element. kind: marker|line|fill."""
    spec = spec or {}
    fill = spec.get("fill") or FALLBACK["fill"]
    stroke = spec.get("stroke") or FALLBACK["stroke"]
    width_mm = round((spec.get("stroke_width") or FALLBACK["stroke_width"]) * PT_TO_MM, 3)
    size_mm = round((spec.get("size") or FALLBACK["size"]) * PT_TO_MM, 3)

    if kind == "line":
        opts = [_opt("line_color", _rgba_str(stroke)),
                _opt("line_style", "solid"),
                _opt("line_width", width_mm),
                _opt("line_width_unit", "MM"),
                _opt("capstyle", "round"), _opt("joinstyle", "round")]
        layer = f'<layer class="SimpleLine" enabled="1" locked="0" pass="0"><Option type="Map">{"".join(opts)}</Option></layer>'
    elif kind == "marker":
        opts = [_opt("name", "circle"),
                _opt("color", _rgba_str(fill)),
                _opt("outline_color", _rgba_str(stroke)),
                _opt("outline_style", "solid"),
                _opt("outline_width", round(width_mm * 0.5, 3)),
                _opt("size", size_mm), _opt("size_unit", "MM")]
        layer = f'<layer class="SimpleMarker" enabled="1" locked="0" pass="0"><Option type="Map">{"".join(opts)}</Option></layer>'
    else:  # fill
        opts = [_opt("color", _rgba_str(fill)),
                _opt("style", "solid"),
                _opt("outline_color", _rgba_str(stroke)),
                _opt("outline_style", "solid"),
                _opt("outline_width", width_mm),
                _opt("outline_width_unit", "MM")]
        layer = f'<layer class="SimpleFill" enabled="1" locked="0" pass="0"><Option type="Map">{"".join(opts)}</Option></layer>'

    return (f'<symbol type="{kind}" name={quoteattr(name)} alpha="1" '
            f'clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">{layer}</symbol>')


def _renderer_xml(renderer: dict | None, kind: str) -> str:
    """<renderer-v2> for a layer. kind: marker|line|fill."""
    if not renderer or renderer.get("type") in (None, "unsupported"):
        sym = _symbol_xml(kind, {}, "0")
        return f'<renderer-v2 type="singleSymbol" forceraster="0" enableorderby="0"><symbols>{sym}</symbols></renderer-v2>'

    if renderer["type"] == "single":
        sym = _symbol_xml(kind, renderer.get("symbol"), "0")
        return f'<renderer-v2 type="singleSymbol" forceraster="0" enableorderby="0"><symbols>{sym}</symbols></renderer-v2>'

    if renderer["type"] == "categorized":
        attr = (renderer.get("fields") or [""])[0]
        cats, syms = [], []
        for i, cl in enumerate(renderer.get("classes") or []):
            values = cl.get("values") or [[]]
            value = str(values[0][0]) if values and values[0] else ""
            label = cl.get("label") or value
            render = "true" if cl.get("visible", True) else "false"
            cats.append(f'<category render="{render}" symbol="{i}" type="string" '
                        f'value={quoteattr(value)} label={quoteattr(label)} uuid="{i}"/>')
            syms.append(_symbol_xml(kind, cl.get("symbol"), str(i)))
        if renderer.get("default"):
            cats.append(f'<category render="true" symbol="default" type="string" value="" label="(other)" uuid="d"/>')
            syms.append(_symbol_xml(kind, renderer["default"], "default"))
        return (f'<renderer-v2 type="categorizedSymbol" attr={quoteattr(attr)} '
                f'forceraster="0" enableorderby="0">'
                f'<categories>{"".join(cats)}</categories>'
                f'<symbols>{"".join(syms)}</symbols></renderer-v2>')

    if renderer["type"] == "graduated":
        attr = renderer.get("field") or ""
        lower = renderer.get("minimum", 0)
        ranges, syms = [], []
        for i, br in enumerate(renderer.get("breaks") or []):
            upper = br.get("upper", 0)
            label = br.get("label") or f"{lower} - {upper}"
            ranges.append(f'<range render="true" symbol="{i}" lower={quoteattr(str(lower))} '
                          f'upper={quoteattr(str(upper))} label={quoteattr(label)} uuid="{i}"/>')
            syms.append(_symbol_xml(kind, br.get("symbol"), str(i)))
            lower = upper
        return (f'<renderer-v2 type="graduatedSymbol" attr={quoteattr(attr)} '
                f'graduatedMethod="GraduatedColor" forceraster="0" enableorderby="0">'
                f'<ranges>{"".join(ranges)}</ranges>'
                f'<symbols>{"".join(syms)}</symbols></renderer-v2>')

    sym = _symbol_xml(kind, {}, "0")
    return f'<renderer-v2 type="singleSymbol" forceraster="0" enableorderby="0"><symbols>{sym}</symbols></renderer-v2>'


def _ogr_source(source: str) -> str:
    """ArcGIS dataSource path -> OGR datasource string."""
    low = source.lower()
    if ".gdb\\" in low or ".gdb/" in low:
        idx = low.rindex(".gdb") + 4
        gdb, layer = source[:idx], source[idx + 1:]
        if layer:
            return f"{gdb}|layername={layer}"
        return gdb
    return source


def _crs_xml(authid: str | None) -> str:
    if not authid:
        return "<srs><spatialrefsys></spatialrefsys></srs>"
    srid = authid.split(":")[-1]
    return (f"<srs><spatialrefsys><authid>{escape(authid)}</authid>"
            f"<srid>{escape(srid)}</srid></spatialrefsys></srs>")


def build_qgs(manifest: dict, map_name: str | None = None) -> tuple[str, dict]:
    """Build the .qgs project XML for one map of the manifest."""
    maps = manifest.get("maps") or []
    if not maps:
        raise ValueError("The project contains no maps to convert.")
    if map_name:
        matches = [m for m in maps if m["name"] == map_name]
        if not matches:
            raise ValueError(f"Map '{map_name}' not found; available: "
                             + ", ".join(m["name"] for m in maps))
        the_map = matches[0]
    else:
        the_map = maps[0]

    tree_nodes, maplayers, order_ids = [], [], []
    stats = {"vector": 0, "raster": 0, "categories": 0,
             "skipped": list(the_map.get("skipped") or [])}

    for lyr in the_map.get("layers") or []:
        lid = ("l" + uuid.uuid4().hex)[:24]
        name = lyr.get("name") or lid
        checked = "Qt::Checked" if lyr.get("visible", True) else "Qt::Unchecked"

        if lyr.get("kind") == "raster":
            source = lyr.get("source") or ""
            maplayers.append(
                f'<maplayer type="raster" autoRefreshEnabled="0">'
                f"<id>{lid}</id><datasource>{escape(source)}</datasource>"
                f"<layername>{escape(name)}</layername>"
                f'{_crs_xml(lyr.get("crs"))}'
                f'<provider>gdal</provider>'
                f"</maplayer>")
            stats["raster"] += 1
        else:
            geometry, sym_kind = GEOMETRY_MAP.get(
                (lyr.get("geometry") or "polyline").lower(), ("Line", "line"))
            source = _ogr_source(lyr.get("source") or "")
            renderer = lyr.get("renderer")
            if renderer and renderer.get("type") == "categorized":
                stats["categories"] += len(renderer.get("classes") or [])
            subset = lyr.get("definition_query")
            subset_xml = f"<subsetstring>{escape(subset)}</subsetstring>" if subset else ""
            maplayers.append(
                f'<maplayer type="vector" geometry="{geometry}" autoRefreshEnabled="0" '
                f'simplifyDrawingHints="1" simplifyLocal="1" readOnly="0">'
                f"<id>{lid}</id><datasource>{escape(source)}</datasource>"
                f"<layername>{escape(name)}</layername>"
                f'{_crs_xml(lyr.get("crs"))}'
                f'<provider encoding="UTF-8">ogr</provider>'
                f"{subset_xml}"
                f'{_renderer_xml(renderer, sym_kind)}'
                f'<blendMode>0</blendMode><featureBlendMode>0</featureBlendMode>'
                f"</maplayer>")
            stats["vector"] += 1

        tree_nodes.append(f'<layer-tree-layer id="{lid}" name={quoteattr(name)} '
                          f'checked="{checked}" expanded="1" '
                          f'providerKey="" source=""/>')
        order_ids.append(f'<item>{lid}</item>')

    project_name = Path(manifest.get("project", "project")).stem
    xml = (
        '<!DOCTYPE qgis PUBLIC \'http://mrcc.com/qgis.dtd\' \'SYSTEM\'>\n'
        f'<qgis version="3.40.0" projectname={quoteattr(project_name)} saveUser="arcclaude" saveUserFull="ARCclaude QGIS export">'
        f'<homePath path=""/>'
        f'<title>{escape(the_map.get("name") or project_name)}</title>'
        f'<projectCrs>{_crs_xml(the_map.get("crs")).replace("<srs>", "").replace("</srs>", "")}</projectCrs>'
        f'<layer-tree-group>{"".join(tree_nodes)}<custom-order enabled="0">{"".join(order_ids)}</custom-order></layer-tree-group>'
        f'<projectlayers>{"".join(maplayers)}</projectlayers>'
        f'<layerorder>{"".join(f"<layer id={quoteattr(i[6:-7])}/>" for i in order_ids)}</layerorder>'
        f'<properties><Gui><CanvasColorRedPart type="int">255</CanvasColorRedPart>'
        f'<CanvasColorGreenPart type="int">255</CanvasColorGreenPart>'
        f'<CanvasColorBluePart type="int">255</CanvasColorBluePart></Gui></properties>'
        '</qgis>'
    )
    return xml, stats


def heal_gdb_rasters(manifest: dict, output_path: str, request) -> list[str]:
    """Self-healing pass: QGIS/GDAL cannot read rasters stored inside a file
    geodatabase, so export each one to a GeoTIFF sidecar via the worker and
    repoint the layer. `request(op, **fields) -> dict` is a worker call.
    Returns plain-language notes describing every fix."""
    fixes: list[str] = []
    out = Path(output_path)
    data_dir = out.parent / (out.stem + "_data")
    for m in manifest.get("maps") or []:
        kept = []
        for lyr in m.get("layers") or []:
            src = (lyr.get("source") or "")
            is_gdb = ".gdb\\" in src.lower() or ".gdb/" in src.lower()
            if lyr.get("kind") == "raster" and is_gdb:
                safe = re.sub(r"\W+", "_", lyr.get("name") or "raster").strip("_")
                tif = data_dir / f"{safe}.tif"
                r = request("copy_raster_tif", source=src, out=str(tif))
                if r.get("ok"):
                    lyr["source"] = str(tif)
                    fixes.append(
                        f"{lyr['name']}: QGIS can't read rasters stored inside a "
                        f"file geodatabase, so a GeoTIFF copy was saved to "
                        f"{data_dir.name}\\{tif.name} and the QGIS layer points there.")
                    kept.append(lyr)
                else:
                    m.setdefault("skipped", []).append({
                        "name": lyr.get("name"),
                        "reason": "GDB raster; GeoTIFF export failed: "
                                  + str(r.get("error", "unknown"))[:200]})
            else:
                kept.append(lyr)
        m["layers"] = kept
    return fixes


def write_qgz(manifest: dict, output_path: str, map_name: str | None = None) -> dict:
    """Write a .qgz (zipped QGIS project). Returns a summary dict."""
    out = Path(output_path)
    if out.suffix.lower() not in (".qgz", ".qgs"):
        out = out.with_suffix(".qgz")
    xml, stats = build_qgs(manifest, map_name)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix.lower() == ".qgs":
        out.write_text(xml, encoding="utf-8")
    else:
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(out.stem + ".qgs", xml)
    return {"qgis_project": str(out), "vector_layers": stats["vector"],
            "raster_layers": stats["raster"],
            "symbology_categories": stats["categories"],
            "skipped_layers": stats["skipped"]}
