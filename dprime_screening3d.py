"""Task-driven d-prime fine screening for 3D source layouts."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from astra_backend3d import forward_project
from eig_screening3d import candidate_to_sources
from phantoms3d import coordinate_grid, sphere_mask
from priors3d import build_smooth_background


@dataclass(frozen=True)
class DetectionTask3D:
    """A local 3D task represented by background, signal and channels."""

    name: str
    description: str
    background: np.ndarray
    signal: np.ndarray
    channels: np.ndarray


def _gaussian_blob(cfg: object, center: tuple[float, float, float], sigma: float) -> np.ndarray:
    zz, yy, xx = coordinate_grid(cfg)
    cx, cy, cz = center
    blob = np.exp(-0.5 * (((xx - cx) ** 2 + (yy - cy) ** 2 + (zz - cz) ** 2) / sigma**2))
    norm = np.linalg.norm(blob.ravel())
    if norm > 0.0:
        blob = blob / norm
    return blob.astype(np.float32)


def _localized_channels(
    cfg: object,
    center: tuple[float, float, float],
    radius: float,
    count: int,
) -> np.ndarray:
    """Build deterministic low-dimensional channels around a task location."""

    base = _gaussian_blob(cfg, center, radius)
    channels = [base]
    offsets = [
        (radius, 0.0, 0.0),
        (-radius, 0.0, 0.0),
        (0.0, radius, 0.0),
        (0.0, -radius, 0.0),
        (0.0, 0.0, radius),
        (0.0, 0.0, -radius),
        (radius, radius, 0.0),
        (-radius, radius, 0.0),
        (radius, 0.0, radius),
        (0.0, radius, radius),
        (-radius, 0.0, radius),
    ]
    for dx, dy, dz in offsets:
        if len(channels) >= count:
            break
        shifted = (center[0] + dx, center[1] + dy, center[2] + dz)
        channels.append(_gaussian_blob(cfg, shifted, radius * 0.85))
    arr = np.asarray(channels, dtype=np.float32)
    flat = arr.reshape(arr.shape[0], -1)
    q, _ = np.linalg.qr(flat.T)
    return q[:, : arr.shape[0]].T.reshape(arr.shape).astype(np.float32)


def _target_signal(cfg: object, center: tuple[float, float, float], radius: float, contrast: float) -> np.ndarray:
    sig = np.zeros((cfg.nz, cfg.ny, cfg.nx), dtype=np.float32)
    sig[sphere_mask(cfg, center, radius)] = contrast
    return sig


def build_dprime_tasks(cfg: object) -> list[DetectionTask3D]:
    """Return known local tasks plus an off-ROI task missing from EIG priors."""

    background = build_smooth_background(cfg)
    center = (0.0, 0.0, 0.0)
    roi = cfg.roi_center
    offroi = (-0.34, 0.26, -0.18)
    material_center = (-0.18, 0.18, -0.08)
    return [
        DetectionTask3D(
            name="center_small_target",
            description="中心小球形低对比目标检测",
            background=background,
            signal=_target_signal(cfg, center, radius=0.075, contrast=0.022),
            channels=_localized_channels(cfg, center, radius=0.075, count=cfg.dprime_channel_count),
        ),
        DetectionTask3D(
            name="eccentric_roi_target",
            description="偏心 ROI 小球形低对比目标检测",
            background=background,
            signal=_target_signal(cfg, roi, radius=0.075, contrast=0.022),
            channels=_localized_channels(cfg, roi, radius=0.075, count=cfg.dprime_channel_count),
        ),
        DetectionTask3D(
            name="offroi_edge_target",
            description="EIG 先验未包含的非预设 ROI 三维边缘小目标检测",
            background=background,
            signal=_target_signal(cfg, offroi, radius=0.075, contrast=0.022),
            channels=_localized_channels(cfg, offroi, radius=0.075, count=cfg.dprime_channel_count),
        ),
        DetectionTask3D(
            name="material_contrast",
            description="局部材料/低对比差异判别任务",
            background=background,
            signal=_target_signal(cfg, material_center, radius=0.115, contrast=0.014),
            channels=_localized_channels(cfg, material_center, radius=0.095, count=cfg.dprime_channel_count),
        ),
    ]


def task_dprime_squared(cfg: object, candidate: dict, task: DetectionTask3D) -> float:
    """Compute a low-dimensional MAP-CHO d-prime squared approximation."""

    sources = candidate_to_sources(cfg, candidate)
    mean_proj = forward_project(cfg, task.background, sources)
    lam = np.maximum(cfg.photons_per_source * np.exp(-mean_proj), 1.0e-6).ravel()
    signal_proj = forward_project(cfg, task.signal, sources).ravel()

    channel_projs = []
    for channel in task.channels:
        channel_projs.append(forward_project(cfg, channel, sources).ravel())
    a = np.asarray(channel_projs, dtype=np.float64)
    weighted_a = a * np.sqrt(lam)[None, :]

    fisher_c = weighted_a @ weighted_a.T
    fisher_c.flat[:: fisher_c.shape[0] + 1] += float(cfg.dprime_regularization_beta)
    delta_c = weighted_a @ (np.sqrt(lam) * signal_proj)
    val = float(delta_c.T @ np.linalg.solve(fisher_c, delta_c))
    return max(val, 0.0)


def score_candidate_dprime(cfg: object, candidate: dict, tasks: list[DetectionTask3D]) -> dict:
    """Score one EIG-screened candidate for all tasks."""

    row = dict(candidate)
    d2_values = []
    for task in tasks:
        d2 = task_dprime_squared(cfg, candidate, task)
        row[f"dprime2_{task.name}"] = d2
        row[f"dprime_{task.name}"] = float(np.sqrt(d2))
        d2_values.append(d2)
    row["task_utility_min_dprime2"] = float(np.min(d2_values))
    row["task_utility_mean_dprime2"] = float(np.mean(d2_values))
    row["task_utility_min_dprime"] = float(np.sqrt(row["task_utility_min_dprime2"]))
    return row


def rank_candidates_by_dprime3d(cfg: object, top_candidates: list[dict]) -> tuple[list[dict], list[DetectionTask3D]]:
    """Rank EIG-top candidates by maximin task d-prime."""

    tasks = build_dprime_tasks(cfg)
    rows = [score_candidate_dprime(cfg, cand, tasks) for cand in top_candidates]
    rows.sort(key=lambda r: (r["task_utility_min_dprime2"], r["task_utility_mean_dprime2"]), reverse=True)
    for idx, row in enumerate(rows, start=1):
        row["dprime_rank"] = idx
    eig_sorted = sorted(rows, key=lambda r: r["eig_weighted"], reverse=True)
    for idx, row in enumerate(eig_sorted, start=1):
        row["eig_rank_within_top"] = idx
    return rows, tasks
