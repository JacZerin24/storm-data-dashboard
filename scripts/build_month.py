"""Build one Storm Data prep month from public web sources.

This script pulls public helper sources for one WFO/month/year and writes a
static Storm Data prep package for GitHub Pages:

- docs/data/stormprep/YYYY/MM/WFO/dashboard.json
- docs/data/stormprep/YYYY/MM/WFO/reports.geojson
- docs/data/stormprep/YYYY/MM/WFO/products.json
- docs/data/stormprep/YYYY/MM/WFO/warnings.geojson
- docs/data/stormprep/YYYY/MM/WFO/tornado_tracks.geojson
- docs/data/stormprep/YYYY/MM/WFO/summary.json

PowerShell example:
python .\scripts\build_month.py --year 2026 --month 5 --wfo LIX

DAT tornado tracks:
python .\scripts\build_month.py --year 2026 --month 5 --wfo LIX --dat-tracks-url "https://..."

Important: these files are a preparation aid, not the final certified Storm
Data record.
"""

from __future__ import annotations

import argparse
import io
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import pandas as pd
import requests


SCHEMA_VERSION = "0.2.4"
USER_AGENT = "storm-data-dashboard/0.2 (GitHub Pages storm prep prototype)"

IEM_LSR_ENDPOINT = "https://mesonet.agron.iastate.edu/cgi-bin/request/gis/lsr.py"
IEM_AFOS_LIST_URL = "https://mesonet.agron.iastate.edu/wx/afos/list.phtml"
NWS_API_BASE = "https://api.weather.gov"
DAT_VIEWER_URL = "https://apps.dat.noaa.gov/stormdamage/damageviewer/"

PRODUCT_GROUPS = [
    {"group": "Local storm reports and public statements", "pils": ["LSR", "PNS"], "purpose": "Candidate reports, survey statements, public information statements, and local documentation."},
    {"group": "Convective warnings and statements", "pils": ["TOR", "SVR", "SVS", "SPS", "WCN"], "purpose": "Warning context, follow-up statements, special weather statements, and watch county notifications."},
    {"group": "Flood and hydro products", "pils": ["FFW", "FFS", "FLS", "FLW", "RVS", "ESF"], "purpose": "Flash flood, flood, river, and hydrologic context."},
    {"group": "Marine and coastal products", "pils": ["SMW", "MWS", "MWW", "CFW", "CWF", "HLS"], "purpose": "Marine warnings/statements, coastal hazards, and tropical local statements."},
    {"group": "Non-convective, winter, heat/cold, and fire products", "pils": ["NPW", "WSW", "RFW", "DGT", "HWO", "AFD"], "purpose": "Non-convective wind, winter, fire weather, drought, hazardous weather outlooks, and forecast discussion context."},
]

EVENT_CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("tornado", ["TORNADO", "WATERSPOUT", "WATER SPOUT", "FUNNEL"]),
    ("hail", ["HAIL"]),
    ("thunderstorm_wind", ["TSTM WND", "THUNDERSTORM WIND", "WIND GST", "WIND DMG", "DOWNBURST"]),
    ("flooding", ["FLASH FLOOD", "FLOOD", "HEAVY RAIN", "STORM SURGE", "COASTAL FLOOD"]),
    ("heat_cold", ["HEAT", "COLD", "FREEZE", "WIND CHILL"]),
    ("winter", ["SNOW", "SLEET", "ICE", "BLIZZARD", "WINTER"]),
    ("marine", ["MARINE", "SEICHE", "SURF", "RIP CURRENT"]),
    ("fire_smoke", ["WILDFIRE", "DENSE SMOKE"]),
    ("other", []),
]

