#!/usr/bin/env python3
"""Build the 3D models (STEP) of kicad-lib's BGA parts with FreeCAD.

Usage (FreeCAD's command-line interpreter runs the script; arguments go through the environment):

    KIGEN_ROOT=<kicad-lib> /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd generator/bga_model.py

Reads generator/bga/<Library>/<footprint>.model.json (written by bga.py: body size and height above
the stand-off, ball diameter and stand-off, ball centres in the footprint frame with +y down) and
writes 3dmodels/<Library>.3dshapes/<footprint>.step: the body as a box on the stand-off and each
ball as a cylinder of the nominal diameter and the nominal stand-off height. The models are
envelopes drawn from the datasheet dimensions (parts-lib ADR 0001: OpenDAP's own, scripted,
reproducible), not manufacturer models. The STEP header timestamp is fixed so a rebuild is stable.
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
    bx, by, bz = m["body"]
    a1, d = m["standoff"], m["ball"]
    body = Part.makeBox(bx, by, bz, FreeCAD.Vector(-bx / 2, -by / 2, a1))
    # KiCad's 3D frame: +y up; the footprint frame has +y down
    balls = [Part.makeCylinder(d / 2, a1, FreeCAD.Vector(x, -y, 0)) for x, y in m["balls"]]
    shape = Part.makeCompound([body] + balls)
    out = os.path.join(ROOT, "3dmodels", m["library"] + ".3dshapes", m["name"] + ".step")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    shape.exportStep(out)
    with open(out) as fh:
        text = fh.read()
    text = re.sub(r"FILE_NAME\('[^']*','[^']*'", "FILE_NAME('%s','%s'" % (m["name"] + ".step", STAMP), text, count=1)
    with open(out, "w") as fh:
        fh.write(text)
    return out


for p in sorted(glob.glob(os.path.join(ROOT, "generator", "bga", "*", "*.model.json"))):
    print(os.path.relpath(build_one(p), ROOT))
