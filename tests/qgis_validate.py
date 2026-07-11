"""Headless PyQGIS validator — run under QGIS's own Python:

    "C:\\Program Files\\QGIS 3.x\\bin\\python-qgis.bat" tests/qgis_validate.py out.qgz

Prints one machine-readable line: QGIS_VALIDATE_JSON:{...}
"""

import json
import sys

from qgis.core import QgsApplication

app = QgsApplication([], False)
app.initQgis()

from qgis.core import QgsProject  # noqa: E402

project = QgsProject.instance()
read_ok = project.read(sys.argv[1])

layers = []
for layer in project.mapLayers().values():
    try:
        renderer_type = layer.renderer().type()
    except Exception:
        renderer_type = None
    layers.append({
        "name": layer.name(),
        "valid": bool(layer.isValid()),
        "renderer": renderer_type,
    })

print("QGIS_VALIDATE_JSON:" + json.dumps({
    "read_ok": bool(read_ok),
    "layer_count": len(layers),
    "layers": layers,
}))
app.exitQgis()
