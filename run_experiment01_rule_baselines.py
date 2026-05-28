"""Run experiment 1: 3D rule-baseline source-layout comparison."""

from __future__ import annotations

from config import ensure_dirs, make_experiment01_config
from experiments3d import configure_logging, run_experiment01_rule_baselines


def main() -> None:
    """Run the first 3D experiment and export tables, figures and report."""

    configure_logging()
    cfg = make_experiment01_config()
    ensure_dirs(cfg)
    result = run_experiment01_rule_baselines(cfg)
    print("3D experiment 1 complete.")
    print(f"Output directory: {cfg.output_dir}")
    for row in result["metrics"]:
        print(
            f"{row['phantom']} | {row['architecture']} | "
            f"global={row['rmse_global']:.5g} roi={row['rmse_roi']:.5g}"
        )


if __name__ == "__main__":
    main()
