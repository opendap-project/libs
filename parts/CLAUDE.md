# Parts Library

The manifest of external part files (datasheets, manufacturer models) for every part OpenDAP designs with.

## Working here

- Write everything in English.
- Never commit manufacturer files (PDF, STEP, IBIS, SPICE, Touchstone) unless their licence allows it; list them in `manifest.toml` with URL, revision, date and sha256, and fetch them with `toolkit/hardware/tools/parts-sync.py`.
- No spec sheets or datasheet transcriptions here ([ADR 0002](docs/adr/0002-public-form-of-a-part.md)): a part's values go into its KiCad generator data, each citing the datasheet page.
- Licensing follows REUSE (`REUSE.toml`, `LICENSES/`). After adding files or folders, run the `/opendap:license-check` skill.
