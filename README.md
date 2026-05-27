# Storm Data Dashboard

A static GitHub Pages dashboard for viewing official Storm Data entries by month, year, and WFO identifier.

The long-term goal is to let a user select:

- Month
- Year
- WFO identifier

and then view official Storm Data entries for that WFO/month, including tornadoes, thunderstorm wind, hail, flood/flash flood, drought, heat/cold, tropical/coastal, winter, marine, and other event types permitted by the applicable NWS Storm Data directive.

This project is intentionally static-first:

- Python scripts build JSON and GeoJSON files.
- The frontend is plain HTML, CSS, and JavaScript.
- Leaflet will likely be used for maps.
- The dashboard can be hosted on GitHub Pages.
- Public output files should avoid internal/private evidence unless explicitly cleared.

## Project status

See [`PROJECT_STATUS.md`](PROJECT_STATUS.md) for current progress, decisions, open questions, and next steps.

## Repository layout

```text
docs/              Static GitHub Pages site
docs/data/         Public JSON/GeoJSON output used by the dashboard
scripts/           PowerShell-friendly Python command-line scripts
src/stormdash/     Reusable Python package code
config/            Editable project configuration files
data/              Local/private source and working data
tests/             Basic tests
