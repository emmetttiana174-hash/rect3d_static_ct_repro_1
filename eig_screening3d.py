"""3D Laplace EIG coarse screening with ASTRA projection probes."""

from __future__ import annotations

import logging

import numpy as np

from astra_backend3d import forward_project
from geometry_ring3d import SourceSet3D, build_parameterized_ring_sources
from priors3d import GaussianPrior3D

LOGGER = logging.getLogger(__name__)


def latin_hypercube_candidates(cfg: object) -> list[dict]:
    """Sample a parameterized 3D architecture family."""

    try:
        from scipy.stats import qmc

        sampler = qmc.LatinHypercube(d=5, seed=cfg.seed)
        samples = sampler.random(cfg.eig_candidate_count)
    except Exception:
        rng = np.random.default_rng(cfg.seed)
        samples = rng.random((cfg.eig_candidate_count, 5))
    layer_options = np.array([1, 2, 3, 4])
    rows = []
    for idx, s in enumerate(samples):
        layer_count = int(layer_options[min(int(s[0] * len(layer_options)), len(layer_options) - 1)])
        radius = float(1.25 + 0.45 * s[1])
        z_extent = float(0.0 if layer_count == 1 else 0.15 + 0.45 * s[2])
        offset_fraction = float(s[3])
        alpha = float(s[4])
        rows.append(
            {
                "candidate_id": f"cand_{idx:04d}",
                "layer_count": layer_count,
                "sources_per_layer_mean": cfg.source_count_total / layer_count,
                "radius": radius,
                "z_extent": z_extent,
                "angular_offset_fraction": offset_fraction,
                "orientation_alpha": alpha,
            }
        )
    return rows


def candidate_to_sources(cfg: object, row: dict) -> SourceSet3D:
    """Convert a sampled candidate row to SourceSet3D."""

    return build_parameterized_ring_sources(
        total_sources=cfg.source_count_total,
        layer_count=int(row["layer_count"]),
        detector_radius=float(row["radius"]),
        z_extent=float(row["z_extent"]),
        angular_offset_fraction=float(row["angular_offset_fraction"]),
        orientation_alpha=float(row["orientation_alpha"]),
        roi_center=cfg.roi_center,
        architecture=str(row["candidate_id"]),
    )


def make_probe_volumes(cfg: object) -> np.ndarray:
    """Create deterministic random orthonormal probe volumes."""

    rng = np.random.default_rng(cfg.seed + 991)
    probes = rng.normal(size=(cfg.eig_probe_rank, cfg.nz * cfg.ny * cfg.nx)).astype(np.float32)
    q, _ = np.linalg.qr(probes.T)
    return q[:, : cfg.eig_probe_rank].T.reshape((cfg.eig_probe_rank, cfg.nz, cfg.ny, cfg.nx)).astype(np.float32)


def local_laplace_eig_from_probes(
    cfg: object,
    sources: SourceSet3D,
    prior: GaussianPrior3D,
    probes: np.ndarray,
) -> float:
    """Approximate 0.5 logdet(I + Sigma^1/2 F Sigma^1/2) in a probe subspace."""

    mean_proj = forward_project(cfg, prior.mean_volume, sources)
    lam_sqrt = np.sqrt(np.maximum(cfg.photons_per_source * np.exp(-mean_proj), 1.0e-8)).ravel()
    sigma_sqrt = np.sqrt(prior.diag_var)
    cols = []
    for probe in probes:
        weighted_probe = sigma_sqrt * probe
        proj = forward_project(cfg, weighted_probe.astype(np.float32), sources).ravel()
        cols.append(lam_sqrt * proj)
    b = np.column_stack(cols)
    gram = b.T @ b
    gram.flat[:: gram.shape[0] + 1] += 1.0
    sign, logdet = np.linalg.slogdet(gram)
    if sign <= 0:
        gram.flat[:: gram.shape[0] + 1] += 1.0e-6
        sign, logdet = np.linalg.slogdet(gram)
    return float(0.5 * logdet)


def score_candidate_eig(cfg: object, candidate: dict, priors: list[GaussianPrior3D], probes: np.ndarray) -> dict:
    """Score one candidate with weighted approximate EIG."""

    sources = candidate_to_sources(cfg, candidate)
    row = dict(candidate)
    weighted = 0.0
    for prior in priors:
        val = local_laplace_eig_from_probes(cfg, sources, prior, probes)
        row[f"eig_{prior.name}"] = val
        weighted += prior.weight * val
    row["eig_weighted"] = float(weighted)
    return row


def rank_candidates_by_eig3d(cfg: object, candidates: list[dict], priors: list[GaussianPrior3D]) -> list[dict]:
    """Score and rank sampled candidates."""

    probes = make_probe_volumes(cfg)
    rows = []
    for idx, cand in enumerate(candidates, start=1):
        LOGGER.info("3D EIG candidate %d/%d: %s", idx, len(candidates), cand["candidate_id"])
        rows.append(score_candidate_eig(cfg, cand, priors, probes))
    vals = np.asarray([r["eig_weighted"] for r in rows])
    lo, hi = float(vals.min()), float(vals.max())
    span = hi - lo or 1.0
    mean = float(vals.mean())
    std = float(vals.std()) or 1.0
    for row in rows:
        row["eig_weighted_minmax"] = float((row["eig_weighted"] - lo) / span)
        row["eig_weighted_zscore"] = float((row["eig_weighted"] - mean) / std)
    return sorted(rows, key=lambda r: r["eig_weighted"], reverse=True)
