"""Simple 3D phantoms for rule-baseline experiments."""

from __future__ import annotations

import numpy as np


def coordinate_grid(cfg: object) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return z, y, x coordinate grids matching ASTRA's volume order."""

    x = np.linspace(-cfg.volume_side_xy / 2.0, cfg.volume_side_xy / 2.0, cfg.nx, endpoint=False) + cfg.voxel_size_x / 2.0
    y = np.linspace(-cfg.volume_side_xy / 2.0, cfg.volume_side_xy / 2.0, cfg.ny, endpoint=False) + cfg.voxel_size_y / 2.0
    z = np.linspace(-cfg.volume_height / 2.0, cfg.volume_height / 2.0, cfg.nz, endpoint=False) + cfg.voxel_size_z / 2.0
    zz, yy, xx = np.meshgrid(z, y, x, indexing="ij")
    return zz, yy, xx


def sphere_mask(cfg: object, center: tuple[float, float, float], radius: float) -> np.ndarray:
    """Return a boolean sphere mask in z, y, x order."""

    zz, yy, xx = coordinate_grid(cfg)
    cx, cy, cz = center
    return (xx - cx) ** 2 + (yy - cy) ** 2 + (zz - cz) ** 2 <= radius**2


def cube_mask(cfg: object, center: tuple[float, float, float], side: float) -> np.ndarray:
    """Return a boolean cube mask in z, y, x order."""

    zz, yy, xx = coordinate_grid(cfg)
    cx, cy, cz = center
    h = side / 2.0
    return (np.abs(xx - cx) <= h) & (np.abs(yy - cy) <= h) & (np.abs(zz - cz) <= h)


def build_geometric_phantom(cfg: object) -> np.ndarray:
    """Simple object with two spheres and one cube."""

    vol = np.full((cfg.nz, cfg.ny, cfg.nx), 0.01, dtype=np.float32)
    vol[sphere_mask(cfg, (-0.18, 0.12, 0.0), 0.16)] += 0.035
    vol[sphere_mask(cfg, (0.20, -0.18, 0.22), 0.12)] += 0.045
    vol[cube_mask(cfg, (0.12, 0.18, -0.22), 0.18)] += 0.030
    return vol


def build_roi_target_phantom(cfg: object) -> np.ndarray:
    """Smooth background with an eccentric weak target at cfg.roi_center."""

    zz, yy, xx = coordinate_grid(cfg)
    rr = np.sqrt(xx**2 + yy**2 + 0.6 * zz**2)
    vol = (0.012 + 0.015 * np.exp(-(rr / 0.36) ** 2)).astype(np.float32)
    vol[sphere_mask(cfg, cfg.roi_center, 0.09)] += 0.035
    return vol


def roi_mask(cfg: object, radius: float = 0.13) -> np.ndarray:
    """Return the evaluation ROI mask around cfg.roi_center."""

    return sphere_mask(cfg, cfg.roi_center, radius)


def axial_masks(cfg: object) -> dict[str, np.ndarray]:
    """Return lower/middle/upper axial slab masks."""

    zz, _, _ = coordinate_grid(cfg)
    return {
        "lower": zz < -cfg.volume_height / 6.0,
        "middle": np.abs(zz) <= cfg.volume_height / 6.0,
        "upper": zz > cfg.volume_height / 6.0,
    }
