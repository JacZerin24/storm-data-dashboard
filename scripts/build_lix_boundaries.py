"""Build public LIX boundary GeoJSON layers for the Storm Data Dashboard.

This script downloads public NWS AWIPS shapefiles and writes simplified GeoJSON
files under docs/data/boundaries/LIX/.

The frontend expects:
- docs/data/boundaries/LIX/cwa.geojson
- docs/data/boundaries/LIX/counties_parishes.geojson
- docs/data/boundaries/LIX/land_zones.geojson
- docs/data/boundaries/LIX/marine_zones.geojson

PowerShell usage:
python .\scripts\build_lix_boundaries.py
"""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from urllib.request import urlretrieve

import geopandas as gpd


WFO = "LIX"

# Public NWS AWIPS shapefiles. These versioned shapefiles match the common
# AWIPS GIS filenames used operationally, but this can be updated later if NWS
# publishes newer versions.
SOURCES = {
    "cwa": "https://www.weather.gov/source/gis/Shapefiles/WSOM/w_16ap26.zip",
    "counties": "https://www.weather.gov/source/gis/Shapefiles/WSOM/c_16ap26.zip",
    "land_zones": "https://www.weather.gov/source/gis/Shapefiles/WSOM/z_16ap26.zip",
    "marine_zones": "https://www.weather.gov/source/gis/Shapefiles/WSOM/mz_16ap26.zip",
}


OUTPUTS = {
    "cwa": "cwa.geojson",
    "counties": "counties_parishes.geojson",
    "land_zones": "land_zones.geojson",
    "marine_zones": "marine_zones.geojson",
}


KEEP_FIELDS = {
    "cwa": ["WFO", "CWA", "NAME", "STATE"],
    "counties": ["STATE", "CWA", "WFO", "NAME", "COUNTYNAME", "FIPS", "TIME_ZONE"],
    "land_zones": ["STATE", "ZONE", "CWA", "WFO", "NAME", "STATE_ZONE", "TIME_ZONE"],
    "marine_zones": ["STATE", "ZONE", "CWA", "WFO", "NAME", "ID"],
}


def normalize_columns(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = gdf.copy()
    gdf.columns = [str(col).upper() if col != "geometry" else col for col in gdf.columns]
    return gdf


def filter_for_lix(gdf: gpd.GeoDataFrame, layer_key: str) -> gpd.GeoDataFrame:
    gdf = normalize_columns(gdf)

    if layer_key == "cwa":
        mask = False
        for col in ["WFO", "CWA"]:
            if col in gdf.columns:
                mask = mask | (gdf[col].astype(str).str.upper() == WFO)
        return gdf[mask].copy()

    mask = False
    for col in ["WFO", "CWA"]:
        if col in gdf.columns:
            mask = mask | gdf[col].astype(str).str.upper().str.contains(WFO, na=False)

    return gdf[mask].copy()


def clean_for_geojson(gdf: gpd.GeoDataFrame, layer_key: str, simplify_tolerance: float) -> gpd.GeoDataFrame:
    gdf = gdf.copy()

    if gdf.empty:
        return gdf

    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326", allow_override=True)
    else:
        gdf = gdf.to_crs("EPSG:4326")

    # Repair invalid geometries where possible.
    gdf["geometry"] = gdf.geometry.make_valid()
    gdf = gdf[~gdf.geometry.is_empty & gdf.geometry.notna()].copy()

    if simplify_tolerance > 0:
        gdf["geometry"] = gdf.geometry.simplify(simplify_tolerance, preserve_topology=True)

    keep = [field for field in KEEP_FIELDS[layer_key] if field in gdf.columns]
    gdf = gdf[keep + ["geometry"]].copy()

    # Make JSON friendlier by replacing NaNs with None.
    for col in keep:
        gdf[col] = gdf[col].where(gdf[col].notna(), None)

    return gdf


def add_metadata(path: Path, layer_key: str, source_url: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["metadata"] = {
        "schema_version": "0.1.0",
        "wfo": WFO,
        "layer": layer_key,
        "source": source_url,
        "public_release_status": "public-source-derived",
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def build_layer(layer_key: str, source_url: str, output_dir: Path, simplify_tolerance: float) -> Path:
    output_path = output_dir / OUTPUTS[layer_key]

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / f"{layer_key}.zip"
        print(f"Downloading {layer_key}: {source_url}")
        urlretrieve(source_url, zip_path)

        print(f"Reading {layer_key}")
        gdf = gpd.read_file(f"zip://{zip_path}")
        print(f"  Raw features: {len(gdf)}")

        gdf = filter_for_lix(gdf, layer_key)
        print(f"  LIX features: {len(gdf)}")

        gdf = clean_for_geojson(gdf, layer_key, simplify_tolerance)
        print(f"  Clean features: {len(gdf)}")

        if gdf.empty:
            raise RuntimeError(f"No features found for {layer_key}. Check source schema/filter logic.")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        gdf.to_file(output_path, driver="GeoJSON")
        add_metadata(output_path, layer_key, source_url)

    print(f"Wrote {output_path}")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build LIX boundary GeoJSON files.")
    parser.add_argument(
        "--output-dir",
        default="docs/data/boundaries/LIX",
        help="Output directory for public boundary GeoJSON files.",
    )
    parser.add_argument(
        "--simplify-tolerance",
        type=float,
        default=0.001,
        help="Geometry simplification tolerance in degrees. Use 0 for no simplification.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)

    for layer_key, source_url in SOURCES.items():
        build_layer(layer_key, source_url, output_dir, args.simplify_tolerance)

    print("Done.")


if __name__ == "__main__":
    main()
