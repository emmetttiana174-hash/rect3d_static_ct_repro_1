"""Run experiment 2: 3D EIG coarse screening."""

from __future__ import annotations

from config import ensure_dirs, make_experiment02_config
from experiments3d import configure_logging, run_experiment02_eig_screening


def main() -> None:
    """Run EIG screening and export candidate rankings."""

    configure_logging()
    cfg = make_experiment02_config()
    ensure_dirs(cfg)
    result = run_experiment02_eig_screening(cfg)
    print("3D experiment 2 complete.")
    print(f"Output directory: {cfg.output_dir}")
    print("Top candidates:")
    for row in result["top"][:10]:
        print(
            f"{row['candidate_id']} eig={row['eig_weighted']:.5g} "
            f"layers={row['layer_count']} radius={row['radius']:.3f} "
            f"z={row['z_extent']:.3f} alpha={row['orientation_alpha']:.3f}"
        )


if __name__ == "__main__":
    main()
