"""Build Storm Data prep packages for many WFOs for one month.

This runner calls scripts/build_month.py once per WFO so GitHub Actions can
prebuild dashboard data for broad/public use.

Examples:
python scripts/build_prep_month_all_wfos.py --year 2026 --month 5 --wfos ALL
python scripts/build_prep_month_all_wfos.py --year 2026 --month 5 --wfos LIX,MOB,JAN,LCH
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_BOUNDARY_ROOT = Path("docs/data/boundaries/by_wfo")
DEFAULT_REPORT_PATH = Path("docs/data/stormprep/build_reports")


def log(message: str) -> None:
    print(message, flush=True)


def discover_wfos(boundary_root: Path) -> list[str]:
    if not boundary_root.exists():
        raise RuntimeError(f"Boundary WFO folder not found: {boundary_root}. Run the boundary workflow first.")

    wfos = []
    for child in boundary_root.iterdir():
        if child.is_dir() and len(child.name) == 3 and (child / "cwa.geojson").exists():
            wfos.append(child.name.upper())

    wfos = sorted(set(wfos))
    if not wfos:
        raise RuntimeError(f"No WFO boundary folders found under {boundary_root}. Run the boundary workflow first.")

    return wfos


def resolve_wfos(value: str, boundary_root: Path) -> list[str]:
    cleaned = value.strip().upper()
    if cleaned in {"ALL", "*", "AUTO"}:
        return discover_wfos(boundary_root)
    return sorted(set(item.strip().upper() for item in value.split(",") if item.strip()))


def run_one(year: int, month: int, wfo: str) -> dict:
    cmd = [
        sys.executable,
        "scripts/build_month.py",
        "--year",
        str(year),
        "--month",
        str(month),
        "--wfo",
        wfo,
    ]

    log("Running: " + " ".join(cmd))
    completed = subprocess.run(cmd, text=True, capture_output=True)

    if completed.stdout:
        print(completed.stdout, flush=True)
    if completed.stderr:
        print(completed.stderr, flush=True)

    return {
        "wfo": wfo,
        "returncode": completed.returncode,
        "ok": completed.returncode == 0,
        "stdout_tail": completed.stdout[-2000:] if completed.stdout else "",
        "stderr_tail": completed.stderr[-2000:] if completed.stderr else "",
    }


def write_report(year: int, month: int, results: list[dict], report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"build_report_{year}_{month:02d}.json"
    data = {
        "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "year": year,
        "month": month,
        "total_wfos": len(results),
        "successful_wfos": sum(1 for item in results if item["ok"]),
        "failed_wfos": sum(1 for item in results if not item["ok"]),
        "results": results,
    }
    report_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return report_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Storm Data prep packages for many WFOs for one month.")
    parser.add_argument("--year", required=True, type=int, help="Four-digit year to build.")
    parser.add_argument("--month", required=True, type=int, choices=range(1, 13), help="Month number, 1-12.")
    parser.add_argument("--wfos", default="ALL", help="Comma-separated WFO list, or ALL to use docs/data/boundaries/by_wfo.")
    parser.add_argument("--boundary-root", default=str(DEFAULT_BOUNDARY_ROOT), help="Folder containing WFO boundary subfolders.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_PATH), help="Folder for all-WFO build report JSON.")
    parser.add_argument("--fail-on-any-error", type=int, default=0, choices=[0, 1], help="Exit nonzero if any WFO build fails.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    boundary_root = Path(args.boundary_root)
    report_dir = Path(args.report_dir)
    wfos = resolve_wfos(args.wfos, boundary_root)

    log(f"Building Storm Data prep packages for {len(wfos)} WFOs for {args.year}-{args.month:02d}")

    results = []
    for idx, wfo in enumerate(wfos, start=1):
        log(f"[{idx}/{len(wfos)}] {wfo}")
        results.append(run_one(args.year, args.month, wfo))

    report_path = write_report(args.year, args.month, results, report_dir)
    failures = [item for item in results if not item["ok"]]

    log(f"Wrote build report: {report_path}")
    log(f"Successful WFOs: {len(results) - len(failures)}")
    log(f"Failed WFOs: {len(failures)}")

    if failures:
        log("Failures: " + ", ".join(item["wfo"] for item in failures))
        if args.fail_on_any_error == 1:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
