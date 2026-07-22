import os
import subprocess
import argparse

SCENARIOS = {
    "normal": 5000,
    "gas_leak": 2000,
    "ventilation_failure": 2000,
    "pump_failure": 2000,
    "hot_work_gas_leak": 2000,
    "confined_space": 2000,
    "explosion_risk": 2000
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="Run short scenarios for testing")
    args = parser.parse_args()

    out_dir = "data/raw"
    os.makedirs(out_dir, exist_ok=True)

    print("Generating simulation data...")
    for scenario, default_dur in SCENARIOS.items():
        dur = 500 if args.quick else default_dur
        seed = 42 # for reproducibility
        cmd = [
            "python", "digital twin/simulate.py",
            "--scenario", scenario,
            "--duration", str(dur),
            "--output", f"{out_dir}/{scenario}",
            "--seed", str(seed),
            "--quiet"
        ]
        print(f"Running scenario: {scenario} ({dur} rows)")
        subprocess.run(cmd, check=True)
        print(f"Saved to {out_dir}/{scenario}")

if __name__ == "__main__":
    main()
