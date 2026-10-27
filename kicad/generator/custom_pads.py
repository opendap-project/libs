"""Custom-shape pads for kigen.py: annular copper rings and segmented ring paste apertures.

A bottom-port MEMS microphone lands on a copper ring around its acoustic port, with the paste on
that ring split into sectors (for example Infineon IM73D122V01, datasheet v1.00 Figure 13). KiCad
draws both as custom pads: a small circular anchor plus primitives. This module turns the data
tables below into pad dicts that kigen.py places, clips silk around and writes.

    [[footprint.rings]]            copper ring: number, center, inner and outer radius, anchor
                                   diameter; mask opening as the copper, no paste
    [[footprint.paste_sectors]]    paste-only ring sectors: center, inner and outer radius, count,
                                   gap (width of the parallel-sided gaps), first_gap (degrees,
                                   the centre line of the first gap, from +x towards +y)

Coordinates in millimetres, top view, +y down, in the data frame (kigen.frame() moves them).
"""

from __future__ import annotations

import math

ARC_STEPS = 8  # straight segments per sector arc (0.1 mm chord error stays below 0.002 mm at R1)


def ring_pads(fp):
    """One custom copper pad per [[footprint.rings]] entry. The anchor sits on the ring (at its top),
    never on the centre, so no copper lands in the acoustic port."""
    pads = []
    for r in fp.get("rings", []):
        cx, cy = r["center"]
        ri, ro = r["inner"], r["outer"]
        if not 0 < ri < ro:
            raise ValueError("ring %s: inner radius must be positive and below the outer" % r["number"])
        mid, width = (ri + ro) / 2, ro - ri
        anchor = r.get("anchor", round(width * 0.8, 3))
        if anchor > width:
            raise ValueError("ring %s: anchor %.3f wider than the ring %.3f" % (r["number"], anchor, width))
        pads.append({"number": str(r["number"]), "type": "smd", "shape": "custom",
                     "at": [cx, cy - mid], "size": [anchor, anchor], "paste": False,
                     "custom": [("ring", (0.0, mid), mid, width)],
                     "extent": (-ro, mid - ro, ro, mid + ro)})
    return pads


def sector_points(ri, ro, a0, a1, gap):
    """Outline of the ring sector between the gap centre lines at angles a0 < a1 (radians), each
    gap parallel-sided: every straight edge sits gap/2 from its centre line."""
    h = gap / 2
    out0, out1 = a0 + math.asin(h / ro), a1 - math.asin(h / ro)
    in0, in1 = a0 + math.asin(h / ri), a1 - math.asin(h / ri)
    if in1 <= in0:
        raise ValueError("paste sector: gap %.3f leaves nothing at radius %.3f" % (gap, ri))
    pts = [(ro * math.cos(out0 + (out1 - out0) * k / ARC_STEPS), ro * math.sin(out0 + (out1 - out0) * k / ARC_STEPS))
           for k in range(ARC_STEPS + 1)]
    pts += [(ri * math.cos(in1 - (in1 - in0) * k / ARC_STEPS), ri * math.sin(in1 - (in1 - in0) * k / ARC_STEPS))
            for k in range(ARC_STEPS + 1)]
    return pts


def sector_pads(fp):
    """Paste-only custom pads, one per sector of each [[footprint.paste_sectors]] entry; the
    anchor (a small circle) sits at the sector's mid-radius, mid-angle point."""
    pads = []
    for s in fp.get("paste_sectors", []):
        cx, cy = s["center"]
        ri, ro, n, gap = s["inner"], s["outer"], s["count"], s["gap"]
        first = math.radians(s.get("first_gap", 0.0))
        step = 2 * math.pi / n
        mid = (ri + ro) / 2
        anchor = s.get("anchor", round((ro - ri) / 2, 3))
        for k in range(n):
            a0 = first + k * step
            am = a0 + step / 2
            ax, ay = mid * math.cos(am), mid * math.sin(am)
            pts = [(round(x - ax, 4), round(y - ay, 4)) for x, y in sector_points(ri, ro, a0, a0 + step, gap)]
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            pads.append({"number": "", "type": "paste", "shape": "custom",
                         "at": [cx + ax, cy + ay], "size": [anchor, anchor],
                         "custom": [("poly", pts)],
                         "extent": (min(xs), min(ys), max(xs), max(ys))})
    return pads


def primitives(p, S, Sym, num):
    """The (options …) and (primitives …) nodes of a custom pad."""
    prims = []
    for prim in p["custom"]:
        if prim[0] == "ring":
            _, (x, y), r, w = prim
            prims.append(S("gr_circle", S("center", num(x), num(y)), S("end", num(x + r), num(y)),
                           S("width", num(w)), S("fill", Sym("no"))))
        else:
            prims.append(S("gr_poly", S("pts", *[S("xy", num(x), num(y)) for x, y in prim[1]]),
                           S("width", 0), S("fill", Sym("yes"))))
    return [S("options", S("clearance", Sym("outline")), S("anchor", Sym("circle"))),
            S("primitives", *prims)]
