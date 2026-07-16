"""
Extract statistical properties from Tennessee Eastman Process .RData files.

This script runs once to produce tep_statistics.json which the simulator
uses at runtime. The simulator never reads .RData files directly.

Extracts:
  - Per-variable means, stds, min, max for fault-free data
  - Covariance matrix across all 52 variables
  - Autocorrelation coefficients (lag-1 through lag-5)
  - Per-fault mean shifts and variance ratios relative to fault-free baseline
"""

import json
import os
import sys

import numpy as np

# Key TEP variable indices (0-based) that map to refinery concepts
# XMEAS: indices 0-40 (variables 1-41)
# XMV: indices 41-51 (variables 1-11, excluding agitator speed XMV(12))
TEP_TO_REFINERY = {
    # XMEAS mappings (0-based index into 52-variable vector)
    6:  "pipeline_pressure",       # XMEAS(7) Reactor Pressure
    12: "tank_pressure",           # XMEAS(13) Prod Sep Pressure
    15: "pump_outlet_pressure",    # XMEAS(16) Stripper Pressure
    8:  "pipeline_temperature",    # XMEAS(9) Reactor Temperature
    10: "tank_temperature",        # XMEAS(11) Product Sep Temp
    17: "pump_temperature",        # XMEAS(18) Stripper Temperature
    0:  "hydrocarbon_flow",        # XMEAS(1) A Feed Flow
    5:  "pipeline_flow",           # XMEAS(6) Reactor Feed Rate
    16: "pump_flow",               # XMEAS(17) Stripper Underflow
    19: "pump_power",              # XMEAS(20) Compressor Work
    7:  "tank_level",              # XMEAS(8) Reactor Level
    11: "separator_level",         # XMEAS(12) Product Sep Level
    # XMV mappings (offset by 41 since they come after XMEAS in data)
    43: "isolation_valve",         # XMV(3) A Feed Valve
    46: "relief_valve",            # XMV(6) Purge Valve
    49: "steam_valve",             # XMV(9) Stripper Steam Valve
    50: "pump_speed",              # XMV(10) Reactor CW Flow → Pump Speed
}

# Relevant variable indices for covariance extraction
RELEVANT_INDICES = sorted(TEP_TO_REFINERY.keys())


def extract_from_rdata(rdata_path: str) -> np.ndarray:
    """Load an RData file and return the data as a numpy array."""
    try:
        import pyreadr
    except ImportError:
        print("ERROR: pyreadr not installed. Run: pip install pyreadr")
        sys.exit(1)

    print(f"  Loading {rdata_path}...")
    result = pyreadr.read_r(rdata_path)
    # RData files contain named dataframes
    key = list(result.keys())[0]
    df = result[key]
    print(f"  Shape: {df.shape}, Columns: {list(df.columns[:5])}...")

    # The data has columns: faultNumber, simulationRun, sample, then 52 process vars
    # Extract just the 52 process variables
    process_cols = [c for c in df.columns if c not in ('faultNumber', 'simulationRun', 'sample')]
    data = df[process_cols].values.astype(np.float64)
    print(f"  Process data shape: {data.shape}")
    return data, df


def compute_autocorrelation(data: np.ndarray, max_lag: int = 5) -> dict:
    """Compute autocorrelation coefficients for each variable."""
    n_vars = data.shape[1]
    autocorr = {}
    for lag in range(1, max_lag + 1):
        coeffs = []
        for j in range(n_vars):
            x = data[:, j]
            x_centered = x - np.mean(x)
            var = np.var(x)
            if var < 1e-10:
                coeffs.append(0.0)
            else:
                c = np.mean(x_centered[:-lag] * x_centered[lag:]) / var
                coeffs.append(float(c))
        autocorr[f"lag_{lag}"] = coeffs
    return autocorr


