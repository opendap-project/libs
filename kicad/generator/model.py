#!/usr/bin/env python3
"""Build the 3D envelope models (STEP) of kicad-lib's generated footprints with FreeCAD.

Usage (FreeCAD's command-line interpreter runs the script; arguments go through the environment):

    KIGEN_ROOT=<kicad-lib> /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd generator/model.py

Reads generator/models/<Library>/<footprint>.json (written by kigen.py: boxes in mm, x/y in the
footprint frame with +y down, z from the board surface) and writes
3dmodels/<Library>.3dshapes/<footprint>.step. The models are envelopes drawn from the datasheet
body dimensions (parts-lib ADR 0001: OpenDAP's own, scripted, reproducible), not manufacturer
models. The STEP header timestamp is fixed so a rebuild is byte-stable.
"""

import glob
import json
import os
import re

import FreeCAD  # noqa: F401  (provided by freecadcmd)
import Part

ROOT = os.environ.get("KIGEN_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STAMP = "2026-01-01T00:00:00"


def build_one(path):
    with open(path) as fh:
        m = json.load(fh)
    solids = []
    for b in m["boxes"]:
        sx, sy, sz = b["size"]
        x, y, z0 = b["at"]
        # KiCad's 3D frame: +y up; the footprint frame has +y down
        solids.append(Part.makeBox(sx, sy, sz, FreeCAD.Vector(x - sx / 2, -y - sy / 2, z0)))
    shape = solids[0]
    for s in solids[1:]:
        shape = shape.fuse(s)
    out = os.path.join(ROOT, "3dmodels", m["library"] + ".3dshapes", m["name"] + ".step")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    shape.exportStep(out)
    with open(out) as fh:
        text = fh.read()
    text = re.sub(r"FILE_NAME\('[^']*','[^']*'", "FILE_NAME('%s','%s'" % (m["name"] + ".step", STAMP), text, count=1)
    # the translator names the product with a per-session counter: name it after the footprint
    text = re.sub(r"PRODUCT\('Open CASCADE STEP translator[^']*',\s*'Open CASCADE STEP translator[^']*'",
                  "PRODUCT('%s','%s'" % (m["name"], m["name"]), text)
    with open(out, "w") as fh:
        fh.write(text)
    return out


for p in sorted(glob.glob(os.path.join(ROOT, "generator", "models", "*", "*.json"))):
    print(os.path.relpath(build_one(p), ROOT))