STANDARD_TIME_OVERRIDES: dict[str, tuple[int, str]] = {
    "LIX": (-6, "CST"), "MOB": (-6, "CST"), "JAN": (-6, "CST"), "LCH": (-6, "CST"), "SHV": (-6, "CST"),
    "HGX": (-6, "CST"), "FWD": (-6, "CST"), "EWX": (-6, "CST"), "CRP": (-6, "CST"), "BRO": (-6, "CST"),
    "MFL": (-5, "EST"), "MLB": (-5, "EST"), "JAX": (-5, "EST"), "TAE": (-5, "EST"), "TBW": (-5, "EST"), "KEY": (-5, "EST"),
    "CHS": (-5, "EST"), "ILM": (-5, "EST"), "MHX": (-5, "EST"), "RAH": (-5, "EST"),
    "OUN": (-6, "CST"), "TSA": (-6, "CST"), "SGF": (-6, "CST"), "LSX": (-6, "CST"), "EAX": (-6, "CST"), "ICT": (-6, "CST"), "TOP": (-6, "CST"),
    "ABQ": (-7, "MST"), "EPZ": (-7, "MST"), "FGZ": (-7, "MST"), "PSR": (-7, "MST"), "TWC": (-7, "MST"), "SLC": (-7, "MST"), "BOU": (-7, "MST"), "PUB": (-7, "MST"), "CYS": (-7, "MST"), "RIW": (-7, "MST"),
    "LOX": (-8, "PST"), "SGX": (-8, "PST"), "MTR": (-8, "PST"), "STO": (-8, "PST"), "HNX": (-8, "PST"), "EKA": (-8, "PST"), "MFR": (-8, "PST"), "PQR": (-8, "PST"), "SEW": (-8, "PST"), "OTX": (-8, "PST"),
    "AFG": (-9, "AKST"), "AJK": (-9, "AKST"), "AFC": (-9, "AKST"), "HFO": (-10, "HST"), "SJU": (-4, "AST"), "GUM": (10, "ChST"), "PPG": (-11, "SST"),
}


def log(message: str) -> None:
    print(message, flush=True)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def month_window(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1, 0, 0, tzinfo=timezone.utc)
    end = datetime(year + 1, 1, 1, 0, 0, tzinfo=timezone.utc) if month == 12 else datetime(year, month + 1, 1, 0, 0, tzinfo=timezone.utc)
    return start, end


def iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    text = str(value).strip()
    if text == "" or text.lower() == "nan":
        return None
    return text


def to_float(value: Any) -> float | None:
    text = clean_text(value)
    if text is None:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def event_category(report_type: Any) -> str:
    text = clean_text(report_type)
    if not text:
        return "other"
    upper = text.upper()
    for category, needles in EVENT_CATEGORY_RULES:
        if category != "other" and any(needle in upper for needle in needles):
            return category
    return "other"


def fetch_text(url: str, timeout: int = 60) -> str:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    response.raise_for_status()
    return response.text


def fetch_json(url: str, timeout: int = 60) -> dict[str, Any]:
    response = requests.get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json, application/json"}, timeout=timeout)
    response.raise_for_status()
    return response.json()


def prepared_url(base: str, params: dict[str, Any]) -> str:
    return base + "?" + urlencode(params)


def parse_iem_valid(value: str | None) -> datetime | None:
    text = clean_text(value)
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    try:
        if len(digits) >= 12:
            return datetime(int(digits[0:4]), int(digits[4:6]), int(digits[6:8]), int(digits[8:10]), int(digits[10:12]), tzinfo=timezone.utc)
        parsed = pd.to_datetime(text, utc=True, errors="coerce")
        if pd.isna(parsed):
            return None
        return parsed.to_pydatetime()
    except ValueError:
        return None


def standard_offset_for_wfo(wfo: str, lon: float | None = None) -> tuple[int, str]:
    if wfo in STANDARD_TIME_OVERRIDES:
        return STANDARD_TIME_OVERRIDES[wfo]
    if lon is not None:
        if lon <= -130:
            return -9, "AKST"
        if lon <= -114:
            return -8, "PST"
        if lon <= -102:
            return -7, "MST"
        if lon <= -85:
            return -6, "CST"
        if lon <= -60:
            return -5, "EST"
    return 0, "UTC"


def standard_time_display(valid_utc: str | None, wfo: str, lon: float | None = None) -> str | None:
    dt = parse_iem_valid(valid_utc)
    if dt is None:
        return None
    offset, label = standard_offset_for_wfo(wfo, lon)
    return (dt + timedelta(hours=offset)).strftime("%Y-%m-%d %H:%M") + f" {label}"


def build_iem_lsr_url(wfo: str, start: datetime, end: datetime) -> str:
    return prepared_url(IEM_LSR_ENDPOINT, {"wfo": wfo, "sts": iso_z(start), "ets": iso_z(end), "fmt": "csv"})


