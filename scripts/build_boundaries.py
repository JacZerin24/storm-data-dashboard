"""Build public boundary GeoJSON layers for the Storm Data Dashboard.

This script downloads public NWS AWIPS shapefiles and writes:

- docs/data/boundaries/all_cwas.geojson
- docs/data/boundaries/by_wfo/<WFO>/cwa.geojson
- docs/data/boundaries/by_wfo/<WFO>/counties_parishes.geojson
- docs/data/boundaries/by_wfo/<WFO>/land_zones.geojson
- docs/data/boundaries/by_wfo/<WFO>/marine_zones.geojson

PowerShell usage:
python .\scripts\build_boundaries.py
python .\scripts\build_boundaries.py --wfos ALL
python .\scripts\build_boundaries.py --wfos LIX,MOB,JAN,LCH
"""

from __future__ import annotations

import argparse
import json
import tempfile
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

import geopandas as gpd
import pandas as pd


DEFAULT_WFOS = "ALL"

SOURCES = {
    "cwa": "https://www.weather.gov/source/gis/Shapefiles/WSOM/w_16ap26.zip",
    "counties": "https://www.weather.gov/source/gis/Shapefiles/County/c_16ap26.zip",
    "land_zones": "https://www.weather.gov/source/gis/Shapefiles/WSOM/z_16ap26.zip",
    "marine_zones": "https://www.weather.gov/source/gis/Shapefiles/WSOM/mz16ap26.zip",
}

OUTPUTS = {
    "cwa": "cwa.geojson",
    "counties": "counties_parishes.geojson",
    "land_zones": "land_zones.geojson",
    "marine_zones": "marine_zones.geojson",
}

KEEP_FIELDS = {
    "cwa": ["WFO", "CWA", "NAME", "STATE", "ST", "CITYSTATE"],
    "counties": ["STATE", "CWA", "WFO", "NAME", "COUNTYNAME", "FIPS", "TIME_ZONE"],
    "land_zones": ["STATE", "ZONE", "CWA", "WFO", "NAME", "STATE_ZONE", "TIME_ZONE"],
    "marine_zones": ["ID", "WFO", "GL_WFO", "NAME"],
}

FILTER_COLUMNS = ["WFO", "CWA", "GL_WFO", "ID", "NAME", "CITYSTATE"]


def log(message: str) -> None:
    print(message, flush=True)


def download_file(url: str, output_path: Path) -> None:
    request = Request(
        url,
        headers={
            "User-Agent": "storm-data-dashboard-boundary-builder/0.1 (GitHub Pages prototype)",
            "Accept": "application/zip,application/octet-stream,*/*",
        },
    )
    with urlopen(request, timeout=90) as response:
        output_path.write_bytes(response.read())


def normalize_columns(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = gdf.copy()
    gdf.columns = [str(col).upper() if col != "geometry" else col for col in gdf.columns]
    return gdf


def read_source_layer(layer_key: str, source_url: str, tmpdir: Path) -> gpd.GeoDataFrame:
    zip_path = tmpdir / f"{layer_key}.zip"
    extract_dir = tmpdir / layer_key
    extract_dir.mkdir(parents=True, exist_ok=True)

    log(f"Downloading {layer_key}: {source_url}")
    download_file(source_url, zip_path)
    log(f"  Downloaded bytes: {zip_path.stat().st_size}")

    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)

    shp_files = sorted(extract_dir.rglob("*.shp"))
    if not shp_files:
        raise RuntimeError(f"No .shp file found inside {source_url}")

    shp_path = shp_files[0]
    log(f"Reading {layer_key}: {shp_path}")
    gdf = gpd.read_file(shp_path)
    gdf = normalize_columns(gdf)
    log(f"  Raw features: {len(gdf)}")
    log(f"  Columns: {', '.join(map(str, gdf.columns))}")
    return gdf


