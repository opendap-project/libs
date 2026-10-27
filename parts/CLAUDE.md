# Parts Library

Tool-independent data for every part OpenDAP designs with: spec sheets and the manifest of external part files.

Part of [OpenDAP](https://github.com/opendap-project). This repository is open source.

## Working here

- Write everything in English.
- Spec sheets transcribe datasheets: cite the datasheet revision and page for every value; never guess a value.
- Never commit manufacturer files (PDF, STEP, IBIS, SPICE, Touchstone) unless their licence allows it; list them in `manifest.toml` with URL, revision, date and sha256, and fetch them with `toolkit/hardware/tools/parts-sync.py`.
- Licensing follows REUSE (`REUSE.toml`, `LICENSES/`). After adding files or folders, run the `/opendap:license-check` skill.
