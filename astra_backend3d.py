"""ASTRA 3D forward projection and SIRT reconstruction helpers."""

from __future__ import annotations

import logging

import astra
import numpy as np

from geometry_ring3d import SourceSet3D, cone_vec_vectors

LOGGER = logging.getLogger(__name__)


def create_volume_geometry(cfg: object) -> dict:
    """Create an ASTRA 3D volume geometry centred at the origin."""

    hx = cfg.volume_side_xy / 2.0
    hy = cfg.volume_side_xy / 2.0
    hz = cfg.volume_height / 2.0
    return astra.create_vol_geom(cfg.ny, cfg.nx, cfg.nz, -hx, hx, -hy, hy, -hz, hz)


def create_projection_geometry(cfg: object, sources: SourceSet3D) -> dict:
    """Create ASTRA cone_vec projection geometry for one architecture."""

    return astra.create_proj_geom("cone_vec", cfg.detector_rows, cfg.detector_cols, cone_vec_vectors(cfg, sources))


def forward_project(cfg: object, volume: np.ndarray, sources: SourceSet3D) -> np.ndarray:
    """Forward-project a volume with ASTRA cone_vec geometry."""

    vol_geom = create_volume_geometry(cfg)
    proj_geom = create_projection_geometry(cfg, sources)
    proj_id = None
    try:
        proj_id, proj = astra.create_sino3d_gpu(volume.astype(np.float32), proj_geom, vol_geom)
        return np.asarray(proj, dtype=np.float32)
    finally:
        if proj_id is not None:
            astra.data3d.delete(proj_id)


def reconstruct_sirt3d(cfg: object, projections: np.ndarray, sources: SourceSet3D) -> np.ndarray:
    """Reconstruct a volume from projection line integrals with SIRT3D_CUDA."""

    vol_geom = create_volume_geometry(cfg)
    proj_geom = create_projection_geometry(cfg, sources)
    proj_id = rec_id = alg_id = None
    try:
        proj_id = astra.data3d.create("-proj3d", proj_geom, projections.astype(np.float32))
        rec_id = astra.data3d.create("-vol", vol_geom)
        alg_cfg = astra.astra_dict("SIRT3D_CUDA")
        alg_cfg["ProjectionDataId"] = proj_id
        alg_cfg["ReconstructionDataId"] = rec_id
        alg_cfg["option"] = {"MinConstraint": 0.0}
        alg_id = astra.algorithm.create(alg_cfg)
        astra.algorithm.run(alg_id, cfg.sirt_iterations)
        return np.asarray(astra.data3d.get(rec_id), dtype=np.float32)
    finally:
        if alg_id is not None:
            astra.algorithm.delete(alg_id)
        if rec_id is not None:
            astra.data3d.delete(rec_id)
        if proj_id is not None:
            astra.data3d.delete(proj_id)


def transmission_counts(cfg: object, line_integrals: np.ndarray, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Generate Poisson transmission counts and return counts plus log data."""

    i0 = cfg.photons_per_source * np.ones_like(line_integrals, dtype=np.float32)
    lam = np.maximum(i0 * np.exp(-line_integrals), 1.0e-6)
    counts = rng.poisson(lam).astype(np.float32)
    log_data = -np.log(np.maximum(counts, 1.0) / i0)
    return counts, log_data.astype(np.float32)
