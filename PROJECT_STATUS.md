# Project Status: Storm Data Dashboard

Last updated: 2026-05-27

## Current project goal

Build a static GitHub Pages dashboard where a user selects month, year, and WFO identifier, then views a Storm Data preparation package for that WFO/month.

The dashboard is intended to support the 60-day Storm Data preparation workflow by putting public candidate reports, relevant public NWS product links, warning/alert context, and map boundaries in one place. It is a preparation aid, not the final certified Storm Data record.

## Current phase

- [x] Phase 0: Repo scaffold
- [x] Phase 1: Define public JSON/GeoJSON schema
- [x] Phase 2: Build one-month/one-WFO sample data
- [x] Phase 3: Create basic static frontend
- [x] Phase 4: Add basic Leaflet map/table loading
- [x] Phase 5: Add all-CWA and WFO-specific boundary layers
- [x] Phase 6: Rename boundary builder to `scripts/build_boundaries.py`
- [x] Phase 7: Convert `scripts/build_month.py` into a public Storm Data prep builder
- [x] Phase 8: Add GitHub Actions workflow to build one Storm Data prep month
- [ ] Phase 9: Test workflow with real WFO/month cases and fix source-specific edge cases
- [ ] Phase 10: Add directive-aware event type grouping
- [ ] Phase 11: Add QA/verification helpers
- [ ] Phase 12: Expand hazards and evidence links

## Current status summary

The dashboard has a working static GitHub Pages scaffold. It loads all CWA boundaries and dynamically loads WFO-specific CWA, counties/parishes, land zones, and marine zones based on the WFO entered by the user.

The boundary builder has been renamed from `scripts/build_lix_boundaries.py` to `scripts/build_boundaries.py`. The old LIX-specific script name was removed.

`scripts/build_month.py` is now a Storm Data prep builder. It pulls public helper sources for one WFO/month/year and writes static files under `docs/data/stormprep/YYYY/MM/WFO/`:

```text
dashboard.json
reports.geojson
products.json
warnings.geojson
summary.json
```

A new GitHub Actions workflow, **Build Storm Data Prep Month**, can be run manually with year, month, and WFO inputs. It runs `scripts/build_month.py`, then commits the generated storm prep package into `docs/data/stormprep/`.

The frontend now loads Storm Data prep packages from `docs/data/stormprep/` instead of only the older sample `docs/data/stormdata/` output.

## Key decisions made

| Date | Decision | Reason |
|---|---|---|
| 2026-05-27 | Use `docs/` for GitHub Pages | Keeps public site files separate from scripts and local data workflows |
| 2026-05-27 | Keep raw/local data out of the public site | Reduces risk of publishing internal/private evidence |
| 2026-05-27 | Use Python to build JSON/GeoJSON | Static frontend can load simple public files |
| 2026-05-27 | Add Leaflet through CDN for initial prototype | Keeps the frontend simple and static |
| 2026-05-27 | Prebuild boundaries with GitHub Actions | Static GitHub Pages cannot create boundary files on demand |
| 2026-05-27 | Build all CWA boundaries and WFO-specific folders | Lets public users type a WFO and load matching counties/zones if files exist |
| 2026-05-27 | Use GitHub Actions to build Storm Data prep packages | Lets the dashboard pull public sources without manual local CSV downloads |
| 2026-05-27 | Keep prep data separate from final Storm Data archive data | Avoids confusing candidate/prep evidence with final certified Storm Events records |

## Open questions

| Question | Notes | Priority |
|---|---|---|
| Which additional public sources should be added first? | SPC storm reports, MRMS/rainfall links, public PNS/survey pages, WPC products, NHC tropical products. | High |
| How should WFO attribution be handled for sources that do not include WFO directly? | Current prep builder starts with WFO-filtered public sources and WFO boundaries. | High |
| What event types should be grouped together in the UI? | Needs directive-aware event type config. | Medium |
| What source links/metadata should be exposed publicly? | Avoid private/internal evidence. | High |

## Public data output plan

Storm Data prep package:

```text
docs/data/stormprep/YYYY/MM/WFO/dashboard.json
docs/data/stormprep/YYYY/MM/WFO/reports.geojson
docs/data/stormprep/YYYY/MM/WFO/products.json
docs/data/stormprep/YYYY/MM/WFO/warnings.geojson
docs/data/stormprep/YYYY/MM/WFO/summary.json
```

Boundary files:

