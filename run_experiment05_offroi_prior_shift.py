"""Run experiment 5: 3D off-ROI and prior-shift validation."""

from __future__ import annotations

from config import ensure_dirs, make_experiment05_config
from experiments3d import configure_logging, run_experiment05_offroi_prior_shift


def main() -> None:
    """Run off-ROI/prior-shift validation and export metrics."""

    configure_logging()
    cfg = make_experiment05_config()
    ensure_dirs(cfg)
    result = run_experiment05_offroi_prior_shift(cfg)
    print("3D experiment 5 complete.")
    print(f"Output directory: {cfg.output_dir}")
    print("MAP metrics:")
    for row in result["metrics"]:
        if row["reconstruction"] == "MAP":
            print(
                f"{row['method']} {row['case']} global={row['rmse_global_mean']:.5g} "
                f"roi={row['rmse_roi_mean']:.5g} dprime={row['empirical_dprime']:.5g}"
            )


if __name__ == "__main__":
    main()