def discover_wfos(raw_cwa: gpd.GeoDataFrame) -> list[str]:
    for col in ["WFO", "CWA"]:
        if col in raw_cwa.columns:
            values = raw_cwa[col].dropna().astype(str).str.upper().str.strip()
            wfos = sorted(value for value in values.unique() if len(value) == 3 and value.isalpha())
            if wfos:
                log(f"Discovered {len(wfos)} WFOs from CWA field {col}.")
                return wfos

    raise RuntimeError("Could not auto-discover WFOs from the CWA shapefile.")


def resolve_wfos(value: str, raw_cwa: gpd.GeoDataFrame) -> list[str]:
    cleaned = value.strip().upper()
    if cleaned in {"ALL", "*", "AUTO"}:
        return discover_wfos(raw_cwa)
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def filter_by_wfo_columns(gdf: gpd.GeoDataFrame, wfo: str) -> gpd.GeoDataFrame:
    mask = pd.Series(False, index=gdf.index)
    used_columns = []

    for col in FILTER_COLUMNS:
        if col in gdf.columns:
            used_columns.append(col)
            mask = mask | gdf[col].astype(str).str.upper().str.contains(wfo, na=False)

    if used_columns:
        log(f"  WFO filter columns used: {', '.join(used_columns)}")
    else:
        log("  No WFO-like filter columns found; will use spatial fallback if available.")

    return gdf[mask].copy()


def filter_cwa(gdf: gpd.GeoDataFrame, wfo: str) -> gpd.GeoDataFrame:
    filtered = filter_by_wfo_columns(gdf, wfo)

    if filtered.empty:
        preview_cols = [col for col in FILTER_COLUMNS if col in gdf.columns]
        if preview_cols:
            log("  CWA filter preview:")
            log(str(gdf[preview_cols].head(10)))
        raise RuntimeError(f"Could not find {wfo} CWA feature in CWA shapefile.")

    return filtered


