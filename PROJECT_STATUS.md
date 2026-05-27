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
- [ ] Phase 5: Add real Storm Data ingest script
- [ ] Phase 6: Add directive-aware event type grouping
- [ ] Phase 7: Add QA/verification helpers
- [ ] Phase 8: Expand hazards and edge cases
- [ ] Phase 9: Publish/refine GitHub Pages workflow

## Current status summary

The dashboard has a working static GitHub Pages scaffold. It can load a sample LIX May 2024 `events.json` file, display the event in a table, and plot the matching `events.geojson` feature on a Leaflet map.

No real Storm Data ingest has been implemented yet. The next recommended step is to create a first real `build_month.py` workflow that converts one public Storm Data source file into `events.json`, `events.geojson`, and `summary.json`.

## Key decisions made

| Date | Decision | Reason |
|---|---|---|
| 2026-05-27 | Use `docs/` for GitHub Pages | Keeps public site files separate from scripts and local data workflows |
| 2026-05-27 | Keep raw/local data out of the public site | Reduces risk of publishing internal/private evidence |
| 2026-05-27 | Use Python to build JSON/GeoJSON | Static frontend can load simple public files |
| 2026-05-27 | Add Leaflet through CDN for initial prototype | Keeps the frontend simple and static |

## Open questions

| Question | Notes | Priority |
|---|---|---|
| What official Storm Data source format will be used first? | CSV, NCEI export, bulk download, or sample file? | High |
| How should WFO attribution be handled? | WFO column, county/zone mapping, CWA geometry, or another method? | High |
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

Not yet implemented:

- Real Storm Data ingest
- Event type filters
- Search
- Detailed event panel
- Directive-aware hazard grouping
- Images/evidence panel
- QA flags

## Scripts planned

| Script | Purpose | Status |
|---|---|---|
| `scripts/build_month.py` | Build one WFO/month into public JSON/GeoJSON | Placeholder only |
| `scripts/build_index.py` | Build dashboard index files | Placeholder only |
| `scripts/validate_output.py` | Validate public output files | Placeholder only |

## Known risks

- Accidentally publishing private/internal evidence files.
- Storm Data event type naming inconsistencies.
- WFO attribution may be non-trivial.
- Some event types may not map cleanly to points or tracks.
- Public imagery licensing must be tracked before display.

## Next recommended step

Create the first real `build_month.py` workflow using one public Storm Data input source and one test case.

Recommended first target:

```text
WFO: LIX
Month: May
Year: 2024
Hazards: thunderstorm wind, hail, tornado if present
```

## Chat handoff notes

### What was completed

- Starter repo scaffold created.
- Sample JSON/GeoJSON/summary files added for LIX May 2024.
- Static dashboard loads sample JSON and displays an event table.
- Leaflet added and sample GeoJSON point plotting implemented.

### What files changed

- `docs/index.html`
- `docs/assets/js/app.js`
- `docs/assets/css/styles.css`
- `docs/data/index.json`
- `docs/data/stormdata/2024/05/LIX/events.json`
- `docs/data/stormdata/2024/05/LIX/events.geojson`
- `docs/data/stormdata/2024/05/LIX/summary.json`
- `PROJECT_STATUS.md`

### What decisions were made

- Keep public dashboard output under `docs/data/`.
- Keep internal/private data out of GitHub Pages.
- Use Leaflet for the map prototype.

### What needs to happen next

- Build the first real Storm Data conversion script.
- Decide the first official/public Storm Data source format.
- Add validation checks for required fields.

### Problems/errors encountered

- GitHub Pages may show cached JavaScript briefly after updates. Use hard refresh if needed.
