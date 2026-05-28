"""Run experiment 3: 3D d-prime task-driven fine screening."""

from __future__ import annotations

from config import ensure_dirs, make_experiment03_config
from experiments3d import configure_logging, run_experiment03_dprime_fine_screening


def main() -> None:
    """Run d-prime fine screening and export task rankings."""

    configure_logging()
    cfg = make_experiment03_config()
    ensure_dirs(cfg)
    result = run_experiment03_dprime_fine_screening(cfg)
    print("3D experiment 3 complete.")
    print(f"Output directory: {cfg.output_dir}")
    print("Top d-prime candidates:")
    for row in result["ranked"][:10]:
        print(
            f"{row['candidate_id']} d_rank={row['dprime_rank']} eig_rank={row['eig_rank_within_top']} "
            f"min_dprime={row['task_utility_min_dprime']:.5g} eig={row['eig_weighted']:.5g} "
            f"layers={row['layer_count']} z={row['z_extent']:.3f} alpha={row['orientation_alpha']:.3f}"
        )


if __name__ == "__main__":
    main()
