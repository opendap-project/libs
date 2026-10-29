# Library generator

`kigen.py` generates symbols, footprints and 3D envelope models from one data file per part, `parts/<key>/<MPN>.toml`. (BGA parts have their own generator, `bga.py`, with its own checks; generic symbols that are not one orderable part, such as the crystals of `symbols/opendap-generic.kicad_sym`, come from `generic.py`.) The data file is the reviewed source: every dimension in it cites the manufacturer document, revision and page it was transcribed from, and anything a primary source does not give is marked **UNVERIFIED**. Never edit the generated files by hand.

One library may hold parts of both generators (the RK809-5 from `kigen.py` and the RK3566 from `bga.py` share their maker's library): `symlib.py` gives both the same file, every symbol of the library sorted by name, so neither generator overwrites the other's symbols (`test_symlib.py`).

## Use

```sh
python3 generator/kigen.py              # writes symbols/, footprints/ and generator/models/
python3 generator/generic.py            # writes symbols/opendap-generic.kicad_sym
KIGEN_ROOT=$PWD /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd generator/model.py
                                        # writes 3dmodels/<key>.3dshapes/<footprint>.step
python3 generator/test_library.py       # the checks below
```

Python 3.11 or later (`tomllib`); KiCad 10 (`kicad-cli`) for the load and plot checks; FreeCAD for the STEP models.

## What the generator produces

- **Symbols** (`symbols/<key>.kicad_sym`): one per part, named after the MPN, with the `Manufacturer`, `MPN`, `Datasheet`, `Description` and `Footprint` fields, and `Second_Source` where the BOM names one. Pin ends on the 2.54 mm grid (CRAFT-122; a side with an even pin count leaves its centre empty rather than landing on ±1.27 mm); inputs and control left, outputs right, supplies top, grounds bottom; no hidden pins. Large parts are split into units by function (`[[units]]`; the RK809-5 by rail group), at most 64 pins per unit (CRAFT-126; a connector by contact group, the DF40C in two units of 50).
- **Footprints** (`footprints/<key>.pretty/`): pads as the data gives them; the anchor at the body centroid for SMD parts and at pin 1 for through-hole parts (CRAFT-15); silk outline 0.15 mm, clipped 0.15 mm clear of every pad (CRAFT-05, CRAFT-07); reference 1.0 × 0.15 mm on the silk (CRAFT-02); a filled pin-1 triangle without stroke, outside the body (CRAFT-13); fab body outline with a pin-1 chamfer and `${REFERENCE}` (KLC F5.2, CRAFT-11); courtyard 0.05 mm on a 0.01 mm grid at the KLC F5.3 clearance of the part's class.
- **3D models** (`3dmodels/<key>.3dshapes/`): envelope boxes from the datasheet body dimensions, OpenDAP's own (parts-lib ADR 0001). Manufacturer STEP files are never committed unless their licence allows it; they are listed in the parts-lib `manifest.toml` and fetched into the local cache.
- **Envelope models for lands the library does not draw** (`envelopes.toml`): KiCad stock footprints whose KiCad 10 library ships no model (the Littelfuse NANO2 fuse, the TI DPY0002A, SOT-523, the Coilcraft XxL4020 land by height) and project lands of OpenDAP boards (inductors, the PTS815 switch, Vishay WSL shunts, shield-can frames). Each entry names its key and STEP name, the land it fits, the document it cites and its boxes; `kigen.py` writes them to `generator/models/` and `model.py` builds them with the rest. A consumer's footprint references `${OPENDAP_KICAD_3DMODELS}/<key>.3dshapes/<name>.step`.

Footprints reference their model as `${OPENDAP_KICAD_3DMODELS}/…`, a project text variable, so the library assumes nothing about where a consumer keeps it.

## Checks (`test_library.py`)

- the generated files are up to date with the data, and every footprint and every envelope (with its citation) has its STEP model; a malformed envelope entry is refused;
- symbol pin numbers and names match the datasheet's pin table, transcribed separately in `parts/<key>/pins/<part>.toml` (see below); `sheet_name` and `sheet_number` record where the symbol deliberately differs from the table's text, and `sheet_pins = "none: <reason>"` marks a part whose datasheet has no pin table;
- symbol pins match the footprint's numbered copper pads; the symbol fields are filled;
- the pads read back from each `.kicad_mod` match the drawing values transcribed in `[[checks]]` (pitch, offsets, pad sizes, pad count, and a copper ring's radii and offset: `ring`, `ring_dy`); inline fixtures check the ring, ring-sector and polygon pads;
- the footprint rules of the craft standard listed above;
- every symbol library, including the BGA and generic ones, passes the symbol rules a library carries: pin ends on the 2.54 mm grid (1.27 mm for two-pin discretes, CRAFT-122), no hidden pins (CRAFT-125), at most 64 pins per unit (CRAFT-126), a KLC reference prefix (CRAFT-130); an inline bad symbol proves each rule fails;
- `kicad-cli` loads, upgrades and plots every library.

## Data file

Top-level tables: `[part]` (MPN, manufacturer, library, datasheet and its revision, notes), `[[pins]]` (number, name, electrical type, side, unit), `[[units]]`, `[footprint]` with `body` (and `datasheet` where several parts share one land, so the footprint file is the same whichever part writes it), `[[footprint.pads]]`, `[[footprint.rows]]`, `[[footprint.paste]]`, `[[footprint.vias]]`, `[[footprint.rings]]` and `[[footprint.paste_sectors]]` (custom pads from `custom_pads.py`: a copper ring around a bottom-port microphone's acoustic port, its paste split into parallel-gap sectors; the port itself is an `np_thru_hole` pad), `[[footprint.polys]]` (polygon pads from `custom_pads.py`: `smd` for a non-solder-mask-defined land, or a `copper` pad plus an `aperture` pad with the same number for a solder-mask-defined one, as TI's RXS0016A pads 6, 7 and 8), optional `[[footprint.model]]` boxes and `[footprint.pin1_mark]`, and `[[checks]]`. Coordinates are in millimetres, top view, +y down. `land_pattern` records where the pads come from: `manufacturer` (the recommended land pattern as given), `drawing` (a connector's recommended PCB layout) or `ipc7351b` (derived, with the derivation in comments).

### Lifecycle and second sources (`[part]`, PLIB-003)

Optional in `[part]` of a part here or in `bga/`; `test_library.py` checks their shape and that every part that carried them still does:

```toml
lifecycle = { status = "Active", source = "TI product page", read = "2026-10-24" }   # as the manufacturer states it; note = "..." optional
second_sources = [{ part = "TPS628691ARQYR", note = "on the same land" }]           # [] when none was found
```

`status = "Not stated"` may leave out `source` and `read`. The BOM's chosen alternative stays in `second_source`, the string written to the symbol's `Second_Source` field.

### Pin table (`parts/<key>/pins/<part>.toml`)

A second reading of the datasheet for the pin check, kept apart from the data that builds the symbol (the same split as the BGA parts' `<Part>-pins.csv`). The file has the part's file name and three keys, and the test rejects any other shape:

```toml
datasheet_rev = "BAT54 v.6 (1 July 2022)"   # equal to the part's [part] datasheet_rev
cite = "Pinning (Table 2, p. 2)"            # the page, table or drawing sheet of the pin table
[pins]                                      # pin number = name, as the datasheet prints them
"1" = "A"
"2" = "n.c."
"3" = "K"
```
