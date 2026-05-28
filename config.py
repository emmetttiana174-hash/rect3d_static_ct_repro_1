"""Configuration for 3D static CT source-layout experiments."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Rect3DConfig:
    """Scalar settings for the 3D ring-detector static CT reproduction."""

    name: str = "rect3d_rule_baselines_quick"
    detector_radius: float = 1.5
    detector_height: float = 1.6
    volume_side_xy: float = 1.0
    volume_height: float = 1.0
    nx: int = 32
    ny: int = 32
    nz: int = 32
    detector_cols: int = 48
    detector_rows: int = 32
    source_count_total: int = 48
    source_ring_zs_single: tuple[float, ...] = (0.0,)
    source_ring_zs_double: tuple[float, ...] = (-0.32, 0.32)
    source_ring_zs_triple: tuple[float, ...] = (-0.45, 0.0, 0.45)
    roi_center: tuple[float, float, float] = (0.25, -0.20, 0.15)
    cone_angle_deg: float = 35.0
    j0_total: float = 4.8e8
    poisson_scale: float = 1.0
    sirt_iterations: int = 40
    seed: int = 20260523
    output_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "outputs" / "experiment01_rule_baselines")
    use_cuda_3d: bool = True
    eig_candidate_count: int = 240
    eig_top_fraction: float = 0.10
    eig_probe_rank: int = 24
    eig_prior_weights: tuple[float, float, float] = (0.35, 0.325, 0.325)
    eig_prior_var_background: float = 2.5e-6
    eig_prior_var_target: float = 1.0e-5
    dprime_channel_count: int = 12
    dprime_regularization_beta: float = 2.5e4
    crlb_probe_rank: int = 8
    validation_replicates: int = 5
    map_prior_strength: float = 0.18

    @property
    def voxel_size_x(self) -> float:
        return self.volume_side_xy / self.nx

    @property
    def voxel_size_y(self) -> float:
        return self.volume_side_xy / self.ny

    @property
    def voxel_size_z(self) -> float:
        return self.volume_height / self.nz

    @property
    def detector_col_spacing(self) -> float:
        arc_width = 2.0 * self.detector_radius * __import__("math").tan(__import__("math").radians(self.cone_angle_deg) / 2.0)
        return arc_width / self.detector_cols

    @property
    def detector_row_spacing(self) -> float:
        return self.detector_height / self.detector_rows

    @property
    def photons_per_source(self) -> float:
        return self.j0_total / self.source_count_total


def make_experiment01_config() -> Rect3DConfig:
    """Return a lightweight but meaningful 3D rule-baseline configuration."""

    return Rect3DConfig()


def make_experiment02_config() -> Rect3DConfig:
    """Return config for the 3D EIG coarse-screening experiment."""

    return Rect3DConfig(
        name="rect3d_eig_screening_quick",
        output_dir=PROJECT_ROOT / "outputs" / "experiment02_eig_screening",
        detector_cols=32,
        detector_rows=24,
        eig_candidate_count=240,
        eig_top_fraction=0.10,
        eig_probe_rank=24,
    )


def make_experiment03_config() -> Rect3DConfig:
    """Return config for the 3D d-prime task-driven fine-screening experiment."""

    return Rect3DConfig(
        name="rect3d_dprime_fine_screening_quick",
        output_dir=PROJECT_ROOT / "outputs" / "experiment03_dprime_fine_screening",
        detector_cols=32,
        detector_rows=24,
        eig_candidate_count=240,
        eig_top_fraction=0.10,
        eig_probe_rank=24,
        dprime_channel_count=12,
        dprime_regularization_beta=2.5e4,
    )


def make_experiment04_config() -> Rect3DConfig:
    """Return config for Poisson reconstruction validation experiment."""

    return Rect3DConfig(
        name="rect3d_poisson_mle_map_validation_quick",
        output_dir=PROJECT_ROOT / "outputs" / "experiment04_poisson_mle_map_validation",
        detector_cols=32,
        detector_rows=24,
        eig_candidate_count=240,
        eig_top_fraction=0.10,
        eig_probe_rank=24,
        dprime_channel_count=12,
        dprime_regularization_beta=2.5e4,
        crlb_probe_rank=8,
        validation_replicates=5,
        sirt_iterations=25,
        map_prior_strength=0.18,
    )


def ensure_dirs(cfg: Rect3DConfig) -> None:
    """Create all output directories used by the experiment."""

    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    (cfg.output_dir / "figures").mkdir(parents=True, exist_ok=True)
    (cfg.output_dir / "tables").mkdir(parents=True, exist_ok=True)
    (cfg.output_dir / "recon_slices").mkdir(parents=True, exist_ok=True)
