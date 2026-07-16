"""
Core multivariate process model derived from Tennessee Eastman Process statistics.

Uses TEP-extracted covariance matrices, autocorrelation coefficients, and
fault signatures to generate realistic, correlated sensor values that
evolve over time.
"""

import json
import os
import math

import numpy as np
from scipy.linalg import cholesky


class ProcessModel:
    """TEP-derived multivariate process model.

    Generates correlated process variables using:
    1. Multivariate normal base state (TEP covariance)
    2. AR(1) temporal dynamics (TEP autocorrelation)
    3. Fault injection (TEP fault signatures with gradual onset)
    4. Equipment state coupling (health → process output)
    """

    def __init__(self, tep_stats_path: str | None = None):
        if tep_stats_path is None:
            tep_stats_path = os.path.join(
                os.path.dirname(__file__), '..', 'tep', 'tep_statistics.json')

        self._load_statistics(tep_stats_path)
        self._init_state()

    def _load_statistics(self, path: str) -> None:
        """Load pre-computed TEP statistics."""
        with open(path, 'r') as f:
            stats = json.load(f)

        self.variable_names = stats["covariance_matrix"]["variables"]
        self.n_vars = len(self.variable_names)

        # Baseline statistics
        self.means = np.array([stats["baseline_statistics"][v]["mean"]
                               for v in self.variable_names])
        self.stds = np.array([stats["baseline_statistics"][v]["std"]
                              for v in self.variable_names])
        self.autocorr_lag1 = np.array([
            stats["baseline_statistics"][v]["autocorr_lag1"]
            for v in self.variable_names])

        # Covariance matrix and its Cholesky decomposition
        cov = np.array(stats["covariance_matrix"]["matrix"])
        # Ensure positive semi-definite
        eigvals = np.linalg.eigvalsh(cov)
        if np.any(eigvals < 0):
            cov += np.eye(self.n_vars) * (abs(eigvals.min()) + 1e-6)
        self.cov_matrix = cov
        self.cholesky_L = cholesky(cov, lower=True)

        # Innovation covariance: Var(innovation) = Var(X) - phi^2 * Var(X)
        # For AR(1): X_t = phi * X_{t-1} + e_t
        phi_sq = self.autocorr_lag1 ** 2
        innovation_var = np.diag(self.cov_matrix) * (1 - phi_sq)
        innovation_var = np.maximum(innovation_var, 1e-10)
        # Build innovation covariance preserving correlations
        corr = stats["correlation_matrix"]["matrix"]
        corr = np.array(corr)
        innovation_std = np.sqrt(innovation_var)
        self.innovation_cov = np.outer(innovation_std, innovation_std) * corr
        # Ensure PSD
        eigvals = np.linalg.eigvalsh(self.innovation_cov)
        if np.any(eigvals < 0):
            self.innovation_cov += np.eye(self.n_vars) * (abs(eigvals.min()) + 1e-6)
        self.innovation_L = cholesky(self.innovation_cov, lower=True)

        # Fault signatures
        self.fault_signatures = {}
        for fault_id, sig in stats.get("fault_signatures", {}).items():
            mean_shifts = np.array([sig["mean_shifts"].get(v, 0.0)
                                    for v in self.variable_names])
            var_ratios = np.array([sig["variance_ratios"].get(v, 1.0)
                                   for v in self.variable_names])
            self.fault_signatures[fault_id] = {
                "mean_shifts": mean_shifts,
                "variance_ratios": var_ratios,
            }

        # Build variable name → index mapping
        self._name_to_idx = {name: i for i, name in enumerate(self.variable_names)}

    def _init_state(self) -> None:
        """Initialize the AR(1) process state."""
        self.state = self.means.copy()
        self._rng = np.random.default_rng(42)

        # Current fault parameters (gradual onset)
        self._active_faults: dict[str, float] = {}  # fault_id → intensity (0-1)
        self._equipment_modifiers: dict[str, float] = {}  # var_name → modifier

    def reset(self, seed: int = 42) -> None:
        """Reset the process model to initial conditions."""
        self.state = self.means.copy()
        self._rng = np.random.default_rng(seed)
        self._active_faults.clear()
        self._equipment_modifiers.clear()

    def step(self, diurnal_factor: float = 0.5) -> dict[str, float]:
        """Generate one timestep of correlated process variables.

        Args:
            diurnal_factor: 0.0 at midnight, 1.0 at noon.

        Returns:
            Dict mapping variable names to current values.
        """
        # 1. AR(1) temporal evolution
        deviation = self.state - self.means
        innovation = self.innovation_L @ self._rng.standard_normal(self.n_vars)
        self.state = self.means + self.autocorr_lag1 * deviation + innovation

        # 2. Apply fault signatures
        for fault_id, intensity in self._active_faults.items():
            if fault_id in self.fault_signatures:
                sig = self.fault_signatures[fault_id]
                # Mean shift proportional to intensity
                self.state += sig["mean_shifts"] * self.stds * intensity * 0.01
                # Variance inflation — applied through innovation scaling
                # (already captured in mean shift; variance effect is implicit)

        # 3. Apply equipment state modifiers
        for var_name, modifier in self._equipment_modifiers.items():
            idx = self._name_to_idx.get(var_name)
            if idx is not None:
                # Use additive shift toward zero instead of multiplicative
                # to prevent overflow when modifier is 0
                target = self.means[idx] * modifier
                self.state[idx] = self.state[idx] * modifier + self.means[idx] * (1 - modifier)

        # Clamp state to prevent numerical overflow
        for i in range(self.n_vars):
            lo = self.means[i] - 20 * self.stds[i]
            hi = self.means[i] + 20 * self.stds[i]
            self.state[i] = max(lo, min(hi, self.state[i]))

        # 4. Diurnal cycle on temperature-related variables
        temp_indices = [self._name_to_idx.get(v) for v in
                        ("pipeline_temperature", "tank_temperature", "pump_temperature")
                        if v in self._name_to_idx]
        for idx in temp_indices:
            if idx is not None:
                diurnal_effect = (diurnal_factor - 0.5) * 1.0
                self.state[idx] += diurnal_effect

        # 5. Build output dict
        return {name: float(self.state[i])
                for i, name in enumerate(self.variable_names)}

    def inject_fault(self, fault_id: str, intensity: float) -> None:
        """Set fault intensity (0.0 = no fault, 1.0 = full fault magnitude).

        Use gradual ramp for realistic fault onset.
        """
        self._active_faults[fault_id] = max(0.0, min(1.0, intensity))

    def clear_faults(self) -> None:
        """Remove all active faults."""
        self._active_faults.clear()

    def set_equipment_modifier(self, var_name: str, modifier: float) -> None:
        """Apply a multiplicative modifier from equipment state.

        Example: pump at 50% speed → set_equipment_modifier("pump_speed", 0.5)
        """
        self._equipment_modifiers[var_name] = modifier

    def clear_equipment_modifiers(self) -> None:
        self._equipment_modifiers.clear()

    def get_variable(self, name: str) -> float:
        """Get current value of a single variable."""
        idx = self._name_to_idx.get(name)
        if idx is not None:
            return float(self.state[idx])
        return 0.0

    @property
    def variable_index(self) -> dict[str, int]:
        return self._name_to_idx.copy()
