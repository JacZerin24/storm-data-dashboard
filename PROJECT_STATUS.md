# Project Status: Storm Data Dashboard

Last updated: 2026-05-27

## Current project goal

Build a static GitHub Pages dashboard where a user selects month, year, and WFO identifier, then views official Storm Data entries for that WFO/month.

The project should eventually support tornadoes, thunderstorm wind, hail, flood/flash flood, drought, heat/cold, tropical/coastal, winter, marine, and other Storm Data event types permitted by the applicable NWS directive.

## Current phase

- [x] Phase 0: Repo scaffold
- [x] Phase 1: Define public JSON/GeoJSON schema
- [x] Phase 2: Build one-month/one-WFO sample data
- [x] Phase 3: Create basic static frontend
- [x] Phase 4: Add basic Leaflet map/table loading
- [x] Phase 5: Add all-CWA and WFO-specific boundary layers
- [x] Phase 6: Add first real Storm Data CSV ingest script
- [ ] Phase 7: Test real ingest with one downloaded Storm Events CSV
- [ ] Phase 8: Add directive-aware event type grouping
- [ ] Phase 9: Add QA/verification helpers
- [ ] Phase 10: Expand hazards and edge cases
- [ ] Phase 11: Publish/refine GitHub Pages workflow

## Current status summary

The dashboard has a working static GitHub Pages scaffold. It can load a sample LIX May 2024 `events.json` file, display the event in a table, and plot the matching `events.geojson` feature on a Leaflet map.

The map now loads all CWA boundaries and dynamically loads WFO-specific CWA, counties/parishes, land zones, and marine zones based on the WFO entered by the user.

The boundary builder has been renamed from `scripts/build_lix_boundaries.py` to `scripts/build_boundaries.py`. The old LIX-specific script name was removed.

A first real `scripts/build_month.py` ingest script now exists. It reads one downloaded public Storm Events CSV, filters one WFO/year/month, and writes dashboard-ready `events.json`, `events.geojson`, and `summary.json` files under `docs/data/stormdata/`.

The next recommended step is to download one public Storm Events CSV and test `build_month.py` for a known WFO/month.

## Key decisions made

| Date | Decision | Reason |
|---|---|---|
| 2026-05-27 | Use `docs/` for GitHub Pages | Keeps public site files separate from scripts and local data workflows |
| 2026-05-27 | Keep raw/local data out of the public site | Reduces risk of publishing internal/private evidence |
| 2026-05-27 | Use Python to build JSON/GeoJSON | Static frontend can load simple public files |
| 2026-05-27 | Add Leaflet through CDN for initial prototype | Keeps the frontend simple and static |
| 2026-05-27 | Prebuild boundaries with GitHub Actions | Static GitHub Pages cannot create boundary files on demand |
| 2026-05-27 | Build all CWA boundaries and WFO-specific folders | Lets public users type a WFO and load matching counties/zones if files exist |
| 2026-05-27 | Start real ingest from a local downloaded public Storm Events CSV | Keeps the first ingest test simple before adding automated downloading |

## Open questions

| Question | Notes | Priority |
|---|---|---|
| What exact Storm Events CSV download source should be standardized first? | Manual NCEI CSV download or NOAA bulk CSV URL. | High |
| How should WFO attribution be handled when older records are missing or inconsistent? | Current first pass requires a `WFO` column. | High |
| What event types should be grouped together in the UI? | Needs directive-aware event type config. | Medium |
| What source links/metadata should be exposed publicly? | Avoid private/internal evidence. | High |

## Public data output plan

Planned public files under `docs/data/`:

```text
docs/data/index.json
docs/data/wfos.json
docs/data/stormdata/YYYY/MM/WFO/events.json
docs/data/stormdata/YYYY/MM/WFO/events.geojson
docs/data/stormdata/YYYY/MM/WFO/summary.json
```

Boundary files:

```text
docs/data/boundaries/all_cwas.geojson
docs/data/boundaries/by_wfo/WFO/cwa.geojson
docs/data/boundaries/by_wfo/WFO/counties_parishes.geojson
docs/data/boundaries/by_wfo/WFO/land_zones.geojson
docs/data/boundaries/by_wfo/WFO/marine_zones.geojson
```