def spatial_filter_to_cwa(gdf: gpd.GeoDataFrame, cwa_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if gdf.empty or cwa_gdf.empty:
        return gdf.iloc[0:0].copy()

    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326", allow_override=True)
    if cwa_gdf.crs is None:
        cwa_gdf = cwa_gdf.set_crs("EPSG:4326", allow_override=True)

    gdf_4326 = gdf.to_crs("EPSG:4326")
    cwa_4326 = cwa_gdf.to_crs("EPSG:4326")

    try:
        cwa_geom = cwa_4326.geometry.union_all()
    except AttributeError:
        cwa_geom = cwa_4326.geometry.unary_union

    mask = gdf_4326.geometry.intersects(cwa_geom)
    return gdf_4326[mask].copy()


def filter_for_wfo(layer_key: str, gdf: gpd.GeoDataFrame, wfo: str, cwa_gdf: gpd.GeoDataFrame | None) -> gpd.GeoDataFrame:
    if layer_key == "cwa":
        return filter_cwa(gdf, wfo)

    filtered = filter_by_wfo_columns(gdf, wfo)

    if not filtered.empty:
        return filtered

    if cwa_gdf is not None and not cwa_gdf.empty:
        log(f"  No WFO-column matches found for {wfo}; using spatial intersection with {wfo} CWA.")
        return spatial_filter_to_cwa(gdf, cwa_gdf)

    return gdf.iloc[0:0].copy()


def clean_for_geojson(gdf: gpd.GeoDataFrame, layer_key: str, simplify_tolerance: float) -> gpd.GeoDataFrame:
    gdf = gdf.copy()

    if gdf.empty:
        return gdf

    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326", allow_override=True)
    else:
        gdf = gdf.to_crs("EPSG:4326")

    try:
        gdf["geometry"] = gdf.geometry.make_valid()
    except AttributeError:
        gdf["geometry"] = gdf.geometry.buffer(0)

    gdf = gdf[~gdf.geometry.is_empty & gdf.geometry.notna()].copy()

    if simplify_tolerance > 0 and not gdf.empty:
        gdf["geometry"] = gdf.geometry.simplify(simplify_tolerance, preserve_topology=True)

    keep = [field for field in KEEP_FIELDS[layer_key] if field in gdf.columns]
    gdf = gdf[keep + ["geometry"]].copy()

    for col in keep:
        gdf[col] = gdf[col].where(gdf[col].notna(), None)

    return gdf


def add_metadata(path: Path, metadata: dict) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["metadata"] = metadata
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def write_geojson(gdf: gpd.GeoDataFrame, output_path: Path, metadata: dict) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if gdf.empty:
        data = {
            "type": "FeatureCollection",
            "metadata": metadata | {"warning": "No features were found for this layer."},
            "features": [],
        }
        output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return

    gdf.to_file(output_path, driver="GeoJSON")
    add_metadata(output_path, metadata)


def build_all_cwas(raw_cwa: gpd.GeoDataFrame, output_dir: Path, simplify_tolerance: float) -> None:
    log("Building all CWA boundary layer")
    cwa = clean_for_geojson(raw_cwa, "cwa", simplify_tolerance)
    output_path = output_dir / "all_cwas.geojson"
    write_geojson(
        cwa,
        output_path,
        {
            "schema_version": "0.1.0",
            "layer": "all_cwas",
            "source": SOURCES["cwa"],
            "public_release_status": "public-source-derived",
        },
    )
    log(f"Wrote {output_path}")


def build_wfo_layer(
    layer_key: str,
    source_url: str,
    output_dir: Path,
    simplify_tolerance: float,
    raw_gdf: gpd.GeoDataFrame,
    wfo: str,
    cwa_gdf: gpd.GeoDataFrame | None,
) -> gpd.GeoDataFrame:
    output_path = output_dir / "by_wfo" / wfo / OUTPUTS[layer_key]

    gdf = filter_for_wfo(layer_key, raw_gdf, wfo, cwa_gdf)
    log(f"  {wfo} {layer_key} features: {len(gdf)}")

    gdf = clean_for_geojson(gdf, layer_key, simplify_tolerance)
    log(f"  {wfo} {layer_key} clean features: {len(gdf)}")

    if gdf.empty and layer_key == "cwa":
        raise RuntimeError(f"{wfo} CWA layer is empty after filtering; cannot build reliable WFO boundaries.")

    write_geojson(
        gdf,
        output_path,
        {
            "schema_version": "0.1.0",
            "wfo": wfo,
            "layer": layer_key,
            "source": source_url,
            "public_release_status": "public-source-derived",
        },
    )
    log(f"Wrote {output_path}")
    return gdf


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Storm Data Dashboard boundary GeoJSON files.")
    parser.add_argument(
        "--output-dir",
        default="docs/data/boundaries",
        help="Output directory for public boundary GeoJSON files.",
    )
    parser.add_argument(
        "--wfos",
        default=DEFAULT_WFOS,
        help="Comma-separated WFO list, or ALL to auto-discover all WFOs from the CWA shapefile.",
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

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)

        raw_layers: dict[str, gpd.GeoDataFrame] = {}
        for layer_key, source_url in SOURCES.items():
            raw_layers[layer_key] = read_source_layer(layer_key, source_url, tmpdir)

        wfos = resolve_wfos(args.wfos, raw_layers["cwa"])
        if not wfos:
            raise RuntimeError("At least one WFO must be provided or discovered.")

        log(f"Building WFO-specific boundary layers for {len(wfos)} WFOs: {', '.join(wfos)}")
        build_all_cwas(raw_layers["cwa"], output_dir, args.simplify_tolerance)

        for wfo in wfos:
            log(f"Building WFO-specific boundary layers for {wfo}")
            cwa_gdf = build_wfo_layer(
                "cwa",
                SOURCES["cwa"],
                output_dir,
                args.simplify_tolerance,
                raw_layers["cwa"],
                wfo,
                None,
            )

            for layer_key in ["counties", "land_zones", "marine_zones"]:
                build_wfo_layer(
                    layer_key,
                    SOURCES[layer_key],
                    output_dir,
                    args.simplify_tolerance,
                    raw_layers[layer_key],
                    wfo,
                    cwa_gdf,
                )

    log("Done.")


if __name__ == "__main__":
    main()
