#!/usr/bin/env python3
"""Check the OpenDAP KiCad schematic colour theme against CRAFT-103.

Every schematic colour key has a role (pcb-craft-standard.md §9.1, CRAFT-103):

- text:   items KiCad draws as text or text with an outline (labels, fields, names); contrast on
          the background at least 4.5:1 (WCAG 2, 1.4.3).
- line:   wires, outlines, markers; at least 3:1 (WCAG 2, 1.4.11, non-text contrast).
- quiet:  grid, page limits, hidden items, private notes: drawn on purpose below the ink; no minimum.
- fill:   backgrounds and fills; must stay light enough that the ink on them keeps its ratio.
- interaction: hover, selection and drag feedback; the orange accent, never plotted.

The functional groups (ink, net, bus, interface, rail, assembly, error, warning) must be pairwise
distinct: CIE76 colour difference at least MIN_DELTA_E between the group colours. The error and
warning colours appear only on ERC keys, and the orange only on interaction keys.

Usage: check_theme.py [THEME.json] [--table]   (default: opendap.json next to this script)
Exit status: 0 pass, 1 a check failed, 2 usage or file error. Standard library only.
"""
import json
import os
import re
import sys

MIN_TEXT, MIN_LINE, MIN_DELTA_E = 4.5, 3.0, 20.0

# key: (role, functional group or None)
ROLES = {
    "background": ("background", None),
    "wire": ("line", "net"), "junction": ("line", "net"),
    "bus": ("line", "bus"), "bus_junction": ("line", "bus"),
    "label_local": ("text", "ink"),
    "label_hier": ("text", "interface"), "sheet_label": ("text", "interface"),
    "label_global": ("text", "rail"),
    "component_outline": ("line", "ink"), "pin": ("line", "ink"), "pin_name": ("text", "ink"),
    "reference": ("text", "ink"), "value": ("text", "ink"), "sheet": ("line", "ink"),
    "sheet_name": ("text", "ink"), "cursor": ("line", "ink"),
    "pin_number": ("text", "secondary"), "fields": ("text", "secondary"), "note": ("text", "secondary"),
    "sheet_fields": ("text", "secondary"), "sheet_filename": ("text", "secondary"),
    "netclass_flag": ("text", "secondary"), "worksheet": ("text", "secondary"),
    "aux_items": ("line", "secondary"), "op_currents": ("text", "secondary"),
    "op_voltages": ("text", "secondary"),
    "no_connect": ("line", "muted"), "anchor": ("line", "muted"), "rule_area": ("line", "muted"),
    "erc_exclusion": ("line", "muted"),
    "dnp_marker": ("line", "assembly"), "excluded_from_sim": ("line", "assembly"),
    "erc_error": ("line", "error"), "drag_net_collision": ("interaction", "error"),
    "erc_warning": ("line", "warning"),
    "brightened": ("interaction", "orange"), "hovered": ("interaction", "orange"),
    "shadow": ("interaction", "orange"),
    "grid": ("quiet", None), "grid_axes": ("quiet", None), "hidden": ("quiet", None),
    "page_limits": ("quiet", None), "private_note": ("quiet", None),
    "component_body": ("fill", None), "note_background": ("fill", None),
    "sheet_background": ("fill", None),
}
DISTINCT = ("ink", "net", "bus", "interface", "rail", "assembly", "error", "warning")
RESERVED = {"error": "erc", "warning": "erc", "orange": "interaction"}


def parse(value):
    m = re.fullmatch(r"rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)", value.strip())
    if not m:
        raise ValueError(f"not an rgb()/rgba() colour: {value!r}")
    return tuple(int(m.group(i)) for i in (1, 2, 3)), float(m.group(4) or 1.0)


def over(rgb, alpha, bg):
    return tuple(round(alpha * c + (1 - alpha) * b) for c, b in zip(rgb, bg))


def luminance(rgb):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def lab(rgb):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = [t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116 for t in (x, y, z)]
    return 116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])


def delta_e(a, b):
    return sum((p - q) ** 2 for p, q in zip(lab(a), lab(b))) ** 0.5


def check(theme):
    sch = theme.get("schematic")
    if not isinstance(sch, dict):
        return ["no 'schematic' section"], [], []
    errors, rows = [], []
    unknown = sorted(set(sch) - set(ROLES) - {"override_item_colors"})
    missing = sorted(set(ROLES) - set(sch))
    if unknown:
        errors.append(f"keys without a role (add them to ROLES): {unknown}")
    if missing:
        errors.append(f"keys missing from the theme: {missing}")
    if sch.get("override_item_colors") is not False:
        errors.append("override_item_colors must be false")
    bg, _ = parse(sch["background"])
    groups = {}
    for key, (role, group) in ROLES.items():
        if key not in sch or role == "background":
            continue
        rgb, alpha = parse(sch[key])
        seen = over(rgb, alpha, bg)
        ratio = contrast(seen, bg)
        need = {"text": MIN_TEXT, "line": MIN_LINE}.get(role)
        ok = need is None or ratio >= need
        if not ok:
            errors.append(f"{key}: {ratio:.2f}:1 on the background, {role} needs {need}:1")
        if role == "fill" and alpha > 0 and contrast(seen, bg) > 1.2:
            errors.append(f"{key}: a fill must stay within 1.2:1 of the background")
        if group in DISTINCT and role != "interaction":
            if group in groups and groups[group][1] != seen:
                errors.append(f"{key}: group '{group}' already uses {groups[group][1]} ({groups[group][0]})")
            groups.setdefault(group, (key, seen))
        reserved_for = RESERVED.get(group)
        if reserved_for == "erc" and not (key.startswith("erc_") or role == "interaction"):
            errors.append(f"{key}: the {group} colour is reserved for ERC markers")
        if reserved_for == "interaction" and role != "interaction":
            errors.append(f"{key}: the orange accent is reserved for interaction")
        rows.append((key, role, group or "", "#%02X%02X%02X" % seen, f"{ratio:.1f}", "ok" if ok else "FAIL"))
    names = [g for g in DISTINCT if g in groups]
    pairs = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            d = delta_e(groups[a][1], groups[b][1])
            pairs.append((a, b, d))
            if d < MIN_DELTA_E:
                errors.append(f"groups '{a}' and '{b}' are too close: ΔE76 {d:.1f} < {MIN_DELTA_E}")
    return errors, rows, pairs


def main(argv):
    table = "--table" in argv
    args = [a for a in argv if a != "--table"]
    if len(args) > 1 or any(a.startswith("-") for a in args):
        print(__doc__, file=sys.stderr)
        return 2
    path = args[0] if args else os.path.join(os.path.dirname(os.path.abspath(__file__)), "opendap.json")
    try:
        theme = json.load(open(path, encoding="utf-8"))
        errors, rows, pairs = check(theme)
    except (OSError, ValueError, KeyError) as e:
        print(f"check_theme: {path}: {e}", file=sys.stderr)
        return 2
    if table:
        print("| Key | Role | Group | Seen on background | Contrast | Result |\n|---|---|---|---|---|---|")
        for r in sorted(rows, key=lambda r: (r[2], r[0])):
            print("| `%s` | %s | %s | `%s` | %s:1 | %s |" % r)
        print("\n| Group | Group | ΔE76 |\n|---|---|---|")
        for a, b, d in pairs:
            print(f"| {a} | {b} | {d:.0f} |")
    for e in errors:
        print(f"check_theme: {e}", file=sys.stderr)
    if not errors and not table:
        print(f"{os.path.basename(path)}: {len(rows)} colours pass")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
