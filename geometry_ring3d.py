"""3D ring source and flat detector geometry utilities."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SourceSet3D:
    """Point sources and their principal directions."""

    positions: np.ndarray
    directions: np.ndarray
    architecture: str
    layer_zs: tuple[float, ...]
    target: tuple[float, float, float]


def _unit(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    n[n == 0.0] = 1.0
    return v / n


def build_layered_ring_sources(
    total_sources: int,
    detector_radius: float,
    layer_zs: tuple[float, ...],
    architecture: str,
    target: tuple[float, float, float] = (0.0, 0.0, 0.0),
    stagger: bool = True,
) -> SourceSet3D:
    """Place sources on one or more circular rings with optional angular staggering."""

    layer_count = len(layer_zs)
    base = total_sources // layer_count
    remainder = total_sources % layer_count
    positions = []
    target_arr = np.asarray(target, dtype=float)
    for li, z in enumerate(layer_zs):
        n_layer = base + (1 if li < remainder else 0)
        offset = (li / layer_count) * (2.0 * np.pi / max(n_layer, 1)) if stagger else 0.0
        angles = offset + 2.0 * np.pi * np.arange(n_layer, dtype=float) / n_layer
        layer = np.column_stack(
            [
                detector_radius * np.cos(angles),
                detector_radius * np.sin(angles),
                np.full(n_layer, z, dtype=float),
            ]
        )
        positions.append(layer)
    pos = np.vstack(positions)
    dirs = _unit(target_arr[None, :] - pos)
    return SourceSet3D(pos, dirs, architecture, tuple(layer_zs), tuple(target_arr.tolist()))


def build_parameterized_ring_sources(
    total_sources: int,
    layer_count: int,
    detector_radius: float,
    z_extent: float,
    angular_offset_fraction: float,
    orientation_alpha: float,
    roi_center: tuple[float, float, float],
    architecture: str,
) -> SourceSet3D:
    """Build a sampled parameterized multi-layer ring architecture.

    ``orientation_alpha`` interpolates between centre-oriented (0) and
    ROI-oriented (1) directions.
    """

    if layer_count <= 1:
        layer_zs = (0.0,)
    else:
        layer_zs = tuple(np.linspace(-z_extent, z_extent, layer_count).tolist())
    base = total_sources // layer_count
    remainder = total_sources % layer_count
    positions = []
    for li, z in enumerate(layer_zs):
        n_layer = base + (1 if li < remainder else 0)
        step = 2.0 * np.pi / n_layer
        offset = angular_offset_fraction * li * step
        angles = offset + step * np.arange(n_layer, dtype=float)
        positions.append(
            np.column_stack(
                [
                    detector_radius * np.cos(angles),
                    detector_radius * np.sin(angles),
                    np.full(n_layer, z, dtype=float),
                ]
            )
        )
    pos = np.vstack(positions)
    roi = np.asarray(roi_center, dtype=float)
    centre_dirs = _unit(-pos)
    roi_dirs = _unit(roi[None, :] - pos)
    dirs = _unit((1.0 - orientation_alpha) * centre_dirs + orientation_alpha * roi_dirs)
    target = tuple(((1.0 - orientation_alpha) * np.zeros(3) + orientation_alpha * roi).tolist())
    return SourceSet3D(pos, dirs, architecture, layer_zs, target)


def build_rule_architectures(cfg: object) -> list[SourceSet3D]:
    """Return the four rule-baseline source layouts requested for experiment 1."""

    return [
        build_layered_ring_sources(
            cfg.source_count_total,
            cfg.detector_radius,
            cfg.source_ring_zs_single,
            "single_layer_center",
            target=(0.0, 0.0, 0.0),
            stagger=False,
        ),
        build_layered_ring_sources(
            cfg.source_count_total,
            cfg.detector_radius,
            cfg.source_ring_zs_double,
            "double_layer_staggered_center",
            target=(0.0, 0.0, 0.0),
            stagger=True,
        ),
        build_layered_ring_sources(
            cfg.source_count_total,
            cfg.detector_radius,
            cfg.source_ring_zs_triple,
            "triple_layer_staggered_center",
            target=(0.0, 0.0, 0.0),
            stagger=True,
        ),
        build_layered_ring_sources(
            cfg.source_count_total,
            cfg.detector_radius,
            cfg.source_ring_zs_triple,
            "triple_layer_staggered_roi",
            target=cfg.roi_center,
            stagger=True,
        ),
    ]


def cone_vec_vectors(cfg: object, sources: SourceSet3D) -> np.ndarray:
    """Build ASTRA cone_vec rows for flat virtual detector patches.

    Each source gets a detector plane through the system centre, orthogonal to
    the source principal direction. This models a fixed-ring-source static CT
    design with per-source flat detector tiles for the first baseline study.
    """

    rows = []
    world_z = np.array([0.0, 0.0, 1.0])
    for src, direction in zip(sources.positions, sources.directions, strict=True):
        w = _unit(direction[None, :])[0]
        u = np.cross(world_z, w)
        if np.linalg.norm(u) < 1.0e-8:
            u = np.array([1.0, 0.0, 0.0])
        u = u / np.linalg.norm(u) * cfg.detector_col_spacing
        v = np.cross(w, u)
        v = v / np.linalg.norm(v) * cfg.detector_row_spacing
        det_center = np.zeros(3, dtype=float)
        rows.append([*src.tolist(), *det_center.tolist(), *u.tolist(), *v.tolist()])
    return np.asarray(rows, dtype=np.float32)
