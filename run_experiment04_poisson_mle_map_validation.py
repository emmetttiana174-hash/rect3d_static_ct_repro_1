"""Run experiment 4: Poisson MLE/MAP validation."""

from __future__ import annotations

from config import ensure_dirs, make_experiment04_config
from experiments3d import configure_logging, run_experiment04_poisson_mle_map_validation


def main() -> None:
    """Run final validation and export metrics."""

    configure_logging()
    cfg = make_experiment04_config()
    ensure_dirs(cfg)
    result = run_experiment04_poisson_mle_map_validation(cfg)
    print("3D experiment 4 complete.")
    print(f"Output directory: {cfg.output_dir}")
    print("Selected architectures:")
    for method, src in result["selected"]:
        print(f"{method}: {src.architecture}, layers={len(src.layer_zs)}, layer_zs={src.layer_zs}")
    print("MAP metrics:")
    for row in result["metrics"]:
        if row["reconstruction"] == "MAP":
            print(
                f"{row['method']} {row['case']} global={row['rmse_global_mean']:.5g} "
                f"roi={row['rmse_roi_mean']:.5g} dprime={row['empirical_dprime']:.5g}"
            )


if __name__ == "__main__":
    main()
