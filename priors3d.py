"""Prior classes for 3D EIG screening."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from phantoms3d import build_roi_target_phantom, coordinate_grid, sphere_mask


@dataclass(frozen=True)
class GaussianPrior3D:
    """Diagonal Gaussian prior approximation for one object class."""

    name: str
    weight: float
    mean_volume: np.ndarray
    diag_var: np.ndarray


def build_smooth_background(cfg: object) -> np.ndarray:
    """Smooth background object used as a prior mean."""

    zz, yy, xx = coordinate_grid(cfg)
    rr = np.sqrt(xx**2 + yy**2 + 0.5 * zz**2)
    return (0.010 + 0.012 * np.exp(-(rr / 0.40) ** 2)).astype(np.float32)


def build_center_target_prior(cfg: object) -> np.ndarray:
    """Smooth background plus a weak central target."""

    vol = build_smooth_background(cfg)
    vol[sphere_mask(cfg, (0.0, 0.0, 0.0), 0.085)] += 0.030
    return vol


def build_roi_target_prior(cfg: object) -> np.ndarray:
    """Smooth background plus an eccentric target."""

    return build_roi_target_phantom(cfg)


def _diag_var(cfg: object, target_mask: np.ndarray | None = None) -> np.ndarray:
    var = np.full((cfg.nz, cfg.ny, cfg.nx), cfg.eig_prior_var_background, dtype=np.float32)
    if target_mask is not None:
        var[target_mask] = cfg.eig_prior_var_target
    return var


def build_eig_prior_classes(cfg: object) -> list[GaussianPrior3D]:
    """Return background, centre target and eccentric ROI target priors."""

    weights = cfg.eig_prior_weights
    center_mask = sphere_mask(cfg, (0.0, 0.0, 0.0), 0.11)
    roi = sphere_mask(cfg, cfg.roi_center, 0.13)
    return [
        GaussianPrior3D("smooth_background", weights[0], build_smooth_background(cfg), _diag_var(cfg)),
        GaussianPrior3D("center_weak_target", weights[1], build_center_target_prior(cfg), _diag_var(cfg, center_mask)),
        GaussianPrior3D("eccentric_roi_target", weights[2], build_roi_target_prior(cfg), _diag_var(cfg, roi)),
    ]