def extract_fault_signatures(faulty_path: str, baseline_means: np.ndarray,
                              baseline_stds: np.ndarray) -> dict:
    """Extract per-fault mean shifts and variance ratios relative to baseline."""
    try:
        import pyreadr
    except ImportError:
        sys.exit(1)

    print(f"  Loading faulty data from {faulty_path}...")
    result = pyreadr.read_r(faulty_path)
    key = list(result.keys())[0]
    df = result[key]

    process_cols = [c for c in df.columns if c not in ('faultNumber', 'simulationRun', 'sample')]
    fault_numbers = df['faultNumber'].values

    signatures = {}
    unique_faults = sorted(set(fault_numbers))
    print(f"  Found faults: {unique_faults}")

    for fault_id in unique_faults:
        if fault_id == 0:
            continue
        fault_id = int(fault_id)
        mask = fault_numbers == fault_id
        fault_data = df.loc[mask, process_cols].values.astype(np.float64)

        if len(fault_data) < 100:
            continue

        fault_means = np.mean(fault_data, axis=0)
        fault_stds = np.std(fault_data, axis=0)

        # Mean shift as fraction of baseline std
        safe_stds = np.where(baseline_stds > 1e-10, baseline_stds, 1.0)
        mean_shifts = ((fault_means - baseline_means) / safe_stds).tolist()

        # Variance ratio
        variance_ratios = (fault_stds / safe_stds).tolist()

        # Only keep relevant indices
        signatures[str(fault_id)] = {
            "mean_shifts": {TEP_TO_REFINERY[i]: mean_shifts[i]
                           for i in RELEVANT_INDICES if i < len(mean_shifts)},
            "variance_ratios": {TEP_TO_REFINERY[i]: variance_ratios[i]
                               for i in RELEVANT_INDICES if i < len(variance_ratios)},
        }
        print(f"    Fault {fault_id}: {sum(mask)} samples, "
              f"max |shift|={max(abs(s) for s in mean_shifts):.2f}")

    return signatures


def main():
    tep_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'tennessee_eastman_process')
    output_path = os.path.join(os.path.dirname(__file__), 'tep_statistics.json')

    # --- Fault-free training data ---
    ff_path = os.path.join(tep_dir, 'TEP_FaultFree_Training.RData')
    if not os.path.exists(ff_path):
        print(f"ERROR: {ff_path} not found")
        sys.exit(1)

    print("=== Extracting fault-free statistics ===")
    ff_data, ff_df = extract_from_rdata(ff_path)
    n_vars = ff_data.shape[1]
    print(f"  Total variables: {n_vars}")

    # Basic statistics
    means = np.mean(ff_data, axis=0)
    stds = np.std(ff_data, axis=0)
    mins = np.min(ff_data, axis=0)
    maxs = np.max(ff_data, axis=0)

    # Covariance matrix for relevant variables only
    relevant_data = ff_data[:, RELEVANT_INDICES]
    cov_matrix = np.cov(relevant_data, rowvar=False).tolist()

    # Correlation matrix
    corr_matrix = np.corrcoef(relevant_data, rowvar=False).tolist()

    # Autocorrelation for relevant variables
    print("  Computing autocorrelation...")
    autocorr_data = ff_data[:, RELEVANT_INDICES]
    autocorr = compute_autocorrelation(autocorr_data, max_lag=5)

    # Build relevant stats dict
    relevant_stats = {}
    for idx_pos, orig_idx in enumerate(RELEVANT_INDICES):
        name = TEP_TO_REFINERY[orig_idx]
        relevant_stats[name] = {
            "mean": float(means[orig_idx]),
            "std": float(stds[orig_idx]),
            "min": float(mins[orig_idx]),
            "max": float(maxs[orig_idx]),
            "autocorr_lag1": float(autocorr["lag_1"][idx_pos]),
            "autocorr_lag2": float(autocorr["lag_2"][idx_pos]),
        }

    # --- Fault signatures ---
    print("\n=== Extracting fault signatures ===")
    faulty_path = os.path.join(tep_dir, 'TEP_Faulty_Training.RData')
    if os.path.exists(faulty_path):
        fault_sigs = extract_fault_signatures(faulty_path, means, stds)
    else:
        print("  WARNING: Faulty training data not found, using empty signatures")
        fault_sigs = {}

    # --- Assemble output ---
    statistics = {
        "description": "Statistical properties extracted from Tennessee Eastman Process dataset",
        "source": "TEP_FaultFree_Training.RData + TEP_Faulty_Training.RData",
        "n_samples_faultfree": int(ff_data.shape[0]),
        "variable_mapping": {TEP_TO_REFINERY[i]: f"original_index_{i}" for i in RELEVANT_INDICES},
        "baseline_statistics": relevant_stats,
        "covariance_matrix": {
            "variables": [TEP_TO_REFINERY[i] for i in RELEVANT_INDICES],
            "matrix": cov_matrix,
        },
        "correlation_matrix": {
            "variables": [TEP_TO_REFINERY[i] for i in RELEVANT_INDICES],
            "matrix": corr_matrix,
        },
        "fault_signatures": fault_sigs,
    }

    print(f"\n=== Writing to {output_path} ===")
    with open(output_path, 'w') as f:
        json.dump(statistics, f, indent=2)
    print(f"  Done! File size: {os.path.getsize(output_path)} bytes")

    # Print summary
    print("\n=== Summary ===")
    for name, stats in relevant_stats.items():
        print(f"  {name:30s}: mean={stats['mean']:10.3f}  std={stats['std']:8.3f}  "
              f"ac1={stats['autocorr_lag1']:.3f}")
    print(f"\n  Fault signatures extracted: {len(fault_sigs)}")


if __name__ == '__main__':
    main()
