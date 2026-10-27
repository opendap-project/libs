"""Build a DRC test board for a kicad-lib rule set.

Shared by every `design-rules/<set>/test/make_test_board.py`. It reads the
rule set's `.kicad_dru`, takes each rule's value from it, and places one
object just past the limit (FAIL column) and one just inside it (PASS column)
per rule. `check_drc.py` then runs KiCad's DRC and compares the result with
the `.expected.json` written here.

Runs under the Python bundled with KiCad (it needs the `pcbnew` module).
Keep it compatible with Python 3.9, the version KiCad 10 ships on macOS.
"""

from __future__ import annotations

import json
import os
import re
import sys

try:
    import pcbnew
except ImportError:  # pragma: no cover
    sys.exit(
        "pcbnew not found: run this with KiCad's Python, for example\n"
        "  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/"
        "Versions/Current/bin/python3 make_test_board.py")

# Margin between a rule's limit and the test objects on either side of it.
DELTA = 0.01  # mm

# Layout (mm). Labels on the left, failing objects in the middle, passing
# objects on the right. check_drc.py rejects any violation right of PASS_EDGE.
LABEL_X = 2.0
FAIL_X = 40.0
PASS_X = 54.0
PASS_EDGE = 50.0
BOARD_W = 66.0
ROW_H = 3.5
TOP = 8.0

MIL = 0.0254


def mm(value: float) -> int:
    return pcbnew.FromMM(value)


def pt(x: float, y: float):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def to_mm(token: str) -> float:
    """'3mil' -> 0.0762, '0.2mm' -> 0.2."""
    m = re.fullmatch(r"([0-9.]+)(mm|mil|in)?", token)
    if not m:
        raise ValueError(f"cannot read a length from '{token}'")
    value = float(m.group(1))
    unit = m.group(2) or "mm"
    return value * {"mm": 1.0, "mil": MIL, "in": 25.4}[unit]


# --- .kicad_dru reader ---------------------------------------------------

def _tokenize(text: str):
    text = "\n".join(line for line in text.splitlines()
                     if not line.lstrip().startswith("#"))
    return re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', text)


def _parse(tokens, i=0):
    out = []
    while i < len(tokens):
        tok = tokens[i]
        if tok == "(":
            sub, i = _parse(tokens, i + 1)
            out.append(sub)
        elif tok == ")":
            return out, i + 1
        else:
            out.append(tok[1:-1] if tok.startswith('"') else tok)
            i += 1
    return out, i


class Rule:
    def __init__(self, sexpr):
        self.name = sexpr[1]
        self.layer = None
        self.condition = None
        self.constraints = {}
        for item in sexpr[2:]:
            if item[0] == "layer":
                self.layer = item[1]
            elif item[0] == "condition":
                self.condition = item[1]
            elif item[0] == "constraint":
                values = {}
                for arg in item[2:]:
                    if isinstance(arg, list) and arg[0] in ("min", "max", "opt"):
                        values[arg[0]] = to_mm(arg[1])
                self.constraints[item[1]] = values

    def value(self, constraint: str, which: str = "min") -> float:
        return self.constraints[constraint][which]