```text
docs/data/boundaries/all_cwas.geojson
docs/data/boundaries/by_wfo/WFO/cwa.geojson
docs/data/boundaries/by_wfo/WFO/counties_parishes.geojson
docs/data/boundaries/by_wfo/WFO/land_zones.geojson
docs/data/boundaries/by_wfo/WFO/marine_zones.geojson
```

Older/sample official Storm Data-style files may still exist under:

```text
docs/data/stormdata/YYYY/MM/WFO/
```

but the active dashboard now expects the storm prep package under `docs/data/stormprep/`.

## Frontend status

Implemented:

- Header/title
- Month selector
- Year selector
- WFO selector
- Load button
- Summary panel
- Candidate report table
- Public product link groups
- Leaflet map
- Candidate report plotting from `reports.geojson`
- NWS API alert/warning polygon layer from `warnings.geojson` when available
- All CWA boundary layer
- WFO-specific CWA layer
- WFO-specific counties/parishes layer
- WFO-specific land zones layer
- WFO-specific marine zones layer

Not yet implemented:

- Directive-aware hazard grouping from config
- Event type filters
- Search
- Detailed event panel
- Dedicated final/certified Storm Data comparison mode
- Images/evidence panel
- QA flags
- Scheduled recurring build workflow

## Scripts and workflows

| Item | Purpose | Status |
|---|---|---|
| `scripts/build_month.py` | Build one WFO/month Storm Data prep package from public web sources | First GitHub Actions version added, needs testing |
| `scripts/build_boundaries.py` | Build all CWA boundaries and WFO-specific boundary folders | Working prototype |
| `.github/workflows/build-stormprep-month.yml` | Manual GitHub Action to build one year/month/WFO prep package | Added |
| `.github/workflows/build-lix-boundaries.yml` | Manual GitHub Action to build boundary GeoJSON | Still named historically, but calls `build_boundaries.py` |
| `scripts/build_index.py` | Build dashboard index files | Placeholder only |
| `scripts/validate_output.py` | Validate public output files | Placeholder only |

## Known risks

- Accidentally publishing private/internal evidence files.
- Public sources may be incomplete or delayed.
- IEM LSR archive is a useful helper source but should not be treated as the final official Storm Data record by itself.
- NWS API alert history is limited for older months, so `warnings.geojson` may be empty for older cases.
- Storm Data event type naming and NWSI grouping still need directive-aware logic.
- Some event types may not map cleanly to points or tracks.
- Public imagery licensing must be tracked before display.
- Large all-WFO boundary output may need optimization or simplification later.

## Next recommended step

Run the new manual GitHub Action:

```text
Actions → Build Storm Data Prep Month → Run workflow
```

Use a test case such as:

```text
Year: 2026
Month: 5
WFO: LIX
```

After the workflow finishes, confirm these files exist:

```text
docs/data/stormprep/2026/05/LIX/dashboard.json
docs/data/stormprep/2026/05/LIX/reports.geojson
docs/data/stormprep/2026/05/LIX/products.json
docs/data/stormprep/2026/05/LIX/warnings.geojson
docs/data/stormprep/2026/05/LIX/summary.json
```

Then hard refresh the GitHub Pages dashboard and load the same year/month/WFO.

## Chat handoff notes

### What was completed

- Starter repo scaffold created.
- Static dashboard loads data from GitHub Pages.
- Leaflet map added.
- All CWA and WFO-specific boundary layer support added.
- Boundary builder renamed to `scripts/build_boundaries.py`.
- Manual Storm Data prep GitHub Action added.
- `scripts/build_month.py` now pulls public LSR/NWS helper sources and writes a storm prep package.
- Frontend now loads storm prep package files from `docs/data/stormprep/`.

### What files changed

- `docs/index.html`
- `docs/assets/js/app.js`
- `docs/assets/css/styles.css`
- `docs/data/index.json`
- `docs/data/boundaries/`
- `.github/workflows/build-lix-boundaries.yml`
- `.github/workflows/build-stormprep-month.yml`
- `scripts/build_boundaries.py`
- `scripts/build_month.py`
- `PROJECT_STATUS.md`

### What needs to happen next

- Test **Build Storm Data Prep Month** with LIX and at least one other WFO.
- Fix any source-specific errors from the first workflow run.
- Add more public evidence/source links.
- Add directive-aware categorization and filters.

### Problems/errors encountered

- GitHub Pages may show cached JavaScript briefly after updates. Use hard refresh if needed.
- Boundary workflow initially failed due to shapefile source URL issues and was patched.
- NWS API alert history may be empty for older months; this is expected and should be documented in the dashboard.
