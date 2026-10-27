"""One symbol library that several generators fill.

A maker key names one library, whichever generator draws its parts: in rockchip.kicad_sym, kigen.py draws the
RK809-5 PMIC and bga.py the RK3566 SoC. Each generator renders its own symbols of a library and passes the text
to merged(), which adds the symbols the other generators draw for the same library (rendered from their data in
this repository), so both generators write the same file and neither overwrites the other's symbols. A library
only one generator fills is written exactly as that generator renders it.

The merged file keeps the header of the first generator by name and the symbols sorted by name.
"""
from __future__ import annotations

import functools
import glob
import os
import tomllib

GENERATORS = ("opendap-bga", "opendap-kigen")


@functools.cache
def _bga_libraries():
    import bga
    out = {}
    for path in bga.part_paths([]):
        with open(path, "rb") as fh:
            lib = tomllib.load(fh)["part"]["library"]
        out.setdefault(lib, []).append(path)
    return out


@functools.cache
def _kigen_libraries():
    import kigen
    out = {}
    for path in sorted(glob.glob(os.path.join(kigen.PARTS, "*", "*.toml"))):
        with open(path, "rb") as fh:
            lib = tomllib.load(fh)["part"]["library"]
        out.setdefault(lib, []).append(path)
    return out


def _render(generator, lib):
    """The library text another generator renders for `lib`, or None when it draws no part of it."""
    if generator == "opendap-bga":
        paths = _bga_libraries().get(lib)
        if not paths:
            return None
        import bga
        return bga.symbol_lib([bga.load(p) for p in paths])
    paths = _kigen_libraries().get(lib)
    if not paths:
        return None
    import kigen
    return kigen.symbol_lib(kigen.load_parts(paths))


def split(text):
    """(header lines, [(symbol name, block lines)]) of a library whose top-level symbols are tab-indented."""
    lines = text.rstrip("\n").split("\n")
    head, blocks, cur = [], [], None
    for line in lines[:-1]:  # the last line closes the library
        if line.startswith("\t(symbol "):
            cur = (line.split('"')[1], [line])
            blocks.append(cur)
        elif cur is not None:
            cur[1].append(line)
            if line == "\t)":
                cur = None
        else:
            head.append(line)
    return head, blocks


def merged(lib, generator, text):
    """`text` (the library as `generator` renders it) with the symbols the other generators draw for `lib`."""
    texts = {generator: text}
    for other in GENERATORS:
        if other != generator:
            t = _render(other, lib)
            if t is not None:
                texts[other] = t
    if len(texts) == 1:
        return text
    head, blocks = None, []
    for g in sorted(texts):
        h, b = split(texts[g])
        head = head or h
        blocks += b
    names = [n for n, _ in blocks]
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup:
        raise ValueError("%s: symbols drawn by two generators: %s" % (lib, ", ".join(dup)))
    body = [line for _, b in sorted(blocks) for line in b]
    return "\n".join(head + body + [")"]) + "\n"