def read_rules(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        tree, _ = _parse(_tokenize(fh.read()))
    rules = {}
    for node in tree:
        if isinstance(node, list) and node and node[0] == "rule":
            rule = Rule(node)
            rules[rule.name] = rule
    return rules


# --- Board builder -------------------------------------------------------

class TestBoard:
    """A board with one row per rule: label, failing object, passing object."""

    def __init__(self, name: str, dru_path: str, copper_layers: int,
                 mask_expansion: float = 0.0, mask_min_web: float = 0.0):
        pcbnew.KIID.SeedGenerator(1)  # reproducible UUIDs between runs
        self.name = name
        self.rules = read_rules(dru_path)
        self.board = pcbnew.BOARD()
        self.board.SetCopperLayerCount(copper_layers)
        ds = self.board.GetDesignSettings()
        ds.m_SolderMaskExpansion = mm(mask_expansion)
        ds.m_SolderMaskMinWidth = mm(mask_min_web)
        self.mask_expansion = mask_expansion
        self.mask_min_web = mask_min_web
        self.row = 0
        self.expected_rules = {}
        self.expected_checks = {}
        self._nets = 0
        self._refs = 0
        self._cutouts = []
        self._net_classes = []
        self._label(FAIL_X, TOP - 4.0, "FAIL", 1.0)
        self._label(PASS_X, TOP - 4.0, "PASS", 1.0)

    # helpers -------------------------------------------------------------
    def rule(self, name: str) -> Rule:
        if name not in self.rules:
            raise KeyError(f"rule '{name}' is not in the rule set")
        return self.rules[name]

    def _net(self, prefix="N"):
        self._nets += 1
        net = pcbnew.NETINFO_ITEM(self.board, f"{prefix}{self._nets}")
        self.board.Add(net)
        return net

    def _label(self, x, y, text, size=0.6):
        t = pcbnew.PCB_TEXT(self.board)
        t.SetText(text)
        t.SetLayer(pcbnew.Cmts_User)
        t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
        t.SetTextThickness(mm(size * 0.15))
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
        t.SetPosition(pt(x, y))
        self.board.Add(t)

    def _footprint(self, x, y, attr):
        self._refs += 1
        fp = pcbnew.FOOTPRINT(self.board)
        fp.SetReference(f"T{self._refs}")
        fp.SetValue("test")
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        fp.SetAttributes(attr | pcbnew.FP_BOARD_ONLY)
        fp.SetPosition(pt(x, y))
        self.board.Add(fp)
        return fp

    def _pad(self, fp, x, y, size, kind="smd", drill=0.0, bga=False, net=None,
             shape=None):
        pad = pcbnew.PAD(fp)
        pad.SetNumber("1")
        pad.SetPosition(pt(x, y))
        sx, sy = (size, size) if not isinstance(size, tuple) else size
        pad.SetSize(pcbnew.VECTOR2I(mm(sx), mm(sy)))
        if kind == "smd":
            pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
            pad.SetLayerSet(pad.SMDMask())
            pad.SetShape(shape or (pcbnew.PAD_SHAPE_CIRCLE if bga else pcbnew.PAD_SHAPE_RECT))
        elif kind == "pth":
            pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
            pad.SetLayerSet(pad.PTHMask())
            pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
            pad.SetDrillSize(pcbnew.VECTOR2I(mm(drill), mm(drill)))
        elif kind == "npth":
            pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
            pad.SetLayerSet(pad.UnplatedHoleMask())
            pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
            pad.SetDrillSize(pcbnew.VECTOR2I(mm(drill), mm(drill)))
        if bga:
            pad.SetProperty(pcbnew.PAD_PROP_BGA)
        if net is not None:
            pad.SetNet(net)
        fp.Add(pad)
        return pad

    def _track(self, x1, y1, x2, y2, width, layer, net=None):
        t = pcbnew.PCB_TRACK(self.board)
        t.SetStart(pt(x1, y1))
        t.SetEnd(pt(x2, y2))
        t.SetWidth(mm(width))
        t.SetLayer(layer)
        t.SetNet(net if net is not None else self._net())
        self.board.Add(t)
        return t

    def _via(self, x, y, drill, diameter, vtype=None, layers=None, net=None):
        v = pcbnew.PCB_VIA(self.board)
        v.SetViaType(vtype if vtype is not None else pcbnew.VIATYPE_THROUGH)
        v.SetPosition(pt(x, y))
        v.SetDrill(mm(drill))
        v.SetWidth(mm(diameter))
        if layers:
            v.SetLayerPair(*layers)
        v.SetNet(net if net is not None else self._net())
        self.board.Add(v)
        return v

    def _text(self, x, y, layer, height, thickness, text="Ab", width=None,
              angle=0.0, italic=False, mirrored=False):
        t = pcbnew.PCB_TEXT(self.board)
        t.SetText(text)
        t.SetLayer(layer)
        t.SetTextSize(pcbnew.VECTOR2I(mm(width if width is not None else height), mm(height)))
        t.SetTextThickness(mm(thickness))
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
        t.SetTextAngleDegrees(angle)
        t.SetItalic(italic)
        t.SetMirrored(mirrored)
        t.SetPosition(pt(x, y))
        self.board.Add(t)
        return t

    def _silk_line(self, x1, y1, x2, y2, width, layer=None):
        s = pcbnew.PCB_SHAPE(self.board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pt(x1, y1))
        s.SetEnd(pt(x2, y2))
        s.SetWidth(mm(width))
        s.SetLayer(layer if layer is not None else pcbnew.F_SilkS)
        self.board.Add(s)
        return s

    def _rule_area(self, name, x1, y1, x2, y2):
        """A keepout-free rule area, used only to scope rules by its name."""
        z = pcbnew.ZONE(self.board)
        z.SetIsRuleArea(True)
        z.SetZoneName(name)
        z.SetLayerSet(pcbnew.LSET.AllCuMask())
        for allow in ("SetDoNotAllowTracks", "SetDoNotAllowVias", "SetDoNotAllowPads",
                      "SetDoNotAllowZoneFills", "SetDoNotAllowFootprints"):
            getattr(z, allow)(False)
        outline = z.Outline()
        outline.NewOutline()
        for x, y in ((x1, y1), (x2, y1), (x2, y2), (x1, y2)):
            outline.Append(mm(x), mm(y))
        self.board.Add(z)
        return z

    def _row(self, label, builder, expect_rule=None, expect_check=None, count=1):
        y = TOP + self.row * ROW_H
        self._label(LABEL_X, y, label)
        builder(FAIL_X, y, True)
        builder(PASS_X, y, False)
        if expect_rule:
            self.expected_rules[expect_rule] = self.expected_rules.get(expect_rule, 0) + count
        if expect_check:
            self.expected_checks[expect_check] = self.expected_checks.get(expect_check, 0) + count
        self.row += 1

    def add_row(self, label, builder, expect_rule=None, expect_check=None, count=1):
        """A free-form row: builder(x, y, fail) draws the failing or the passing
        object. count is how many violations the failing object raises."""
        self._row(label, builder, expect_rule, expect_check, count)

    @staticmethod
    def _v(limit, fail, kind="min"):
        """A value just past the limit (fail) or just inside it (pass)."""
        if kind == "min":
            return limit - DELTA if fail else limit + DELTA
        return limit + DELTA if fail else limit - DELTA

    # fixtures ------------------------------------------------------------
    # Each takes the rule name and draws a failing and a passing object
    # sized from the rule's own value, so the board follows the rules file.

    def track_width(self, name, layer):
        w = self.rule(name).value("track_width")

        def build(x, y, fail):
            self._track(x, y, x + 3, y, self._v(w, fail), layer)
        self._row(name, build, name)

    def track_clearance(self, name, layer, width):
        gap = self.rule(name).value("clearance")

        def build(x, y, fail):
            g = self._v(gap, fail)
            self._track(x, y, x + 3, y, width, layer)
            self._track(x, y + width + g, x + 3, y + width + g, width, layer)
        self._row(name, build, name)

    def bga_pad_to_track(self, name, pad, width):
        gap = self.rule(name).value("clearance")

        def build(x, y, fail):
            fp = self._footprint(x, y, pcbnew.FP_SMD)
            self._pad(fp, x, y, pad, bga=True, net=self._net())
            ty = y + pad / 2 + self._v(gap, fail) + width / 2
            self._track(x - 1, ty, x + 2, ty, width, pcbnew.F_Cu)
        self._row(name, build, name)

    def bga_pad_size(self, name, limit):
        def build(x, y, fail):
            fp = self._footprint(x, y, pcbnew.FP_SMD)
            self._pad(fp, x, y, self._v(limit, fail), bga=True, net=self._net())
        self._row(name, build, name)

    def pad_size_pth(self, name, limit, drill):
        def build(x, y, fail):
            fp = self._footprint(x, y, pcbnew.FP_THROUGH_HOLE)
            self._pad(fp, x, y, self._v(limit, fail), kind="pth", drill=drill,
                      net=self._net())
        self._row(name, build, name)

    def via_drill(self, name, ring, vtype=None, layers=None):
        drill = self.rule(name).value("hole_size")

        def build(x, y, fail):
            d = self._v(drill, fail)
            self._via(x, y, d, d + 2 * ring, vtype, layers)
        self._row(name, build, name)

    def via_ring(self, name, drill, vtype=None, layers=None):
        ring = self.rule(name).value("annular_width")

        def build(x, y, fail):
            self._via(x, y, drill, drill + 2 * self._v(ring, fail), vtype, layers)
        self._row(name, build, name)

    def via_diameter(self, name, drill):
        dia = self.rule(name).value("via_diameter")

        def build(x, y, fail):
            self._via(x, y, drill, self._v(dia, fail))
        self._row(name, build, name)

    def via_hole_to_hole(self, name, drill, diameter):
        h2h = self.rule(name).value("hole_to_hole")

        def build(x, y, fail):
            net = self._net()  # same net: overlapping copper is no short
            self._via(x, y, drill, diameter, net=net)
            self._via(x + drill + self._v(h2h, fail), y, drill, diameter, net=net)
        self._row(name, build, name)

    def hole_to_copper(self, name, layer, hole, width):
        gap = self.rule(name).value("hole_clearance")

        def build(x, y, fail):
            fp = self._footprint(x, y, pcbnew.FP_THROUGH_HOLE)
            self._pad(fp, x, y, hole, kind="npth", drill=hole)
            ty = y + hole / 2 + self._v(gap, fail) + width / 2
            self._track(x - 1, ty, x + 2, ty, width, layer)
        self._row(name, build, name)

    def edge_clearance(self, name, width):
        gap = self.rule(name).value("edge_clearance")

        def build(x, y, fail):
            # a 1 x 1 mm internal cutout, with a track below it
            self._cutouts.append((x, y - 0.5, x + 1, y + 0.5))
            ty = y + 0.5 + self._v(gap, fail) + width / 2
            self._track(x - 1, ty, x + 2, ty, width, pcbnew.F_Cu)
        self._row(name, build, name)

    def silk_thickness(self, name, height):
        limit = self.rule(name).value("text_thickness")

        def build(x, y, fail):
            self._text(x, y, pcbnew.F_SilkS, height, self._v(limit, fail))
        self._row(name, build, name)

    def silk_height(self, name, thickness):
        limit = self.rule(name).value("text_height")

        def build(x, y, fail):
            self._text(x, y, pcbnew.F_SilkS, self._v(limit, fail), thickness)
        self._row(name, build, name)

    def disallowed_via(self, name, vtype, layers, drill, diameter):
        def build(x, y, fail):
            if fail:
                self._via(x, y, drill, diameter, vtype, layers)
            else:
                self._via(x, y, drill, diameter)
        self._row(name, build, name)

    def mask_web(self, label, pad):
        """Board Setup check, not a custom rule: solder mask minimum web."""
        web, exp = self.mask_min_web, self.mask_expansion

        def build(x, y, fail):
            gap = self._v(web, fail) + 2 * exp  # copper gap for that web
            for dx in (0.0, pad + gap):
                fp = self._footprint(x + dx, y, pcbnew.FP_SMD)
                self._pad(fp, x + dx, y, pad, net=self._net())
        self._row(label, build, expect_check="solder_mask_bridge")

    # output --------------------------------------------------------------
    def add_net_class(self, name, pattern):
        """A net class assigned by net-name pattern in the project file."""
        self._net_classes.append((name, pattern))

    def save(self, out_dir: str, ignore_checks=()):
        height = TOP + self.row * ROW_H + 2.0
        self._rect(0, 0, BOARD_W, height)
        for c in self._cutouts:
            self._rect(*c)
        pcb = os.path.join(out_dir, f"{self.name}.kicad_pcb")
        pcbnew.SaveBoard(pcb, self.board)
        self._write_project(out_dir, ignore_checks)
        expected = {
            "rules": self.expected_rules,
            "board_setup_checks": self.expected_checks,
            "pass_column_starts_at_mm": PASS_EDGE,
        }
        with open(os.path.join(out_dir, f"{self.name}.expected.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(expected, fh, indent=2, sort_keys=True)
            fh.write("\n")
        return pcb

    def _rect(self, x1, y1, x2, y2):
        r = pcbnew.PCB_SHAPE(self.board)
        r.SetShape(pcbnew.SHAPE_T_RECT)
        r.SetStart(pt(x1, y1))
        r.SetEnd(pt(x2, y2))
        r.SetLayer(pcbnew.Edge_Cuts)
        r.SetWidth(mm(0.05))
        self.board.Add(r)

    def _write_project(self, out_dir, ignore_checks):
        # Board Setup minimums at zero, so only the custom rules decide.
        zero = {k: 0.0 for k in (
            "min_clearance", "min_connection", "min_copper_edge_clearance",
            "min_groove_width", "min_hole_clearance", "min_hole_to_hole",
            "min_microvia_diameter", "min_microvia_drill", "min_silk_clearance",
            "min_text_height", "min_text_thickness", "min_through_hole_diameter",
            "min_track_width", "min_via_annular_width", "min_via_diameter")}
        def net_class(name, priority):
            return {
                "name": name, "priority": priority,
                "clearance": 0.0, "track_width": 0.0,
                "via_diameter": 0.4, "via_drill": 0.2,
                "microvia_diameter": 0.2, "microvia_drill": 0.1,
                "diff_pair_gap": 0.1, "diff_pair_width": 0.1,
                "diff_pair_via_gap": 0.1,
            }
        net_settings = {"classes": [net_class("Default", 2147483647)],
                        "meta": {"version": 4}}
        if self._net_classes:
            net_settings["classes"] += [net_class(n, i) for i, (n, _) in
                                        enumerate(self._net_classes)]
            net_settings["netclass_patterns"] = [
                {"netclass": n, "pattern": p} for n, p in self._net_classes]
        project = {
            "board": {"design_settings": {
                "rules": zero,
                "rule_severities": {c: "ignore" for c in ignore_checks},
            }},
            "meta": {"filename": f"{self.name}.kicad_pro", "version": 3},
            "net_settings": net_settings,
        }
        with open(os.path.join(out_dir, f"{self.name}.kicad_pro"), "w",
                  encoding="utf-8") as fh:
            json.dump(project, fh, indent=2, sort_keys=True)
            fh.write("\n")


# Checks that only concern how the test board is drawn (footprints made in
# code, objects deliberately left unconnected), never a fab limit.
TEST_BOARD_IGNORED_CHECKS = (
    "lib_footprint_issues",
    "lib_footprint_mismatch",
    "track_dangling",
    "via_dangling",
    "missing_courtyard",
)
