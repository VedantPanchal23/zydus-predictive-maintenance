"""
Population Stability Index (PSI) & Model Drift Evaluator
========================================================
Monitors distribution shift across high-frequency telemetry channels
to trigger autonomous GxP-validated ML retraining cycles.
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple

logger = logging.getLogger("drift-evaluator")


def calculate_feature_psi(
    baseline: np.ndarray,
    target: np.ndarray,
    num_buckets: int = 10,
    epsilon: float = 1e-4,
) -> float:
    """
    Calculates the Population Stability Index (PSI) between baseline and target distributions.
    
    Thresholds (Industry Standard / Basel II / GAMP 5):
    - PSI < 0.10: Insignificant Shift (Nominal)
    - 0.10 <= PSI < 0.25: Moderate Shift (Warning)
    - PSI >= 0.25: Significant Distribution Shift (Action Required: Retrain)
    """
    if len(baseline) == 0 or len(target) == 0:
        return 0.0

    # Determine quantile bins based on baseline
    percentiles = np.linspace(0, 100, num_buckets + 1)
    bin_edges = np.percentile(baseline, percentiles)
    bin_edges = np.unique(bin_edges)

    if len(bin_edges) <= 2:
        return 0.0

    # Calculate frequency distributions
    base_counts, _ = np.histogram(baseline, bins=bin_edges)
    target_counts, _ = np.histogram(target, bins=bin_edges)

    base_pct = (base_counts / len(baseline)) + epsilon
    target_pct = (target_counts / len(target)) + epsilon

    # Normalize to 1.0
    base_pct /= base_pct.sum()
    target_pct /= target_pct.sum()

    # PSI calculation: sum((Target - Base) * ln(Target / Base))
    psi_value = np.sum((target_pct - base_pct) * np.log(target_pct / base_pct))
    return float(np.round(max(0.0, psi_value), 4))


def evaluate_dataset_drift(
    baseline_df: pd.DataFrame,
    current_df: pd.DataFrame,
    features: list[str] = None,
) -> Dict[str, Any]:
    """
    Evaluates drift across all numerical sensor features and returns drift status.
    """
    if features is None:
        features = [c for c in baseline_df.columns if pd.api.types.is_numeric_dtype(baseline_df[c])]

    psi_scores = {}
    drifting_features = []

    for feat in features:
        if feat in baseline_df.columns and feat in current_df.columns:
            base_arr = baseline_df[feat].dropna().values
            curr_arr = current_df[feat].dropna().values
            if len(base_arr) > 10 and len(curr_arr) > 10:
                psi = calculate_feature_psi(base_arr, curr_arr)
                psi_scores[feat] = psi
                if psi >= 0.25:
                    drifting_features.append(feat)

    max_psi = max(psi_scores.values()) if psi_scores else 0.0
    mean_psi = np.mean(list(psi_scores.values())) if psi_scores else 0.0

    status = "SIGNIFICANT_DRIFT" if max_psi >= 0.25 else "MODERATE_DRIFT" if max_psi >= 0.10 else "NOMINAL"

    return {
        "drift_status": status,
        "max_psi": round(max_psi, 4),
        "mean_psi": round(float(mean_psi), 4),
        "feature_psi": psi_scores,
        "drifting_features": drifting_features,
        "retraining_recommended": bool(max_psi >= 0.25),
    }