def fetch_lsr_reports(wfo: str, start: datetime, end: datetime) -> tuple[list[dict[str, Any]], str, str | None]:
    url = build_iem_lsr_url(wfo, start, end)
    log(f"Fetching LSRs from {url}")
    try:
        text = fetch_text(url)
    except requests.RequestException as exc:
        return [], url, f"LSR fetch failed: {exc}"
    if not text.strip():
        return [], url, None
    try:
        df = pd.read_csv(io.StringIO(text))
    except pd.errors.EmptyDataError:
        return [], url, None
    df.columns = [str(col).strip().upper() for col in df.columns]

    reports: list[dict[str, Any]] = []
    for idx, row in df.iterrows():
        valid = clean_text(row.get("VALID"))
        report_type = clean_text(row.get("TYPETEXT"))
        lat = to_float(row.get("LAT"))
        lon = to_float(row.get("LON"))
        reports.append({
            "report_id": f"iem-lsr-{wfo}-{idx + 1}",
            "source_dataset": "IEM Local Storm Reports archive",
            "valid_utc": valid,
            "standard_time_display": standard_time_display(valid, wfo, lon),
            "standard_time_zone": standard_offset_for_wfo(wfo, lon)[1],
            "wfo": clean_text(row.get("WFO")) or wfo,
            "report_type": report_type,
            "event_category": event_category(report_type),
            "magnitude": to_float(row.get("MAG")),
            "magnitude_qualifier": clean_text(row.get("QUALIFY")),
            "city": clean_text(row.get("CITY")),
            "county": clean_text(row.get("COUNTY")),
            "state": clean_text(row.get("STATE")),
            "source": clean_text(row.get("SOURCE")),
            "remark": clean_text(row.get("REMARK")),
            "lat": lat,
            "lon": lon,
            "ugc": clean_text(row.get("UGC")),
            "ugc_name": clean_text(row.get("UGCNAME")),
            "source_url": url,
        })
    return reports, url, None


def report_geojson(reports: list[dict[str, Any]], metadata: dict[str, Any]) -> dict[str, Any]:
    features = []
    for report in reports:
        lat = report.get("lat")
        lon = report.get("lon")
        if lat is None or lon is None:
            continue
        features.append({
            "type": "Feature",
            "id": report.get("report_id"),
            "properties": {
                "report_id": report.get("report_id"),
                "report_type": report.get("report_type"),
                "event_category": report.get("event_category"),
                "valid_utc": report.get("valid_utc"),
                "standard_time_display": report.get("standard_time_display"),
                "wfo": report.get("wfo"),
                "county_or_zone": report.get("county"),
                "city": report.get("city"),
                "state": report.get("state"),
                "magnitude": report.get("magnitude"),
                "magnitude_units": None,
                "source": report.get("source"),
                "event_narrative": report.get("remark"),
            },
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
        })
    return {"type": "FeatureCollection", "metadata": metadata, "features": features}


def build_nws_alerts_url(wfo: str, start: datetime, end: datetime) -> str:
    return prepared_url(f"{NWS_API_BASE}/alerts", {"office": wfo, "start": iso_z(start), "end": iso_z(end)})


def empty_warning_alerts(metadata: dict[str, Any], source_url: str, note: str) -> dict[str, Any]:
    return {"type": "FeatureCollection", "metadata": metadata | {"source": source_url, "note": note}, "features": []}


