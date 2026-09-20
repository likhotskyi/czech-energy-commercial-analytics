"""
The whole analysis in one command.

    python run_analysis.py [--refresh]

Fetch (or read from cache) -> align three sources on the clock -> model -> Excel
calculator -> deck.

Without --refresh it runs entirely from the cached API responses committed here, so
it works offline and reproduces the numbers in the written report exactly. Every
figure in the workbook, the deck and the report comes from one findings.json, so
they cannot disagree with each other.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

STEPS = [
    ("Fetch generation, prices and retail components", ["src/fetch_data.py"]),
    ("Align the three sources on the clock", ["src/build_dataset.py"]),
    ("Run the model", ["src/analyse.py"]),
    ("Build the Excel calculator", ["src/build_excel_report.py"]),
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
                        help="re-download instead of using the cache")
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
