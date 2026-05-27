# Public Boundary GeoJSON

This folder is for public dashboard boundary layers.

Expected LIX prototype outputs:

```text
LIX/cwa.geojson
LIX/counties_parishes.geojson
LIX/land_zones.geojson
LIX/marine_zones.geojson
```

These files should be generated from public NWS AWIPS shapefiles using:

```powershell
python .\scripts\build_lix_boundaries.py
```

or the manual GitHub Actions workflow named **Build LIX boundary GeoJSON**.

The dashboard is already wired to load these files when they exist. The CWA boundary is always shown. Counties/parishes, land zones, and marine zones are available as clickable toggle layers in the Leaflet layer control.