def fetch_warning_alerts(wfo: str, start: datetime, end: datetime, metadata: dict[str, Any]) -> tuple[dict[str, Any], str, str | None]:
    url = build_nws_alerts_url(wfo, start, end)
    now = datetime.now(timezone.utc)
    if end < now - timedelta(days=8):
        note = "NWS API alerts skipped because this month is outside the recent alert-history window. Use warning/product archive links instead."
        log(note)
        return empty_warning_alerts(metadata, url, note), url, None
    if start > now + timedelta(days=1):
        note = "NWS API alerts skipped because this month is in the future."
        log(note)
        return empty_warning_alerts(metadata, url, note), url, None

    log(f"Fetching NWS API alerts from {url}")
    try:
        data = fetch_json(url)
    except requests.RequestException as exc:
        warning = f"NWS alerts fetch failed: {exc}"
        return empty_warning_alerts(metadata, url, warning), url, warning

    features = []
    for feature in data.get("features", []):
        props = feature.get("properties", {}) or {}
        features.append({
            "type": "Feature",
            "id": props.get("id") or feature.get("id"),
            "properties": {key: props.get(key) for key in ["id", "event", "headline", "sent", "effective", "expires", "ends", "status", "messageType", "severity", "certainty", "urgency", "areaDesc", "description", "instruction"]},
            "geometry": feature.get("geometry"),
        })
    return {"type": "FeatureCollection", "metadata": metadata | {"source": url}, "features": features}, url, None


def arcgis_geometry_to_geojson(geometry: dict[str, Any] | None) -> dict[str, Any] | None:
    if not geometry:
        return None
    if "paths" in geometry:
        paths = geometry.get("paths") or []
        if len(paths) == 1:
            return {"type": "LineString", "coordinates": paths[0]}
        if len(paths) > 1:
            return {"type": "MultiLineString", "coordinates": paths}
    if "rings" in geometry:
        rings = geometry.get("rings") or []
        if rings:
            return {"type": "Polygon", "coordinates": rings}
    if "x" in geometry and "y" in geometry:
        return {"type": "Point", "coordinates": [geometry.get("x"), geometry.get("y")]}
    if "type" in geometry and "coordinates" in geometry:
        return geometry
    return None


def normalize_dat_feature(feature: dict[str, Any], idx: int, dat_url: str) -> dict[str, Any] | None:
    geometry = feature.get("geometry")
    properties = feature.get("properties") or feature.get("attributes") or {}
    geojson_geometry = arcgis_geometry_to_geojson(geometry)
    if geojson_geometry is None:
        return None
    properties = dict(properties)
    properties.setdefault("label", properties.get("event_type") or properties.get("EventType") or properties.get("damage_type") or "DAT Tornado Track")
    properties.setdefault("event_type", "Tornado")
    properties.setdefault("source", "NOAA/NWS Damage Assessment Toolkit")
    properties.setdefault("source_url", dat_url)
    properties.setdefault("note", "Track feature loaded from configured DAT source URL.")
    return {"type": "Feature", "id": feature.get("id") or properties.get("OBJECTID") or f"dat-track-{idx + 1}", "properties": properties, "geometry": geojson_geometry}


def empty_tornado_tracks(metadata: dict[str, Any], note: str, source: str | None = None) -> dict[str, Any]:
    return {"type": "FeatureCollection", "metadata": metadata | {"layer": "tornado_tracks", "source": source or DAT_VIEWER_URL, "source_type": "DAT", "note": note}, "features": []}


def tornado_tracks_from_dat(dat_tracks_url: str | None, metadata: dict[str, Any]) -> tuple[dict[str, Any], str | None, str | None]:
    if not dat_tracks_url:
        warning = "DAT tornado track source is not configured for this build. Tornado dots are candidate reports only."
        return empty_tornado_tracks(metadata, warning), None, warning

    log(f"Fetching DAT tornado tracks from {dat_tracks_url}")
    try:
        data = fetch_json(dat_tracks_url, timeout=180)
    except requests.RequestException as exc:
        warning = f"DAT tornado track fetch failed: {exc}"
        return empty_tornado_tracks(metadata, warning, dat_tracks_url), dat_tracks_url, warning

    features = []
    raw_features = data.get("features", [])
    for idx, feature in enumerate(raw_features):
        normalized = normalize_dat_feature(feature, idx, dat_tracks_url)
        if normalized is not None:
            features.append(normalized)

    track_geojson = {
        "type": "FeatureCollection",
        "metadata": metadata | {
            "layer": "tornado_tracks",
            "source": dat_tracks_url,
            "source_type": "DAT",
            "dat_viewer": DAT_VIEWER_URL,
            "note": "Track layer is populated only from the configured DAT source URL.",
        },
        "features": features,
    }
    return track_geojson, dat_tracks_url, None


