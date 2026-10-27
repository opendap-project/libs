# Parts library requirements

| ID | Requirement | Priority | Status |
|---|---|---|---|
| PLIB-001 | Every part in an OpenDAP BOM shall have a spec sheet here and its external files (datasheet, models) listed in the manifest. | must | Confirmed |
| PLIB-002 | Manufacturer files shall not be committed unless their licence allows redistribution; they are fetched into the local cache and verified by sha256. | must | Confirmed |
| PLIB-003 | Every spec sheet shall record the part's lifecycle status as its manufacturer states it (active, NRND, last time buy, obsolete), with the source and the date it was read, and shall name its second sources (form-, fit- and function-compatible parts on the same land) where they exist. Stock, prices, distributors and quotes are not recorded in the parts library. | must | Confirmed |

## Context

- PLIB-003 (2026-10-25): reworded by the maintainers; it previously asked for distributor stock and price.
