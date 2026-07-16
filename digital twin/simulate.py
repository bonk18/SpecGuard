#!/usr/bin/env python3
"""
Digital Twin Petroleum Refinery Simulator — CLI Entry Point.

Usage:
    python simulate.py --scenario normal
    python simulate.py --scenario gas_leak
    python simulate.py --scenario explosion
    python simulate.py --scenario all
    python simulate.py --scenario gas_leak --duration 3600
    python simulate.py --format csv --output ./output/
    python simulate.py --format json --output ./output/
    python simulate.py --format both --split
"""

import argparse
import sys
import time
import os

# Add parent dir to path so simulator package can be found
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simulator.plant import Plant, SCENARIO_CLASSES
from simulator.config import ScenarioID, SCENARIO_DURATIONS
from simulator.export.csv_exporter import CSVExporter
from simulator.export.json_exporter import JSONExporter


def run_scenario(plant: Plant, scenario_id: str, duration: int | None,
                 csv_exp: CSVExporter | None, json_exp: JSONExporter | None,
                 verbose: bool = True) -> int:
    """Run a single scenario and export data.

    Returns the number of rows generated.
    """
    # Get scenario class
    scenario_cls = SCENARIO_CLASSES.get(scenario_id)
    if scenario_cls is None:
        print(f"ERROR: Unknown scenario '{scenario_id}'")
        print(f"Available: {', '.join(SCENARIO_CLASSES.keys())}")
        return 0

    # Determine duration
    if duration is None:
        try:
            scenario_enum = ScenarioID(scenario_id)
            duration = SCENARIO_DURATIONS.get(scenario_enum, 5000)
        except ValueError:
            duration = 5000

    # Initialize
    plant.reset()
    scenario = scenario_cls(duration=duration)
    plant.set_scenario(scenario)

    if verbose:
        print(f"\n{'='*60}")
        print(f"  Scenario: {scenario.name}")
        print(f"  Duration: {duration:,} seconds ({duration/3600:.1f} hours)")
        print(f"  Scenario ID: {scenario_id}")
        print(f"{'='*60}")

    rows = 0
    start_time = time.time()
    last_report = start_time

    for _ in range(duration):
        row = plant.tick()

        if csv_exp:
            csv_exp.write_row(row, rows)
        if json_exp:
            json_exp.write_row(row, rows)

        rows += 1

        # Progress reporting
        now = time.time()
        if verbose and (now - last_report) >= 2.0:
            elapsed = now - start_time
            rate = rows / elapsed if elapsed > 0 else 0
            pct = rows / duration * 100
            label = row.get("event_label", "")
            eta = (duration - rows) / rate if rate > 0 else 0
            print(f"  [{pct:5.1f}%] {rows:>8,}/{duration:,} rows  "
                  f"| {rate:,.0f} rows/s | ETA: {eta:.0f}s | {label}")
            last_report = now

    elapsed = time.time() - start_time
    if verbose:
        rate = rows / elapsed if elapsed > 0 else 0
        print(f"  Completed: {rows:,} rows in {elapsed:.1f}s ({rate:,.0f} rows/s)")

    return rows


def main():
    parser = argparse.ArgumentParser(
        description="Digital Twin Petroleum Refinery Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Scenarios:
  normal               Normal steady-state operation (100,000 rows)
  gas_leak             Small gas leak from pump seal failure (5,000 rows)
  ventilation_failure   Ventilation system failure (5,000 rows)
  pump_failure          Pump bearing failure (5,000 rows)
  hot_work_gas_leak     Hot work during gas leak (5,000 rows)
  confined_space        Confined space incident (5,000 rows)
  explosion_risk        Compound explosion risk (5,000 rows)
  all                   Run all scenarios sequentially (130,000 rows)

Examples:
  python simulate.py --scenario gas_leak
  python simulate.py --scenario all --format both
  python simulate.py --scenario normal --duration 1000 --format csv
        """)

    parser.add_argument("--scenario", "-s", type=str, default="normal",
                        choices=list(SCENARIO_CLASSES.keys()) + ["all"],
                        help="Scenario to simulate (default: normal)")
    parser.add_argument("--duration", "-d", type=int, default=None,
                        help="Override default duration (seconds)")
    parser.add_argument("--format", "-f", type=str, default="csv",
                        choices=["csv", "json", "both"],
                        help="Output format (default: csv)")
    parser.add_argument("--output", "-o", type=str, default="./output",
                        help="Output directory (default: ./output)")
    parser.add_argument("--split", action="store_true",
                        help="Split CSV output into category files")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (default: 42)")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress progress output")

    args = parser.parse_args()

    # Banner
    if not args.quiet:
        print(r"""
  ╔═══════════════════════════════════════════════════════════╗
  ║     DIGITAL TWIN — Petroleum Refinery Simulator          ║
  ║     Industrial Safety Intelligence Data Generator        ║
  ╚═══════════════════════════════════════════════════════════╝
        """)

    # Setup exporters
    os.makedirs(args.output, exist_ok=True)
    csv_exp = None
    json_exp = None

    if args.format in ("csv", "both"):
        csv_exp = CSVExporter(args.output, split=args.split)
    if args.format in ("json", "both"):
        json_exp = JSONExporter(args.output)

    # Initialize plant
    plant = Plant(seed=args.seed)
    total_rows = 0
    overall_start = time.time()

    if args.scenario == "all":
        # Run all scenarios sequentially
        scenarios = list(SCENARIO_CLASSES.keys())
        for sid in scenarios:
            duration = args.duration  # None = use defaults
            rows = run_scenario(plant, sid, duration,
                               csv_exp, json_exp, not args.quiet)
            total_rows += rows
    else:
        total_rows = run_scenario(plant, args.scenario, args.duration,
                                  csv_exp, json_exp, not args.quiet)

    # Cleanup
    if csv_exp:
        csv_exp.close()
    if json_exp:
        json_exp.close()

    overall_elapsed = time.time() - overall_start

    if not args.quiet:
        print(f"\n{'='*60}")
        print(f"  SIMULATION COMPLETE")
        print(f"  Total rows: {total_rows:,}")
        print(f"  Total time: {overall_elapsed:.1f}s")
        print(f"  Output: {os.path.abspath(args.output)}/")

        # List generated files
        for f in sorted(os.listdir(args.output)):
            fp = os.path.join(args.output, f)
            if os.path.isfile(fp):
                size_mb = os.path.getsize(fp) / (1024 * 1024)
                print(f"    {f} ({size_mb:.1f} MB)")

        print(f"{'='*60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