def build_product_links(wfo: str, start: datetime, end: datetime, lsr_url: str, alerts_url: str, dat_tracks_url: str | None) -> dict[str, Any]:
    groups = []
    for group in PRODUCT_GROUPS:
        links = []
        for pil in group["pils"]:
            links.append({"pil": pil, "label": f"Recent NWS API {pil} products for {wfo}", "url": f"{NWS_API_BASE}/products/types/{pil}/locations/{wfo}", "note": "NWS API product endpoint is useful for recent products; use IEM archive link for older monthly review."})
        groups.append({**group, "links": links})

    primary_links = [
        {"label": "IEM Local Storm Reports CSV used by this build", "url": lsr_url, "note": "Candidate LSR source used to build reports.geojson and dashboard.json."},
        {"label": "IEM NWS text product archive search", "url": IEM_AFOS_LIST_URL, "note": "Use this to search archived NWS text products by center or product ID for the selected month."},
        {"label": "NWS API alerts query used by this build", "url": alerts_url, "note": "NWS API alert history is limited; older months use product archive links instead."},
        {"label": "NOAA/NWS Damage Assessment Toolkit viewer", "url": DAT_VIEWER_URL, "note": "Use for public tornado/damage survey review."},
    ]
    if dat_tracks_url:
        primary_links.append({"label": "DAT tornado track source used by this build", "url": dat_tracks_url, "note": "Source for tornado_tracks.geojson."})

    return {"metadata": {"schema_version": SCHEMA_VERSION, "wfo": wfo, "start_utc": iso_z(start), "end_utc": iso_z(end), "generated_utc": utc_now()}, "primary_links": primary_links, "product_groups": groups}


def build_summary(reports: list[dict[str, Any]], warnings_geojson: dict[str, Any], tornado_tracks: dict[str, Any], year: int, month: int, wfo: str, source_warnings: list[str]) -> dict[str, Any]:
    category_counts = Counter(report.get("event_category") or "other" for report in reports)
    type_counts = Counter(report.get("report_type") or "Unknown" for report in reports)
    warning_counts = Counter((feature.get("properties") or {}).get("event") or "Unknown" for feature in warnings_geojson.get("features", []))
    return {
        "schema_version": SCHEMA_VERSION,
        "year": year,
        "month": month,
        "wfo": wfo,
        "total_candidate_reports": len(reports),
        "mapped_candidate_reports": sum(1 for report in reports if report.get("lat") is not None and report.get("lon") is not None),
        "candidate_report_counts": dict(sorted(category_counts.items())),
        "candidate_report_type_counts": dict(sorted(type_counts.items())),
        "nws_api_alert_count": len(warnings_geojson.get("features", [])),
        "nws_api_alert_type_counts": dict(sorted(warning_counts.items())),
        "tornado_track_count": len(tornado_tracks.get("features", [])),
        "source_warnings": source_warnings,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"Wrote {path}")


