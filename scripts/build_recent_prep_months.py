"""Build Storm Data prep packages for recent months.

This is intended for scheduled GitHub Actions. By default it builds the current
UTC month and the previous two months for all WFOs that have prebuilt boundary
folders.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone


def add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    month_index = year * 12 + (month - 1) + delta
    new_year = month_index // 12
    new_month = month_index % 12 + 1
    return new_year, new_month


def recent_months(count: int) -> list[tuple[int, int]]:
    now = datetime.now(timezone.utc)
    return [add_months(now.year, now.month, -offset) for offset in range(count)]


def run_month(year: int, month: int, wfos: str) -> int:
    cmd = [
        sys.executable,
        "scripts/build_prep_month_all_wfos.py",
        "--year",
        str(year),
        "--month",
        str(month),
        "--wfos",
        wfos,
        "--fail-on-any-error",
        "0",
    ]
    print("Running: " + " ".join(cmd), flush=True)
    completed = subprocess.run(cmd)
    return completed.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build recent Storm Data prep months.")
    parser.add_argument("--months-back", type=int, default=3, help="Number of months to build including current UTC month.")
    parser.add_argument("--wfos", default="ALL", help="Comma-separated WFO list, or ALL.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    failures = 0
    for year, month in recent_months(args.months_back):
        failures += 1 if run_month(year, month, args.wfos) != 0 else 0
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
