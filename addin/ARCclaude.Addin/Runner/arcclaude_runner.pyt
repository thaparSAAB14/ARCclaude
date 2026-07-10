# -*- coding: utf-8 -*-
"""ARCclaude live-command runner (Python toolbox).

Executed by the ARCclaude add-in via Geoprocessing.ExecuteToolAsync for each
queued Live Link command. Runs on ArcGIS Pro's in-process Python, so
arcpy.mp.ArcGISProject("CURRENT") refers to the open project and map changes
appear live. Stdlib + arcpy only (ARCclaude worker invariant).

Note: each run is a fresh scope — variables do NOT persist between live
commands (unlike the headless arcpy_execute session).
"""

import ast
import contextlib
import io
import json
import os
import traceback

import arcpy


class Toolbox(object):
    def __init__(self):
        self.label = "ARCclaude Runner"
        self.alias = "arcclauderunner"
        self.tools = [RunCode]


class RunCode(object):
    def __init__(self):
        self.label = "Run ARCclaude Live Command"
        self.description = "Executes one queued ARCclaude Live Link command in this Pro session."
        self.canRunInBackground = False  # must run in-process for CURRENT

    def getParameterInfo(self):
        code_file = arcpy.Parameter(displayName="Code file", name="code_file",
                                    datatype="DEFile", parameterType="Required",
                                    direction="Input")
        live_dir = arcpy.Parameter(displayName="Live queue folder", name="live_dir",
                                   datatype="DEFolder", parameterType="Required",
                                   direction="Input")
        cmd_id = arcpy.Parameter(displayName="Command id", name="cmd_id",
                                 datatype="GPString", parameterType="Required",
                                 direction="Input")
        return [code_file, live_dir, cmd_id]

    def execute(self, parameters, messages):
        code_file = parameters[0].valueAsText
        live_dir = parameters[1].valueAsText
        cmd_id = parameters[2].valueAsText

        buf = io.StringIO()
        resp = {"id": cmd_id, "ok": True}
        try:
            with open(code_file, encoding="utf-8") as fh:
                code = fh.read()
            ns = {"arcpy": arcpy, "__name__": "__arcclaude_live__"}
            tree = ast.parse(code, mode="exec")
            last = None
            if tree.body and isinstance(tree.body[-1], ast.Expr):
                last = ast.Expression(tree.body.pop(-1).value)
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                exec(compile(tree, "<arcclaude-live>", "exec"), ns)
                if last is not None:
                    value = eval(compile(last, "<arcclaude-live>", "eval"), ns)
                    if value is not None:
                        resp["result"] = repr(value)
        except BaseException as exc:  # report, never raise — the queue must flow
            resp = {"id": cmd_id, "ok": False,
                    "error": "%s: %s" % (type(exc).__name__, exc),
                    "traceback": traceback.format_exc(limit=15)}
        resp["stdout"] = buf.getvalue()

        tmp = os.path.join(live_dir, "result_%s.tmp" % cmd_id)
        out = os.path.join(live_dir, "result_%s.json" % cmd_id)
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(resp, fh, ensure_ascii=False, default=repr)
        os.replace(tmp, out)
        messages.addMessage("ARCclaude command %s -> %s" % (cmd_id, "ok" if resp["ok"] else "ERROR"))