def update_index(index_path: Path, year: int, month: int, wfo: str) -> None:
    month_text = f"{month:02d}"
    record = {
        "year": year,
        "month": month_text,
        "wfo": wfo,
        "dashboard_json": f"data/stormprep/{year}/{month_text}/{wfo}/dashboard.json",
        "reports_geojson": f"data/stormprep/{year}/{month_text}/{wfo}/reports.geojson",
        "products_json": f"data/stormprep/{year}/{month_text}/{wfo}/products.json",
        "warnings_geojson": f"data/stormprep/{year}/{month_text}/{wfo}/warnings.geojson",
        "tornado_tracks_geojson": f"data/stormprep/{year}/{month_text}/{wfo}/tornado_tracks.geojson",
        "summary_json": f"data/stormprep/{year}/{month_text}/{wfo}/summary.json",
    }
    if index_path.exists() and index_path.read_text(encoding="utf-8").strip():
        data = json.loads(index_path.read_text(encoding="utf-8"))
    else:
        data = {"schema_version": SCHEMA_VERSION, "description": "Public data index for the Storm Data Dashboard.", "available_months": []}
    data["schema_version"] = SCHEMA_VERSION
    prep_months = data.setdefault("available_prep_months", [])
    prep_months = [item for item in prep_months if not (item.get("year") == year and item.get("month") == month_text and item.get("wfo") == wfo)]
    prep_months.append(record)
    data["available_prep_months"] = sorted(prep_months, key=lambda item: (item.get("year", 0), item.get("month", ""), item.get("wfo", "")))
    write_json(index_path, data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build one Storm Data prep dashboard month from public web sources.")
    parser.add_argument("--year", required=True, type=int, help="Four-digit year to build.")
    parser.add_argument("--month", required=True, type=int, choices=range(1, 13), help="Month number, 1-12.")
    parser.add_argument("--wfo", required=True, help="Three-letter WFO identifier, such as LIX.")
    parser.add_argument("--dat-tracks-url", default="", help="DAT GeoJSON or ArcGIS REST JSON URL to use for tornado_tracks.geojson. Leave blank to produce a DAT-not-configured warning.")
    parser.add_argument("--out-root", default="docs/data/stormprep", help="Root output folder for public prep JSON.")
    parser.add_argument("--index", default="docs/data/index.json", help="Public data index JSON path.")
    parser.add_argument("--update-index", type=int, default=1, choices=[0, 1], help="Whether to update docs/data/index.json.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    year = args.year
    month = args.month
    wfo = args.wfo.strip().upper()
    dat_tracks_url = args.dat_tracks_url.strip() or None
    start, end = month_window(year, month)
    generated_utc = utc_now()
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "year": year,
        "month": month,
        "wfo": wfo,
        "start_utc": iso_z(start),
        "end_utc": iso_z(end),
        "generated_utc": generated_utc,
        "mode": "storm_data_prep",
        "public_release_status": "public-source-derived",
        "time_note": "Storm Data entry times should be reviewed in local Standard Time (ST), not daylight time. Candidate reports include standard_time_display.",
        "tornado_track_policy": "Tornado tracks must come from DAT. NCEI begin/end coordinates are not used as a tornado track substitute.",
    }

    source_warnings: list[str] = []
    reports, lsr_url, lsr_warning = fetch_lsr_reports(wfo, start, end)
    if lsr_warning:
        source_warnings.append(lsr_warning)
    warnings_geojson, alerts_url, alerts_warning = fetch_warning_alerts(wfo, start, end, metadata)
    if alerts_warning:
        source_warnings.append(alerts_warning)
    tornado_tracks, dat_source_url, dat_warning = tornado_tracks_from_dat(dat_tracks_url, metadata)
    if dat_warning:
        source_warnings.append(dat_warning)

    tornado_report_count = sum(1 for report in reports if report.get("event_category") == "tornado")
    if tornado_report_count > 0 and len(tornado_tracks.get("features", [])) == 0:
        source_warnings.append("Tornado candidate reports were found, but DAT tornado tracks were not available for this build.")

    products = build_product_links(wfo, start, end, lsr_url, alerts_url, dat_source_url)
    summary = build_summary(reports, warnings_geojson, tornado_tracks, year, month, wfo, source_warnings)
    reports_geojson = report_geojson(reports, metadata | {"source": lsr_url})

    month_text = f"{month:02d}"
    out_dir = Path(args.out_root) / str(year) / month_text / wfo
    dashboard = {
        "metadata": metadata,
        "summary": summary,
        "sources": {"iem_lsr_csv": lsr_url, "nws_api_alerts": alerts_url, "iem_text_archive": IEM_AFOS_LIST_URL, "dat_viewer": DAT_VIEWER_URL, "dat_tornado_tracks": dat_source_url},
        "source_warnings": source_warnings,
        "candidate_reports": reports,
        "product_collections": products,
        "files": {"reports_geojson": "reports.geojson", "products_json": "products.json", "warnings_geojson": "warnings.geojson", "tornado_tracks_geojson": "tornado_tracks.geojson", "summary_json": "summary.json"},
    }

    write_json(out_dir / "dashboard.json", dashboard)
    write_json(out_dir / "reports.geojson", reports_geojson)
    write_json(out_dir / "products.json", products)
    write_json(out_dir / "warnings.geojson", warnings_geojson)
    write_json(out_dir / "tornado_tracks.geojson", tornado_tracks)
    write_json(out_dir / "summary.json", summary)
    if args.update_index == 1:
        update_index(Path(args.index), year, month, wfo)
    log("Done.")


if __name__ == "__main__":
    main()
