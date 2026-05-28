"""Metrics for 3D rule-baseline comparisons."""

from __future__ import annotations

import numpy as np

from phantoms3d import axial_masks, roi_mask


def rmse(a: np.ndarray, b: np.ndarray, mask: np.ndarray | None = None) -> float:
    """Root mean squared error, optionally inside a mask."""

    diff = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    if mask is not None:
        diff = diff[mask]
    return float(np.sqrt(np.mean(diff * diff)))


def compute_metrics(cfg: object, truth: np.ndarray, recon: np.ndarray, phantom_name: str) -> dict[str, float | str]:
    """Compute global, ROI and axial RMSE metrics."""

    masks = axial_masks(cfg)
    return {
        "phantom": phantom_name,
        "rmse_global": rmse(recon, truth),
        "rmse_roi": rmse(recon, truth, roi_mask(cfg)),
        "rmse_axial_lower": rmse(recon, truth, masks["lower"]),
        "rmse_axial_middle": rmse(recon, truth, masks["middle"]),
        "rmse_axial_upper": rmse(recon, truth, masks["upper"]),
    }
