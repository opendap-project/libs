# Parts library requirements

| ID | Requirement | Priority | Status |
|---|---|---|---|
| PLIB-001 | Every part in an OpenDAP BOM shall have its external files (datasheet, models) listed in the manifest, and, where the libraries draw it, generator data citing the datasheet page for every value (ADR 0002). | must | Confirmed |
| PLIB-002 | Manufacturer files shall not be committed unless their licence allows redistribution; they are fetched into the local cache and verified by sha256. | must | Confirmed |
| PLIB-003 | Every part in an OpenDAP BOM shall record its lifecycle status as its manufacturer states it (active, NRND, last time buy, obsolete), with the source and the date it was read, and shall name its second sources (form-, fit- and function-compatible parts on the same land) where they exist, as fields of its generator data (ADR 0002). Stock, prices, distributors and quotes are not recorded in the parts library. | must | Confirmed |

## Context

- PLIB-003 (2026-10-25): reworded by the maintainers; it previously asked for distributor stock and price.
- PLIB-001 and PLIB-003 (2026-10-27): spec sheets are no longer published (ADR 0002). PLIB-001 now asks for the manifest entries and the generator data; PLIB-003 keeps its facts, now as fields of the generator data, and a second source a design uses is also named in the symbol's `Second_Source` field.
- PLIB-003 (2026-10-29): the libraries carry no product content. The alternative a design chooses is a BOM choice: the design names it in the `Second_Source` field of its placed part, and the library symbol no longer carries one; the generator data keeps the part's own `second_sources`.
