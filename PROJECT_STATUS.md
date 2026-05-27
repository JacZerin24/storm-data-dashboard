# Project Status: Storm Data Dashboard

Last updated: 2026-05-27

## Current project goal

Build a static GitHub Pages dashboard where a user selects month, year, and WFO identifier, then views official Storm Data entries for that WFO/month.

The project should eventually support tornadoes, thunderstorm wind, hail, flood/flash flood, drought, heat/cold, tropical/coastal, winter, marine, and other Storm Data event types permitted by the applicable NWS directive.

## Current phase

- [x] Phase 0: Repo scaffold
- [ ] Phase 1: Define public JSON/GeoJSON schema
- [ ] Phase 2: Build one-month/one-WFO sample data
- [ ] Phase 3: Create basic static frontend
- [ ] Phase 4: Add map/table/filtering
- [ ] Phase 5: Add QA/verification helpers
- [ ] Phase 6: Add additional hazards and edge cases
- [ ] Phase 7: Publish on GitHub Pages

## Current status summary

Initial GitHub repository scaffold is being created. No real Storm Data ingest has been implemented yet.

## Key decisions made

| Date | Decision | Reason |
|---|---|---|
| 2026-05-27 | Use `docs/` for GitHub Pages | Keeps public site files separate from scripts and local data workflows |
| 2026-05-27 | Keep raw/local data out of the public site | Reduces risk of publishing internal/private evidence |
| 2026-05-27 | Use Python to build JSON/GeoJSON | Static frontend can load simple public files |

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
