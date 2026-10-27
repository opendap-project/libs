# ADR 0002: The public form of a part

- **Status:** Accepted
- **Date:** 2026-10-27
- **Basis:** the maintainers' rule that the libraries publish the outputs a design and its checks read, and not the working transcriptions behind them
- **Supersedes:** [ADR 0001](0001-part-data-in-repo-and-local-cache.md) (the spec sheets; its local cache and manifest stand)

## Context

ADR 0001 published one spec sheet per part, `<key>/<MPN>.md`, transcribing ratings, operating conditions, power by mode, pinout, footprint, application notes and design notes from the datasheet. No generator reads a spec sheet: the KiCad symbols, footprints and 3D models are built from the generator data in [`kicad/generator/parts/`](../../../kicad/generator/README.md), where each value cites its datasheet page. The only reader was the symbol pin check (`kicad/generator/test_library.py`), which compared the symbol pins with the sheet's pin table.

## Decision

1. Spec sheets are no longer published. The libraries carry no `<key>/<MPN>.md` files and no spec sheet template.
2. A part's public form is:
   - its entries in [`manifest.toml`](../../manifest.toml): official URL, revision, date and sha256 of each external file, read by `toolkit-hardware`'s `tools/parts-sync.py` to fetch and verify the datasheet;
   - its KiCad generator data, `kicad/generator/parts/<key>/<part>.toml` (or `kicad/generator/bga/<key>/<Part>.toml`), each value citing the datasheet page;
   - the generated symbol, footprint and 3D model;
   - any second reading of the datasheet that a check needs, stored as data next to the generator part: `kicad/generator/parts/<key>/pins/<part>.toml` (the pin table: datasheet revision, page citation, pin number to name), and the BGA parts' `<Part>-pins.csv` and `<Part>-ballmap.txt`.
3. The local cache of ADR 0001 is unchanged: manufacturer files stay out of the repository unless their licence allows redistribution, and they are fetched from the manifest's URLs and verified by sha256.

## Consequences

- The symbol pin check runs on every checkout: it reads the pin tables next to the generator data and no longer depends on the spec sheets being present.
- A value a board document relies on (a rating, a power figure, an application circuit) is stated in that document with its datasheet page, not by linking a spec sheet.
- Consumers that read `<key>/<MPN>.md` from this repository lose those files from v0.3.0.
