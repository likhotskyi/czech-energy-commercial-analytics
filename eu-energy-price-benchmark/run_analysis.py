"""
The whole analysis in one command.

    python run_analysis.py [--refresh]

Fetch (or read from cache) -> tidy and reconcile -> compute findings ->
Excel workbook -> PowerPoint deck.

Without --refresh it runs entirely from the cached Eurostat responses committed
to this repository, so it works offline and reproduces exactly the numbers in the
written report. With --refresh it re-downloads, and any figure that moved moves
in the spreadsheet, the deck and the report together -- because all three read
the same findings.json and none of them contains a hand-typed number.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

STEPS = [
    ("Fetch the Eurostat series", ["src/fetch_data.py"]),
    ("Tidy the data and reconcile the components", ["src/build_dataset.py"]),
    ("Compute the findings", ["src/analyse.py"]),
    ("Build the Excel workbook", ["src/build_excel_report.py"]),
    ("Build the deck", ["src/build_deck.py"]),
]


def run(label: str, argv: list[str]) -> None:
    print(f"\n>> {label}")
    started = time.perf_counter()
    if subprocess.run([sys.executable, *argv], cwd=ROOT).returncode != 0:
        sys.exit(f"Step failed: {label}")
    print(f"   ({time.perf_counter() - started:.1f}s)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true",
                        help="re-download from Eurostat instead of using the cache")
    args = parser.parse_args()

    started = time.perf_counter()
    for label, argv in STEPS:
        if argv[0].endswith("fetch_data.py") and args.refresh:
            argv = [*argv, "--refresh"]
        run(label, argv)

    print(f"\nFinished in {time.perf_counter() - started:.1f}s. Outputs:")
    for path in sorted((ROOT / "output").glob("*.*")):
        print(f"   {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
