"""Build one public Storm Data dashboard month from one downloaded Storm Events CSV.

This is the first real ingest script for the static GitHub Pages dashboard.
It reads a local/public Storm Events CSV, filters one WFO/year/month, and writes:

- docs/data/stormdata/YYYY/MM/WFO/events.json
- docs/data/stormdata/YYYY/MM/WFO/events.geojson
- docs/data/stormdata/YYYY/MM/WFO/summary.json

PowerShell example:
python .\scripts\build_month.py `
  --csv .\data\raw\storm_events_2024.csv `
  --year 2024 `
  --month 5 `
  --wfo LIX

Notes:
- The CSV should be a public Storm Events / Storm Data style CSV.
- This script does not publish raw CSV files.
- It only writes dashboard-ready JSON/GeoJSON under docs/data/.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from dateutil import parser as date_parser


SCHEMA_VERSION = "0.1.0"

EVENT_CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("tornado", ["TORNADO", "WATERSPOUT"]),
    ("hail", ["HAIL"]),
    ("thunderstorm_wind", ["THUNDERSTORM WIND", "TSTM WIND", "HIGH WIND", "STRONG WIND"]),
    ("flooding", ["FLASH FLOOD", "FLOOD", "COASTAL FLOOD", "LAKESHORE FLOOD", "STORM SURGE"]),
    ("drought", ["DROUGHT"]),
    ("heat_cold", ["EXCESSIVE HEAT", "HEAT", "EXTREME COLD", "COLD", "WIND CHILL", "FROST", "FREEZE"]),
    ("tropical_coastal", ["HURRICANE", "TROPICAL STORM", "TROPICAL DEPRESSION", "RIP CURRENT", "HIGH SURF"]),
    ("winter", ["WINTER", "SNOW", "ICE", "SLEET", "BLIZZARD", "AVALANCHE", "LAKE-EFFECT"]),
    ("marine", ["MARINE", "SEICHE"]),
    ("fire_smoke", ["WILDFIRE", "DENSE SMOKE"]),
    ("other", []),
]


def log(message: str) -> None:
    print(message, flush=True)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(col).strip().upper() for col in df.columns]
    return df


def get_value(row: pd.Series, *names: str, default: Any = None) -> Any:
    for name in names:
        key = name.upper()
        if key in row.index:
            value = row[key]
            if pd.isna(value):
                continue
            return value
    return default


def to_int(value: Any) -> int | None:
    if value is None or pd.isna(value):
        return None
    try:
        text = str(value).strip()
        if text == "":
            return None
        return int(float(text))
    except (TypeError, ValueError):
        return None


def to_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        text = str(value).strip()
        if text == "":
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def clean_text(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if text == "" or text.lower() == "nan":
        return None
    return text


def parse_storm_time(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None

    try:
        dt = date_parser.parse(text, fuzzy=True)
    except (ValueError, TypeError, OverflowError):
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    return dt.isoformat().replace("+00:00", "Z")


def parse_time_from_parts(yearmonth: Any, day: Any, hhmm: Any) -> str | None:
    ym = clean_text(yearmonth)
    dd = to_int(day)
    time_value = clean_text(hhmm)

    if not ym or dd is None or not time_value:
        return None

    ym = ym.replace(".0", "")
    if len(ym) < 6:
        return None

    try:
        year = int(ym[:4])
        month = int(ym[4:6])
        digits = "".join(ch for ch in time_value if ch.isdigit())
        digits = digits.zfill(4)[-4:]
        hour = int(digits[:2])
        minute = int(digits[2:])
        dt = datetime(year, month, dd, hour, minute, tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")
    except ValueError:
        return None


def get_begin_time_utc(row: pd.Series) -> str | None:
    direct = parse_storm_time(get_value(row, "BEGIN_DATE_TIME"))
    if direct:
        return direct
    return parse_time_from_parts(
        get_value(row, "BEGIN_YEARMONTH"),
        get_value(row, "BEGIN_DAY"),
        get_value(row, "BEGIN_TIME"),
    )


def get_end_time_utc(row: pd.Series) -> str | None:
    direct = parse_storm_time(get_value(row, "END_DATE_TIME"))
    if direct:
        return direct
    return parse_time_from_parts(
        get_value(row, "END_YEARMONTH"),
        get_value(row, "END_DAY"),
        get_value(row, "END_TIME"),
    )


def normalize_month(value: Any) -> int | None:
    month = to_int(value)
    if month is not None and 1 <= month <= 12:
        return month

    text = clean_text(value)
    if not text:
        return None

    try:
        return date_parser.parse(text).month
    except (ValueError, TypeError, OverflowError):
        return None


def event_category(event_type: Any) -> str:
    text = clean_text(event_type)
    if not text:
        return "other"

    upper = text.upper()
    for category, needles in EVENT_CATEGORY_RULES:
        if category == "other":
            continue
        if any(needle in upper for needle in needles):
            return category
    return "other"


def filter_month(df: pd.DataFrame, year: int, month: int, wfo: str) -> pd.DataFrame:
    filtered = df.copy()

    if "YEAR" in filtered.columns:
        filtered = filtered[pd.to_numeric(filtered["YEAR"], errors="coerce") == year]
    elif "BEGIN_YEARMONTH" in filtered.columns:
        ym = pd.to_numeric(filtered["BEGIN_YEARMONTH"], errors="coerce")
        filtered = filtered[(ym // 100) == year]

    if "MONTH_NAME" in filtered.columns:
        months = filtered["MONTH_NAME"].apply(normalize_month)
        filtered = filtered[months == month]
    elif "BEGIN_YEARMONTH" in filtered.columns:
        ym = pd.to_numeric(filtered["BEGIN_YEARMONTH"], errors="coerce")
        filtered = filtered[(ym % 100) == month]

    if "WFO" not in filtered.columns:
        raise RuntimeError("Input CSV does not include a WFO column. WFO filtering cannot be done safely yet.")

    filtered = filtered[filtered["WFO"].astype(str).str.upper().str.strip() == wfo]

    return filtered.copy()


def build_event(row: pd.Series) -> dict[str, Any]:
    event_type = clean_text(get_value(row, "EVENT_TYPE"))
    begin_lat = to_float(get_value(row, "BEGIN_LAT"))
    begin_lon = to_float(get_value(row, "BEGIN_LON"))
    end_lat = to_float(get_value(row, "END_LAT"))
    end_lon = to_float(get_value(row, "END_LON"))

    magnitude = to_float(get_value(row, "MAGNITUDE"))
    if magnitude is not None and magnitude.is_integer():
        magnitude = int(magnitude)

    return {
        "event_id": clean_text(get_value(row, "EVENT_ID")),
        "episode_id": clean_text(get_value(row, "EPISODE_ID")),
        "event_type": event_type,
        "event_category": event_category(event_type),
        "begin_time_utc": get_begin_time_utc(row),
        "end_time_utc": get_end_time_utc(row),
        "state": clean_text(get_value(row, "STATE")),
        "cz_type": clean_text(get_value(row, "CZ_TYPE")),
        "cz_name": clean_text(get_value(row, "CZ_NAME")),
        "county_or_zone": clean_text(get_value(row, "CZ_NAME")),
        "wfo": clean_text(get_value(row, "WFO")),
        "begin_lat": begin_lat,
        "begin_lon": begin_lon,
        "end_lat": end_lat,
        "end_lon": end_lon,
        "begin_location": clean_text(get_value(row, "BEGIN_LOCATION")),
        "end_location": clean_text(get_value(row, "END_LOCATION")),
        "magnitude": magnitude,
        "magnitude_units": clean_text(get_value(row, "MAGNITUDE_TYPE")),
        "source": clean_text(get_value(row, "SOURCE")),
        "flood_cause": clean_text(get_value(row, "FLOOD_CAUSE")),
        "tor_f_scale": clean_text(get_value(row, "TOR_F_SCALE")),
        "tor_length": to_float(get_value(row, "TOR_LENGTH")),
        "tor_width": to_float(get_value(row, "TOR_WIDTH")),
        "injuries_direct": to_int(get_value(row, "INJURIES_DIRECT")) or 0,
        "injuries_indirect": to_int(get_value(row, "INJURIES_INDIRECT")) or 0,
        "deaths_direct": to_int(get_value(row, "DEATHS_DIRECT")) or 0,
        "deaths_indirect": to_int(get_value(row, "DEATHS_INDIRECT")) or 0,
        "property_damage": clean_text(get_value(row, "DAMAGE_PROPERTY")),
        "crop_damage": clean_text(get_value(row, "DAMAGE_CROPS")),
        "event_narrative": clean_text(get_value(row, "EVENT_NARRATIVE")),
        "episode_narrative": clean_text(get_value(row, "EPISODE_NARRATIVE")),
        "data_source": clean_text(get_value(row, "DATA_SOURCE")),
        "source_links": [],
    }


def event_geometry(event: dict[str, Any]) -> dict[str, Any] | None:
    begin_lat = event.get("begin_lat")
    begin_lon = event.get("begin_lon")
    end_lat = event.get("end_lat")
    end_lon = event.get("end_lon")

    if begin_lat is None or begin_lon is None:
        return None

    if (
        end_lat is not None
        and end_lon is not None
        and (round(float(begin_lat), 5), round(float(begin_lon), 5)) != (round(float(end_lat), 5), round(float(end_lon), 5))
    ):
        return {
            "type": "LineString",
            "coordinates": [[begin_lon, begin_lat], [end_lon, end_lat]],
        }

    return {
        "type": "Point",
        "coordinates": [begin_lon, begin_lat],
    }


def build_geojson(events: list[dict[str, Any]], metadata: dict[str, Any]) -> dict[str, Any]:
    features = []

    for event in events:
        geometry = event_geometry(event)
        if geometry is None:
            continue

        properties = {
            "event_id": event.get("event_id"),
            "episode_id": event.get("episode_id"),
            "event_type": event.get("event_type"),
            "event_category": event.get("event_category"),
            "begin_time_utc": event.get("begin_time_utc"),
            "end_time_utc": event.get("end_time_utc"),
            "county_or_zone": event.get("county_or_zone"),
            "magnitude": event.get("magnitude"),
            "magnitude_units": event.get("magnitude_units"),
            "event_narrative": event.get("event_narrative"),
        }

        features.append(
            {
                "type": "Feature",
                "id": event.get("event_id"),
                "properties": properties,
                "geometry": geometry,
            }
        )

    return {
        "type": "FeatureCollection",
        "metadata": metadata,
        "features": features,
    }


def build_summary(events: list[dict[str, Any]], year: int, month: int, wfo: str) -> dict[str, Any]:
    category_counts = Counter(event.get("event_category") or "other" for event in events)
    type_counts = Counter(event.get("event_type") or "Unknown" for event in events)

    return {
        "schema_version": SCHEMA_VERSION,
        "year": year,
        "month": month,
        "wfo": wfo,
        "total_events": len(events),
        "mapped_events": sum(1 for event in events if event_geometry(event) is not None),
        "event_counts": dict(sorted(category_counts.items())),
        "event_type_counts": dict(sorted(type_counts.items())),
        "fatalities": {
            "direct": sum(event.get("deaths_direct") or 0 for event in events),
            "indirect": sum(event.get("deaths_indirect") or 0 for event in events),
        },
        "injuries": {
            "direct": sum(event.get("injuries_direct") or 0 for event in events),
            "indirect": sum(event.get("injuries_indirect") or 0 for event in events),
        },
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
        "events_json": f"data/stormdata/{year}/{month_text}/{wfo}/events.json",
        "events_geojson": f"data/stormdata/{year}/{month_text}/{wfo}/events.geojson",
        "summary_json": f"data/stormdata/{year}/{month_text}/{wfo}/summary.json",
    }

    if index_path.exists():
        data = json.loads(index_path.read_text(encoding="utf-8"))
    else:
        data = {
            "schema_version": SCHEMA_VERSION,
            "description": "Public data index for the Storm Data Dashboard.",
            "available_months": [],
        }

    months = data.setdefault("available_months", [])
    months = [item for item in months if not (item.get("year") == year and item.get("month") == month_text and item.get("wfo") == wfo)]
    months.append(record)
    months = sorted(months, key=lambda item: (item.get("year", 0), item.get("month", ""), item.get("wfo", "")))
    data["available_months"] = months

    write_json(index_path, data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build one WFO/month from a downloaded Storm Events CSV.")
    parser.add_argument("--csv", required=True, help="Path to downloaded Storm Events CSV.")
    parser.add_argument("--year", required=True, type=int, help="Four-digit year to build.")
    parser.add_argument("--month", required=True, type=int, choices=range(1, 13), help="Month number, 1-12.")
    parser.add_argument("--wfo", required=True, help="Three-letter WFO identifier, such as LIX.")
    parser.add_argument("--out-root", default="docs/data/stormdata", help="Root output folder for public storm data JSON.")
    parser.add_argument("--index", default="docs/data/index.json", help="Public data index JSON path.")
    parser.add_argument("--update-index", type=int, default=1, choices=[0, 1], help="Whether to update docs/data/index.json.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    csv_path = Path(args.csv)
    year = args.year
    month = args.month
    wfo = args.wfo.strip().upper()

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    log(f"Reading {csv_path}")
    df = pd.read_csv(csv_path, low_memory=False)
    df = normalize_columns(df)
    log(f"Input rows: {len(df)}")

    filtered = filter_month(df, year, month, wfo)
    log(f"Rows for {wfo} {year}-{month:02d}: {len(filtered)}")

    events = [build_event(row) for _, row in filtered.iterrows()]

    generated_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "year": year,
        "month": month,
        "wfo": wfo,
        "generated_utc": generated_utc,
        "source": str(csv_path),
        "public_release_status": "public-source-derived",
    }

    month_text = f"{month:02d}"
    out_dir = Path(args.out_root) / str(year) / month_text / wfo

    events_json = {
        "metadata": metadata,
        "events": events,
    }
    geojson = build_geojson(events, metadata)
    summary = build_summary(events, year, month, wfo)

    write_json(out_dir / "events.json", events_json)
    write_json(out_dir / "events.geojson", geojson)
    write_json(out_dir / "summary.json", summary)

    if args.update_index == 1:
        update_index(Path(args.index), year, month, wfo)

    log("Done.")


if __name__ == "__main__":
    main()
