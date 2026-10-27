# Schematic templates

The schematic part of the [PCB craft standard](../docs/specs/pcb-craft-standard.md) (§9) as files a project uses directly. Every file here and in `drawing-sheets/` and `examples/load-switch/` is written by [`generate.py`](generate.py); edit the generator, never the outputs, and run it again:

```sh
python3 templates/generate.py   # needs KiCad 10 for its stock symbols; kicad-cli normalises the output
```

| Path | What it is |
|---|---|
| [`../drawing-sheets/opendap.kicad_wks`](../drawing-sheets/opendap.kicad_wks) | The OpenDAP drawing sheet (CRAFT-80, -100 to -104): frame with zone marks and the title block. Anchored to the page corners, so one file serves A4 and A3 |
| [`../colour-themes/opendap.json`](../colour-themes/opendap.json) | The OpenDAP schematic colour theme (CRAFT-103): graphite on white with one functional accent per drawing role (wires, buses, interface labels, rail labels, DNP). Written by hand, not by the generator; `../colour-themes/check_theme.py` checks contrast, distinctness and reserved colours (`--table` prints the measurements) |
| [`feature-block/feature-block.kicad_sch`](feature-block/feature-block.kicad_sch) | The sheet template for one feature block (RFC 0011): title block fields, interface labels at the edges, titled groups, interface and rail tables, notes. Placeholders in `<angle brackets>` |
| [`../examples/load-switch/`](../examples/load-switch/) | A complete example project, a switched peripheral supply, that passes every check of `odapkit craft check` at Q4 |

## Using them in a board project

1. kicad-lib is the project's submodule at `hardware/lib/opendap`. In Schematic Setup → Page Settings, or in the `.kicad_pro`, set the drawing sheet to `${KIPRJMOD}/../lib/opendap/drawing-sheets/opendap.kicad_wks` (the example, inside this repository, uses a path relative to itself).
2. In Project Settings → Text Variables, set `OPENDAP_PROJECT`, `OPENDAP_BOARD`, `OPENDAP_LICENCE` (`CERN-OHL-S-2.0` or `CERN-OHL-W-2.0`) and `OPENDAP_SOURCE`.
3. Copy the ERC severities and the field names of the example's `.kicad_pro` (CRAFT-158, §9.4).
4. For each feature block, copy `feature-block/feature-block.kicad_sch` to `<block>.kicad_sch` (the block ID without `blk.`), fill its title block and replace the placeholders.
5. To plot with the OpenDAP colours, copy `colour-themes/opendap.json` into KiCad's `colors` folder (on macOS `~/Library/Preferences/kicad/10.0/colors/`) and pass `--theme OpenDAP` to `kicad-cli sch export pdf`, or select it in Preferences → Colors.
6. Check with `odapkit craft check hardware/<project>/<project>.kicad_sch` (toolkit-hardware); its configuration is the `[schematic]` table of `<project>.craft.toml`, as in the example.

## Notes

- The drawing sheet uses KiCad's stroke font; why, and the proposal for IBM Plex, are in the standard (§9.1, §12).
- `kicad-cli sch upgrade` drops embedded fonts and files (KiCad 10.0.7); the generator uses it only on files that embed neither.
- The example's part numbers and data-sheet links are illustrative and were not checked against stock.
