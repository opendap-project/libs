# Spec sheet template

Every spec sheet `<manufacturer>/<MPN>.md` follows this structure. Content is transcribed from the datasheet; every value cites the document and page. A value without a primary source is marked **UNVERIFIED**.

## File name and title

- File name: the MPN, with characters that cannot appear in a file name replaced by a hyphen (`+T` becomes `-T`, `/` becomes `-`).
- Title: `# <MPN>`, the exact MPN with its original punctuation.

## Metadata

A list right under the title, in this order:

- **Manufacturer:** the manufacturer's name.
- **Function:** what the part is, in one line.
- **BOM v1 lines:** each board BOM v1 line that uses the part, with what the line uses it for and the quantity when known.
- **Package:** package name, size and pitch.
- **Datasheet:** document, revision and date; the sha256 only when the sheet states it. Further documents go in nested bullets. Local file locations are never written here: they belong to `manifest.toml` and the local cache.
- **Lifecycle (date, source):** the lifecycle status as the manufacturer states it (active, NRND, last time buy, obsolete), with the document or page it was read from and the date; or "Not stated" (PLIB-003).
- **Second sources:** form-, fit- and function-compatible parts on the same land, by MPN; or "None found". Stock, prices, distributors and quotes are not recorded here (PLIB-003).
- **Status:** one of:
  - "Transcribed from the datasheet";
  - "Partly UNVERIFIED";
  - "Datasheet not downloaded: every field UNVERIFIED", followed by the reason.

## Sections

In this order, with these exact headings. A section that does not apply says "Not applicable." Content that fits no section goes into the closest one under a `###` sub-heading.

1. `## Summary`
2. `## Absolute maximum ratings`
3. `## Recommended operating conditions`
4. `## Power by mode`
5. `## Pinout and package`
6. `## Recommended footprint`
7. `## Application circuit and required passives`
8. `## Interfaces and timing`
9. `## Linux driver`
10. `## Simulation models`
11. `## Design notes for the T1`
12. `## Sources`
