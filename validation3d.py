"""Poisson MLE/MAP validation for selected 3D source layouts."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib

import numpy as np

from astra_backend3d import forward_project, reconstruct_sirt3d, transmission_counts
from eig_screening3d import candidate_to_sources, make_probe_volumes
from geometry_ring3d import SourceSet3D, build_rule_architectures
from metrics3d import rmse
from phantoms3d import roi_mask, sphere_mask
from priors3d import build_smooth_background


@dataclass(frozen=True)
class ValidationCase3D:
    """One H0/H1 validation task."""

    name: str
    description: str
    background: np.ndarray
    signal: np.ndarray
    roi: np.ndarray


def _signal(cfg: object, center: tuple[float, float, float], radius: float = 0.075, contrast: float = 0.022) -> np.ndarray:
    sig = np.zeros((cfg.nz, cfg.ny, cfg.nx), dtype=np.float32)
    sig[sphere_mask(cfg, center, radius)] = contrast
    return sig


def build_validation_cases(cfg: object) -> list[ValidationCase3D]:
    """Return center-target and eccentric ROI-target validation cases."""

    background = build_smooth_background(cfg)
    center_mask = sphere_mask(cfg, (0.0, 0.0, 0.0), 0.13)
    eccentric_mask = roi_mask(cfg, radius=0.13)
    return [
        ValidationCase3D(
            name="center_target",
            description="中心低对比小目标泊松验证",
            background=background,
            signal=_signal(cfg, (0.0, 0.0, 0.0)),
            roi=center_mask,
        ),
        ValidationCase3D(
            name="eccentric_roi_target",
            description="偏心 ROI 低对比小目标泊松验证",
            background=background,
            signal=_signal(cfg, cfg.roi_center),
            roi=eccentric_mask,
        ),
    ]


def approximate_map_reconstruction(cfg: object, mle_recon: np.ndarray, prior_mean: np.ndarray) -> np.ndarray:
    """Lightweight MAP-style shrinkage for quick validation."""

    w = float(cfg.map_prior_strength)
    return ((1.0 - w) * mle_recon + w * prior_mean).astype(np.float32)


def detectability_from_scores(h0_scores: list[float], h1_scores: list[float]) -> float:
    """Empirical d-prime from scalar observer scores."""

    h0 = np.asarray(h0_scores, dtype=float)
    h1 = np.asarray(h1_scores, dtype=float)
    var = 0.5 * (float(h0.var(ddof=1)) + float(h1.var(ddof=1))) if len(h0) > 1 else 0.0
    if var <= 1.0e-18:
        return 0.0
    return float((h1.mean() - h0.mean()) / np.sqrt(var))


def _score(volume: np.ndarray, signal: np.ndarray) -> float:
    template = signal.ravel().astype(float)
    norm = np.linalg.norm(template)
    if norm > 0.0:
        template = template / norm
    return float(volume.ravel().astype(float) @ template)


def validate_architecture(
    cfg: object,
    method: str,
    sources: SourceSet3D,
    cases: list[ValidationCase3D],
) -> tuple[list[dict], list[dict]]:
    """Run repeated Poisson MLE/MAP validation for one architecture."""

    method_seed = int(hashlib.sha256(method.encode("utf-8")).hexdigest()[:8], 16) % 100000
    rng = np.random.default_rng(cfg.seed + method_seed)
    metric_rows: list[dict] = []
    recon_examples: list[dict] = []
    for case in cases:
        truth_h0 = case.background.astype(np.float32)
        truth_h1 = (case.background + case.signal).astype(np.float32)
        per_recon_scores: dict[str, dict[str, list[float]]] = {
            "MLE": {"H0": [], "H1": []},
            "MAP": {"H0": [], "H1": []},
        }
        per_recon_metrics: dict[str, list[dict]] = {"MLE": [], "MAP": []}
        for rep in range(cfg.validation_replicates):
            for state, truth in [("H0", truth_h0), ("H1", truth_h1)]:
                line_integrals = forward_project(cfg, truth, sources)
                _, log_data = transmission_counts(cfg, line_integrals, rng)
                mle = reconstruct_sirt3d(cfg, log_data, sources)
                map_recon = approximate_map_reconstruction(cfg, mle, case.background)
                for recon_name, recon in [("MLE", mle), ("MAP", map_recon)]:
                    per_recon_scores[recon_name][state].append(_score(recon, case.signal))
                    target_truth = truth_h1 if state == "H1" else truth_h0
                    per_recon_metrics[recon_name].append(
                        {
                            "state": state,
                            "replicate": rep,
                            "rmse_global": rmse(recon, target_truth),
                            "rmse_roi": rmse(recon, target_truth, case.roi),
                        }
                    )
                if rep == 0 and state == "H1":
                    recon_examples.append(
                        {
                            "method": method,
                            "case": case.name,
                            "truth": truth_h1,
                            "MLE": mle,
                            "MAP": map_recon,
                        }
                    )
        for recon_name in ["MLE", "MAP"]:
            vals = per_recon_metrics[recon_name]
            h1_vals = [v for v in vals if v["state"] == "H1"]
            metric_rows.append(
                {
                    "method": method,
                    "architecture": sources.architecture,
                    "case": case.name,
                    "reconstruction": recon_name,
                    "replicates": cfg.validation_replicates,
                    "rmse_global_mean": float(np.mean([v["rmse_global"] for v in h1_vals])),
                    "rmse_global_std": float(np.std([v["rmse_global"] for v in h1_vals], ddof=1)),
                    "rmse_roi_mean": float(np.mean([v["rmse_roi"] for v in h1_vals])),
                    "rmse_roi_std": float(np.std([v["rmse_roi"] for v in h1_vals], ddof=1)),
                    "empirical_dprime": detectability_from_scores(
                        per_recon_scores[recon_name]["H0"],
                        per_recon_scores[recon_name]["H1"],
                    ),
                }
            )
    return metric_rows, recon_examples


def crlb_aopt_score(cfg: object, candidate: dict, background: np.ndarray, probes: np.ndarray) -> float:
    """Approximate global A-optimality with a low-rank probe Hessian."""

    sources = candidate_to_sources(cfg, candidate)
    mean_proj = forward_project(cfg, background, sources)
    lam_sqrt = np.sqrt(np.maximum(cfg.photons_per_source * np.exp(-mean_proj), 1.0e-8)).ravel()
    cols = []
    for probe in probes:
        proj = forward_project(cfg, probe.astype(np.float32), sources).ravel()
        cols.append(lam_sqrt * proj)
    b = np.column_stack(cols)
    h = b.T @ b
    h.flat[:: h.shape[0] + 1] += float(cfg.dprime_regularization_beta)
    return float(np.trace(np.linalg.inv(h)))


def select_crlb_baseline(cfg: object, eig_rows: list[dict]) -> dict:
    """Select an approximate A-optimality baseline from the sampled candidate family."""

    background = build_smooth_background(cfg)
    probes = make_probe_volumes(cfg)[: cfg.crlb_probe_rank]
    scored = []
    for row in eig_rows:
        cand = dict(row)
        cand["crlb_aopt_score"] = crlb_aopt_score(cfg, cand, background, probes)
        scored.append(cand)
    return min(scored, key=lambda r: r["crlb_aopt_score"])


def selected_architectures_for_validation(
    cfg: object,
    crlb_candidate_rows: list[dict],
    eig_top_rows: list[dict],
    dprime_rows: list[dict],
) -> list[tuple[str, SourceSet3D]]:
    """Build the four validation architecture representatives."""

    rule = build_rule_architectures(cfg)[2]
    crlb = select_crlb_baseline(cfg, crlb_candidate_rows)
    eig_best = (
        min(eig_top_rows, key=lambda r: int(r.get("eig_rank_within_top", 10**9)))
        if "eig_rank_within_top" in eig_top_rows[0]
        else max(eig_top_rows, key=lambda r: float(r["eig_weighted"]))
    )
    dprime_best = min(dprime_rows, key=lambda r: int(r["dprime_rank"]))
    pairs = [
        ("Rule_triple_center", rule),
        ("CRLB_Aopt", candidate_to_sources(cfg, crlb)),
        ("EIG_only", candidate_to_sources(cfg, eig_best)),
        ("EIG_plus_dprime", candidate_to_sources(cfg, dprime_best)),
    ]
    renamed = []
    for method, src in pairs:
        renamed.append((method, SourceSet3D(src.positions, src.directions, f"{method}_{src.architecture}", src.layer_zs, src.target)))
    return renamed