## Current sample dataset

```text
WFO: LIX
Year: 2024
Month: 05
Files:
- docs/data/stormdata/2024/05/LIX/events.json
- docs/data/stormdata/2024/05/LIX/events.geojson
- docs/data/stormdata/2024/05/LIX/summary.json
```

## Frontend status

Implemented:

- Header/title
- Month selector
- Year selector
- WFO selector
- Load button
- Summary panel
- Event table
- Leaflet map
- Sample GeoJSON plotting
- All CWA boundary layer
- WFO-specific CWA layer
- WFO-specific counties/parishes layer
- WFO-specific land zones layer
- WFO-specific marine zones layer

Not yet implemented:

- Real Storm Data ingest test with an actual CSV
- Event type filters
- Search
- Detailed event panel
- Directive-aware hazard grouping from config
- Images/evidence panel
- QA flags

## Scripts

| Script | Purpose | Status |
|---|---|---|
| `scripts/build_month.py` | Build one WFO/month into public JSON/GeoJSON from one downloaded Storm Events CSV | First real version added, needs testing |
| `scripts/build_boundaries.py` | Build all CWA boundaries and WFO-specific boundary folders | Working prototype |
| `scripts/build_index.py` | Build dashboard index files | Placeholder only |
| `scripts/validate_output.py` | Validate public output files | Placeholder only |

## Known risks

- Accidentally publishing private/internal evidence files.
- Storm Data event type naming inconsistencies.
- WFO attribution may be non-trivial for older or inconsistent records.
- Some event types may not map cleanly to points or tracks.
- Public imagery licensing must be tracked before display.
- Large all-WFO boundary output may need optimization or simplification later.

## Next recommended step

Download one public Storm Events CSV and test:

```powershell
python .\scripts\build_month.py `
  --csv .\data\raw\storm_events_2024.csv `
  --year 2024 `
  --month 5 `
  --wfo LIX
```

Then confirm these files are created or updated:

```text
docs/data/stormdata/2024/05/LIX/events.json
docs/data/stormdata/2024/05/LIX/events.geojson
docs/data/stormdata/2024/05/LIX/summary.json
docs/data/index.json
```

## Chat handoff notes

### What was completed

- Starter repo scaffold created.
- Sample JSON/GeoJSON/summary files added for LIX May 2024.
- Static dashboard loads sample JSON and displays an event table.
- Leaflet added and sample GeoJSON point plotting implemented.
- All CWA and WFO-specific boundary layer support added.
- Boundary builder renamed to `scripts/build_boundaries.py`.
- First real `scripts/build_month.py` CSV ingest script added.

### What files changed

- `docs/index.html`
- `docs/assets/js/app.js`
- `docs/assets/css/styles.css`
- `docs/data/index.json`
- `docs/data/stormdata/2024/05/LIX/events.json`
- `docs/data/stormdata/2024/05/LIX/events.geojson`
- `docs/data/stormdata/2024/05/LIX/summary.json`
- `docs/data/boundaries/`
- `.github/workflows/build-lix-boundaries.yml`
- `scripts/build_boundaries.py`
- `scripts/build_month.py`
- `PROJECT_STATUS.md`

### What decisions were made

- Keep public dashboard output under `docs/data/`.
- Keep internal/private data out of GitHub Pages.
- Use Leaflet for the map prototype.
- Prebuild boundary files instead of attempting browser-side shapefile processing.
- Start real Storm Data ingest from one manually downloaded public CSV before automating downloads.

### What needs to happen next

- Test `scripts/build_month.py` with one real downloaded Storm Events CSV.
- Confirm actual CSV column compatibility.
- Add validation checks for required fields.
- Improve event category mapping using `config/event_types.yml`.

### Problems/errors encountered

- GitHub Pages may show cached JavaScript briefly after updates. Use hard refresh if needed.
- Boundary workflow initially failed due to shapefile source URL issues and was patched.
- Workflow now builds all CWA/WFO-specific boundary files successfully.
